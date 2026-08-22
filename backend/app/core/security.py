from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

# `bcrypt__rounds` is configurable because the cost is a real product decision,
# not just a security one: each round doubles the work, and on a small shared
# instance the difference between 12 and 10 is the difference between a login
# that feels instant and one that does not. Existing hashes keep working when it
# changes — bcrypt stores the cost it was created with inside the hash itself.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)

# Purpose claim carried by the short-lived token issued during Google sign-up,
# used ONLY to authorise POST /auth/set-password. Defined here (rather than in
# the auth module) so that app/common/dependencies.py can reject such tokens
# without importing the auth service and creating a circular import.
SETUP_TOKEN_PURPOSE = "set_password"

# Minimum password length enforced at signup / set-password.
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    """Synchronous. Safe from scripts and tests; never call it from a handler."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Synchronous. Safe from scripts and tests; never call it from a handler."""
    return pwd_context.verify(password, hashed)


# ---------------------------------------------------------------------------
# Async wrappers — the only forms a request handler may use.
#
# bcrypt is deliberately slow and deliberately CPU-bound: ~180ms per call on a
# developer laptop, several times that on a small shared instance. Called
# directly from an async handler it does not just make *that* request slow, it
# freezes the entire worker — every other user's dashboard, every poll, every
# in-flight AI call stalls for the duration.
#
# That is why logins felt fine alone and terrible with two people using the app:
# five simultaneous logins took 882ms and ran strictly one after another,
# because none of them ever yielded. Pushed to a thread they overlap, and
# nothing else on the worker is held up.
#
# Same rule as the Apify SDK (rule 7 in CLAUDE.md), applied to CPU work rather
# than to blocking I/O.
# ---------------------------------------------------------------------------

async def hash_password_async(password: str) -> str:
    return await run_in_threadpool(pwd_context.hash, password)


async def verify_password_async(password: str, hashed: str) -> bool:
    return await run_in_threadpool(pwd_context.verify, password, hashed)


#: A real bcrypt hash of a value nobody can log in with, used to spend the same
#: CPU on a missing account as on a real one. Without it, "no such user" returns
#: in ~1ms and "wrong password" in ~180ms, which is a reliable oracle for
#: discovering which email addresses have accounts on Crewaa.
_DUMMY_HASH = pwd_context.hash("crewaa-timing-equaliser-not-a-real-password")


async def waste_equivalent_time() -> None:
    """Spend a verify's worth of CPU so a missing account is indistinguishable."""
    await verify_password_async("crewaa-timing-equaliser-not-a-real-password", _DUMMY_HASH)

def create_access_token(data: dict, expires_minutes: int):
    payload = data.copy()
    # Marks this as a full session token. get_current_user() rejects any token
    # carrying a "purpose" claim, so a setup token can never be used as one.
    payload["type"] = "access"
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
