"""Authentication dependencies (consumption side).

Reads the access JWT from the httpOnly cookie set at login, validates it, and
loads the corresponding user. Reuses decode_token (M1), get_db, and the User
model — no duplicated JWT or DB-session logic. Exposed as a FastAPI dependency
so any route can require the current user via `Depends(get_current_user)`.
"""
from __future__ import annotations

import jwt  # PyJWT — imported for its exception types
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.auth.models import User
from app.auth.security import decode_token

# Name of the httpOnly cookie that carries the access JWT. Single source of truth
# for both the login route that WRITES it and this dependency that READS it.
ACCESS_COOKIE = "fundradar_access"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the authenticated user from the access cookie.

    Raises 401 for a missing/invalid/expired token or an unknown user, and 403
    for a disabled account. The 401 message is generic on purpose.
    """
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise _unauthenticated()  # missing cookie

    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise _unauthenticated()  # invalid signature / malformed / expired

    subject = payload.get("sub")
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _unauthenticated()  # missing or non-numeric subject

    user = db.get(User, user_id)
    if user is None:
        raise _unauthenticated()  # user deleted / not found

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )
    return user


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
    )
