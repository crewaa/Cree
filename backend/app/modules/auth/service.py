from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.modules.users.models import User
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.modules.auth.utils import verify_google_token
from app.core.security import create_access_token

async def signup_user(db: AsyncSession, email: str, password: str, role: str):
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar():
        raise HTTPException(400, "User already exists")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=role
    )
    db.add(user)
    await db.commit()
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        settings.access_token_expire_minutes
    )

    return token, user.role


async def google_auth(db, id_token: str, role: str | None):
    payload = await verify_google_token(id_token)

    email = payload["email"]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar()

    # 🔹 CASE 1: User already exists → LOGIN
    if user:
        token = create_access_token(
            {"sub": str(user.id), "role": user.role},
            settings.access_token_expire_minutes,
        )
        return token, user.role

    # 🔹 CASE 2: First-time Google user → SIGNUP
    if not role:
        raise HTTPException(
            status_code=400,
            detail="Role is required for first-time signup",
        )

    user = User(
        email=email,
        role=role,
        hashed_password=None,  # Google users don't have password
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        {"sub": str(user.id), "role": user.role},
        settings.access_token_expire_minutes,
    )

    return token, user.role
