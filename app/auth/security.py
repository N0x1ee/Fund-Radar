"""Password hashing + JWT utilities for authentication.

Pure, side-effect-free functions (no DB, no FastAPI) so they are trivially
unit-testable and reusable by the auth routes added in a later milestone.

- Passwords are hashed with the bcrypt library directly (never stored in
  plaintext). passlib is intentionally NOT used: passlib 1.7.4 is unmaintained
  and incompatible with bcrypt >= 4.1 (it reads the removed `bcrypt.__about__`).
- Tokens are signed JWTs (HS256) using settings.jwt_secret.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt  # PyJWT

from app.config import settings

# bcrypt only ever uses the first 72 BYTES of a password; bcrypt >= 5 raises if
# a longer value is passed. We truncate deterministically (identical on hash and
# verify), which matches bcrypt's own historical behavior.
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


# --- Password hashing -------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a bcrypt hash (utf-8 string) for a plaintext password."""
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT tokens -------------------------------------------------------------

def create_access_token(
    subject: str | int,
    *,
    expires_minutes: int | None = None,
    extra_claims: dict | None = None,
) -> str:
    """Create a signed JWT whose `sub` claim identifies the user.

    `expires_minutes` overrides the configured default (used later for
    "Remember me" longer-lived tokens).
    """
    minutes = expires_minutes if expires_minutes is not None else settings.access_token_minutes
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Validate + decode a JWT, returning its payload.

    Raises `jwt.PyJWTError` (e.g. ExpiredSignatureError, InvalidTokenError) if
    the token is invalid or expired — callers handle that as a 401.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# --- Email-verification tokens ---------------------------------------------

def create_verification_token(user_id: str | int, *, expires_hours: int = 24) -> str:
    """Signed, expiring token embedded in the email verification link."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=expires_hours),
        "type": "verify",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_verification_token(token: str) -> int:
    """Return the user id from a valid 'verify' token, else raise jwt.PyJWTError."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "verify":
        raise jwt.InvalidTokenError("not a verification token")
    return int(payload["sub"])
