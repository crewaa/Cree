from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import SETUP_TOKEN_PURPOSE
from app.modules.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # A setup token authorises ONE action (setting a password) and is signed
    # with the same secret as access tokens. It must never be accepted as a
    # session credential.
    if payload.get("purpose") == SETUP_TOKEN_PURPOSE:
        raise HTTPException(
            status_code=401,
            detail="This token cannot be used for authentication",
        )

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id_int))
    user = result.scalar()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Deactivated accounts must lose access immediately.
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled")

    return user


def require_roles(*roles: str):
    """
    Dependency factory enforcing that the caller holds one of `roles`.

    Usage:
        @router.get("/thing")
        async def handler(current_user: User = require_roles("BRAND")):
            ...
    """
    async def _role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return Depends(_role_checker)


async def require_self_or_admin(
    user_id: int,
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ownership guard for routes with a `{user_id}` path parameter.

    Allows the request only if the caller *is* that user, or is an ADMIN.
    FastAPI resolves `user_id` from the path, so any route declaring this
    dependency must have a `{user_id}` segment.
    """
    if current_user.id != user_id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own data",
        )
    return current_user


