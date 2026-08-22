from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.core.logging import logger
from app.modules.users.models import User
from app.core.security import (
    hash_password_async,
    verify_password_async,
    waste_equivalent_time,
    create_access_token,
    SETUP_TOKEN_PURPOSE,
    MIN_PASSWORD_LENGTH,
)
from app.core.config import settings
from app.modules.auth.utils import verify_google_token
from datetime import datetime, timedelta
from jose import jwt, JWTError

SETUP_TOKEN_EXPIRE_MINUTES = 10


def normalise_email(email: str) -> str:
    """
    One canonical form for an address.

    `EmailStr` lowercases the domain but leaves the local part alone, so
    `Vishal@gmail.com` and `vishal@gmail.com` were two different accounts: you
    could sign up with one, type the other at the login screen, and be told your
    credentials were invalid. Nothing in the product hinted at why.

    Mail providers treat the local part as case-sensitive in theory. In practice
    none of the ones people actually use do, and matching that expectation is
    worth far more here than standards purity.
    """
    return email.strip().lower()


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Look a user up case-insensitively.

    Compares on `lower(email)` rather than the stored value so accounts created
    before normalisation existed can still sign in. Ordered by id so that if a
    duplicate pair does exist, the same one is chosen every time rather than
    whichever the database happened to return first.
    """
    result = await db.execute(
        select(User)
        .where(func.lower(User.email) == normalise_email(email))
        .order_by(User.id)
    )
    return result.scalars().first()


def validate_password_strength(password: str) -> None:
    """Reject passwords that are trivially weak. Raises HTTPException."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            400,
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long",
        )


def create_setup_token(email: str, role: str) -> str:
    """Short-lived JWT used only to authorize the set-password step."""
    payload = {
        "purpose": SETUP_TOKEN_PURPOSE,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=SETUP_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_setup_token(token: str) -> dict:
    """Decode & validate the setup token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != SETUP_TOKEN_PURPOSE:
            raise HTTPException(400, "Invalid setup token purpose")
        return payload
    except JWTError:
        raise HTTPException(400, "Invalid or expired setup token")


async def signup_user(db: AsyncSession, email: str, password: str, role: str):
    if role.upper() not in ("BRAND", "INFLUENCER"):
        raise HTTPException(403, "Accounts can only be created as BRAND or INFLUENCER")

    validate_password_strength(password)
    email = normalise_email(email)

    if await find_user_by_email(db, email):
        raise HTTPException(400, "An account with this email already exists. Please log in.")

    user = User(
        email=email,
        hashed_password=await hash_password_async(password),
        role=role.upper(),
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        # The check above is not a lock. Two requests for the same address — a
        # double submit, a retried request, two open tabs — both passed it and
        # both tried to insert, and the loser used to surface as a 500. The
        # unique index on users.email is the real guarantee; this turns losing
        # the race into the same answer the check would have given.
        await db.rollback()
        raise HTTPException(400, "An account with this email already exists. Please log in.")

    # Read the row back rather than `db.refresh(user)`.
    #
    # Two reasons, both observed under concurrent signups for the same address.
    # `refresh()` raises "Could not refresh instance" when this session's object
    # is no longer attached to a row it can see — which surfaced as a 500. And
    # more seriously, a losing insert can commit without raising, leaving an
    # in-memory object whose id was never written; minting a token from that
    # would issue a session for a user that does not exist.
    #
    # Re-reading gives whichever row actually won, or nothing at all.
    created = await find_user_by_email(db, email)
    if created is None:
        raise HTTPException(400, "Could not create the account. Please try again.")

    # Only report success if the row that exists is the one *this* request
    # inserted. Returning the winner's row to the loser would be far worse than
    # the 500 it replaced: two people racing to register the same address would
    # both be handed a session, and the one who lost would hold a valid token
    # for an account whose password they never set.
    if user.id is None or created.id != user.id:
        raise HTTPException(400, "An account with this email already exists. Please log in.")

    return created


def issue_access_token(user: User) -> tuple[str, str]:
    """Mint a session token for a user who has already been authenticated."""
    return create_access_token(
        {"sub": str(user.id), "role": user.role},
        settings.access_token_expire_minutes,
    ), user.role


async def authenticate_user(db: AsyncSession, email: str, password: str):
    user = await find_user_by_email(db, email)

    if not user or not user.hashed_password:
        # Spend the same CPU a real verify would. Returning immediately made a
        # missing account answer in ~1ms and a wrong password in ~180ms, which
        # is a reliable way to discover which addresses have Crewaa accounts.
        await waste_equivalent_time()
        raise HTTPException(401, "Invalid email or password")

    if not await verify_password_async(password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")

    if not user.is_active:
        raise HTTPException(403, "This account is disabled")

    return issue_access_token(user)


async def google_auth(db, id_token: str, role: str | None):
    payload = await verify_google_token(id_token)
    email = normalise_email(payload["email"])

    user = await find_user_by_email(db, email)

    # CASE 1: Existing user who already has a password → direct login
    if user and user.hashed_password:
        token, role_name = issue_access_token(user)
        return {"access_token": token, "role": role_name, "needs_password": False}

    # CASE 2: Existing Google-only user (no password yet) → ask them to set one
    if user and not user.hashed_password:
        setup_token = create_setup_token(email=email, role=user.role)
        return {"needs_password": True, "setup_token": setup_token, "email": email}

    # CASE 3: Brand new user → create account, then ask to set password
    if not role:
        raise HTTPException(
            status_code=400,
            detail="Role is required for first-time signup",
        )

    user = User(
        email=email,
        role=role,
        hashed_password=None,  # Will be set via /auth/set-password
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Same race as password signup: two Google popups completing at once.
        await db.rollback()
        user = await find_user_by_email(db, email)
        if user is None:
            raise HTTPException(400, "Could not create the account. Please try again.")

    setup_token = create_setup_token(email=email, role=role)
    return {"needs_password": True, "setup_token": setup_token, "email": email}


async def set_password_service(db: AsyncSession, setup_token: str, password: str):
    """Validate the setup token, set the user's password, return a real access token."""
    token_data = decode_setup_token(setup_token)
    email = normalise_email(token_data["email"])

    validate_password_strength(password)

    user = await find_user_by_email(db, email)

    if not user:
        raise HTTPException(404, "User not found")

    # A setup token may only ever complete an account that has no password yet.
    # Without this guard, any leaked/replayed setup token would be a password
    # reset for an already-secured account.
    if user.hashed_password:
        raise HTTPException(
            400,
            "This account already has a password. Please log in instead.",
        )

    if not user.is_active:
        raise HTTPException(403, "This account is disabled")

    user.hashed_password = await hash_password_async(password)
    await db.commit()
    await db.refresh(user)

    return issue_access_token(user)
