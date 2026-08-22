from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.dependencies import get_db
from app.core.config import settings
from app.modules.auth.schemas import (
    SignupRequest, LoginRequest, TokenResponse,
    GoogleAuthRequest, GoogleAuthResponse, SetPasswordRequest
)
from app.modules.auth.service import (
    authenticate_user, google_auth, issue_access_token, set_password_service, signup_user,
)
from app.common.rate_limit import (
    check_login_allowed, clear_login_failures, rate_limit, record_login_failure,
)


router = APIRouter(prefix="/auth", tags=["Auth"])

# NOTE: this module used to define its own local copy of `get_db`, duplicating
# the one in app/common/dependencies.py. Two session providers meant auth routes
# silently bypassed anything applied to the shared dependency — including test
# overrides. Always use the shared dependency.

# Credential endpoints are throttled by IP: without this, /login is an
# unbounded password-guessing oracle and /signup an unbounded account-creation one.
@router.post(
    "/signup",
    response_model=TokenResponse,
    dependencies=[rate_limit(10, 3600, "signup")],
)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    user = await signup_user(db, data.email, data.password, data.role)

    # Mint the token from the user we just created, rather than calling
    # authenticate_user. That re-read the row and ran a second bcrypt operation
    # to verify a password we had just hashed ourselves — doubling the cost of
    # the slowest thing in the request for no additional certainty.
    access_token, role = issue_access_token(user)
    return {"access_token": access_token, "role": role}


@router.post(
    "/login",
    response_model=TokenResponse,
    # A coarse flood guard only. The real protection is the failure counter
    # below: this one is deliberately loose because it counts every attempt,
    # including the successful ones.
    dependencies=[rate_limit(60, 300, "login_flood")],
)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Sign in.

    Lockout is counted on **failures only**, per email+IP. The previous throttle
    counted every attempt against the IP, so somebody who mistyped their
    password a few times and then typed it correctly was answered with "Too many
    requests" — right credentials, refused anyway, and no way to tell that from
    the app being broken.
    """
    check_login_allowed(
        request, data.email,
        settings.login_max_failures,
        settings.login_failure_window_seconds,
    )

    try:
        access_token, role = await authenticate_user(db, data.email, data.password)
    except HTTPException as exc:
        if exc.status_code == 401:
            record_login_failure(request, data.email, settings.login_failure_window_seconds)
        raise

    clear_login_failures(request, data.email)
    return {"access_token": access_token, "role": role}


@router.post(
    "/google",
    response_model=GoogleAuthResponse,
    dependencies=[rate_limit(20, 300, "google")],
)
async def google_login(
    data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await google_auth(db, data.id_token, data.role)
    return result


@router.post(
    "/set-password",
    response_model=TokenResponse,
    dependencies=[rate_limit(10, 900, "set_password")],
)
async def set_password(
    data: SetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    access_token, role = await set_password_service(db, data.setup_token, data.password)
    return {"access_token": access_token, "role": role}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """
    Logs out the user by clearing auth cookies (refresh token).
    Access token is cleared on frontend.
    """

    # Clear refresh token cookie (future-proof)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,  # set True in production (HTTPS)
        samesite="lax",
    )

    return
