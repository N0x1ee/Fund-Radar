"""Authentication routes.

Signup (M2), Login (M3), and the authenticated /me endpoint (M4). Signup creates
an account; login verifies credentials and issues a JWT in an httpOnly cookie;
/me returns the current user via the get_current_user dependency; logout clears the
cookie. Refresh tokens / role-based authorization are not implemented yet. Mounted
in app/api/main.py.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.auth.models import User
from app.auth.schemas import (LoginIn, PasswordChangeIn, ProfileUpdateIn,
                              SignupIn, UserOut)
from app.auth.deps import ACCESS_COOKIE, get_current_user
from app.auth.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: Session = Depends(get_db)) -> User:
    """Create a new user account.

    Password strength + email format are validated by SignupIn (→ 422).
    Returns the created user (never the password hash). Does not log in.
    """
    # Email is already normalized (trimmed + lowercased) by the SignupIn schema.
    # Friendly pre-check (fast path, clear message).
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Race: another request created the same email between check and commit.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    db.refresh(user)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)) -> User:
    """Authenticate a user and set an httpOnly access-token cookie.

    Returns the user (never the token). Invalid credentials → 401 with a generic
    message, so login can't be used to discover which emails are registered.
    Email is already normalized by LoginIn. `remember_me` is accepted but not yet
    acted upon (deferred to a later milestone).
    """
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )

    token = create_access_token(user.id)
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=token,
        max_age=settings.access_token_minutes * 60,  # cookie expires with the token
        httponly=True,                 # not readable by JavaScript (XSS-safe)
        secure=settings.cookie_secure, # True in production (HTTPS only)
        samesite="lax",                # CSRF mitigation
        path="/",
    )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user (requires a valid access cookie)."""
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileUpdateIn,
              db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)) -> User:
    """Update the current user's profile. Only fields present in the request change."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(payload: PasswordChangeIn,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """Change the account password (requires the current password)."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password changed."}


@router.post("/logout")
def logout(response: Response):
    """Clear the access cookie. Safe to call whether or not a session exists."""
    response.delete_cookie(
        key=ACCESS_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return {"detail": "Logged out."}
