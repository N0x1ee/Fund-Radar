"""Authentication routes.

Signup (M2), Login (M3), and the authenticated /me endpoint (M4). Signup creates
an account; login verifies credentials and issues a JWT in an httpOnly cookie;
/me returns the current user via the get_current_user dependency; logout clears the
cookie. Refresh tokens / role-based authorization are not implemented yet. Mounted
in app/api/main.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import settings
from app.auth.models import SavedOpportunity, User
from app.db.models import Opportunity
from app.db.schemas import OpportunityOut
from app.auth.schemas import (AuthConfigOut, GoogleAuthIn, LoginIn,
                              PasswordChangeIn, ProfileUpdateIn,
                              ResendVerificationIn, SignupIn, UserOut)
from app.auth.deps import ACCESS_COOKIE, get_current_user
from app.auth.email import send_verification_email, verification_enabled
from app.auth.google import (GoogleAuthError, google_enabled,
                             unusable_password_hash, verify_google_credential)
from app.auth.security import (create_access_token, create_verification_token,
                               decode_verification_token, hash_password,
                               verify_password)
import jwt  # PyJWT — for verification-token exception types

log = logging.getLogger("fundradar.auth")


def _base_url(request: Request) -> str:
    """Public base URL for building links (config override, else the request)."""
    return (settings.app_base_url or str(request.base_url)).rstrip("/")


def _send_verification(user: User, request: Request) -> None:
    """Generate a token and email the verification link (best-effort)."""
    token = create_verification_token(user.id)
    link = f"{_base_url(request)}/auth/verify?token={token}"
    send_verification_email(user.email, user.full_name, link)

def _start_session(response: Response, user: User, db: Session,
                   *, remember_me: bool) -> None:
    """Issue the access cookie and stamp last_login_at.

    Shared by password login and Google sign-in so there is exactly ONE place
    that decides cookie lifetime and security flags — the two paths can never
    drift apart.
    """
    minutes = (settings.remember_me_days * 24 * 60
               if remember_me else settings.access_token_minutes)
    token = create_access_token(user.id, expires_minutes=minutes)
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=token,
        max_age=minutes * 60,          # cookie expires with the token
        httponly=True,                 # not readable by JavaScript (XSS-safe)
        secure=settings.cookie_secure, # True in production (HTTPS only)
        samesite="lax",                # CSRF mitigation
        path="/",
    )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfigOut)
def auth_config() -> AuthConfigOut:
    """Tell the sign-in page which providers are available.

    The dashboard calls this on load: when Google is not configured it simply
    never renders the button, so an unconfigured deploy looks and behaves
    exactly as it did before Google Sign-In was added.
    """
    return AuthConfigOut(
        google_enabled=google_enabled(),
        google_client_id=settings.google_client_id.strip() if google_enabled() else "",
    )


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, request: Request, db: Session = Depends(get_db)) -> User:
    """Create a new user account.

    Password strength + email format are validated by SignupIn (→ 422).
    Returns the created user (never the password hash). Does not log in.

    When email verification is enabled (an email provider is configured), the
    account starts unverified and a verification link is emailed. When it is not
    configured, the account is auto-verified so the app works with no provider.
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
        is_verified=not verification_enabled(),   # auto-verified if no email provider
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
    if verification_enabled():
        _send_verification(user, request)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)) -> User:
    """Authenticate a user and set an httpOnly access-token cookie.

    Returns the user (never the token). Invalid credentials → 401 with a generic
    message, so login can't be used to discover which emails are registered.
    Email is already normalized by LoginIn. With `remember_me` the session lasts
    REMEMBER_ME_DAYS instead of ACCESS_TOKEN_MINUTES.
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
    if verification_enabled() and not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email first. Check your inbox for the "
                   "verification link, or request a new one.",
        )

    _start_session(response, user, db, remember_me=payload.remember_me)
    return user


@router.post("/google", response_model=UserOut)
def google_login(payload: GoogleAuthIn, response: Response,
                 db: Session = Depends(get_db)) -> User:
    """Sign in (or sign up) with a Google account.

    Verifies the ID token with Google, then matches on the *verified* email
    address:

    - Known email  -> that account is signed in. This deliberately links a
      Google login to an existing password account, so someone who signed up
      with alice@gmail.com and a password can later click the Google button and
      land in the same account with the same bookmarks — instead of silently
      getting a second, empty account. Safe because Google has verified
      ownership of the address (we reject unverified ones).
    - New email    -> an account is created, already verified (Google vouched
      for it) and with no usable password.

    Returns the user and sets the normal session cookie.
    """
    if not google_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not set up on this server yet.",
        )

    try:
        info = verify_google_credential(payload.credential)
    except GoogleAuthError as exc:
        log.warning("Google sign-in rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in could not be verified. Please try again.",
        )

    user = db.scalar(select(User).where(User.email == info["email"]))

    if user is None:
        user = User(
            email=info["email"],
            password_hash=unusable_password_hash(),  # no password login for this account
            full_name=info["full_name"],
            is_verified=True,                        # Google already verified the address
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:      # race: created by a parallel request
            db.rollback()
            user = db.scalar(select(User).where(User.email == info["email"]))
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not complete Google sign-in.",
                )
        else:
            db.refresh(user)
    else:
        # Existing account: fill in a missing name, and treat a Google login as
        # proof of email ownership so verification never blocks these users.
        if not user.full_name and info["full_name"]:
            user.full_name = info["full_name"]
        if not user.is_verified:
            user.is_verified = True

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )

    _start_session(response, user, db, remember_me=payload.remember_me)
    return user


def _verify_result_page(title: str, message: str, ok: bool) -> HTMLResponse:
    color = "#059669" if ok else "#b91c1c"
    icon = "✓" if ok else "✕"
    html = f"""<!doctype html><html><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{title} — FundRadar</title></head>
    <body style="font-family:Segoe UI,Arial,sans-serif;background:#eef3f9;margin:0;
      display:grid;place-items:center;min-height:100vh;color:#0f2540">
      <div style="background:#fff;border:1px solid #e6edf5;border-radius:16px;
        border-top:4px solid {color};padding:34px 40px;max-width:420px;text-align:center;
        box-shadow:0 10px 30px -18px rgba(15,37,64,.3)">
        <div style="font-size:42px;color:{color};line-height:1">{icon}</div>
        <h1 style="font-size:20px;margin:10px 0 6px">{title}</h1>
        <p style="color:#64798f;margin:0 0 20px">{message}</p>
        <a href="/dashboard" style="background:#2563eb;color:#fff;text-decoration:none;
          padding:11px 22px;border-radius:9px;font-weight:700;display:inline-block">
          Go to FundRadar</a>
      </div></body></html>"""
    return HTMLResponse(html)


@router.get("/verify", response_class=HTMLResponse, include_in_schema=False)
def verify_email(token: str, db: Session = Depends(get_db)) -> HTMLResponse:
    """Confirm an email from the link in the verification message."""
    try:
        user_id = decode_verification_token(token)
    except jwt.ExpiredSignatureError:
        return _verify_result_page("Link expired",
            "This verification link has expired. Please log in and request a new one.", False)
    except jwt.PyJWTError:
        return _verify_result_page("Invalid link",
            "This verification link is not valid. Please request a new one.", False)

    user = db.get(User, user_id)
    if user is None:
        return _verify_result_page("Account not found",
            "We couldn't find that account.", False)
    if not user.is_verified:
        user.is_verified = True
        db.commit()
    return _verify_result_page("Email verified",
        "Your email is confirmed. You can now log in to FundRadar.", True)


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(payload: ResendVerificationIn, request: Request,
                        db: Session = Depends(get_db)):
    """Send a fresh verification email. Always returns 202 (never reveals whether
    the email is registered)."""
    if verification_enabled():
        user = db.scalar(select(User).where(User.email == payload.email))
        if user and not user.is_verified:
            _send_verification(user, request)
    return {"detail": "If that email needs verifying, a new link is on its way."}


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


# --- Saved opportunities (bookmarks) ----------------------------------------

@router.get("/saved", response_model=list[OpportunityOut])
def list_saved(db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    """Full details of the current user's saved opportunities (newest first)."""
    rows = db.execute(
        select(Opportunity)
        .join(SavedOpportunity, SavedOpportunity.opportunity_id == Opportunity.id)
        .where(SavedOpportunity.user_id == current_user.id)
        .order_by(SavedOpportunity.created_at.desc())
    ).scalars().all()
    return rows


@router.get("/saved/ids")
def list_saved_ids(db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """Just the opportunity IDs — used by the dashboard to draw bookmark stars."""
    ids = db.scalars(
        select(SavedOpportunity.opportunity_id)
        .where(SavedOpportunity.user_id == current_user.id)
    ).all()
    return {"ids": list(ids)}


@router.post("/saved/{opportunity_id}", status_code=status.HTTP_201_CREATED)
def save_opportunity(opportunity_id: int,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """Bookmark an opportunity. Saving one that's already saved is a no-op."""
    if db.get(Opportunity, opportunity_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Opportunity not found.")
    exists = db.scalar(select(SavedOpportunity).where(
        SavedOpportunity.user_id == current_user.id,
        SavedOpportunity.opportunity_id == opportunity_id))
    if not exists:
        db.add(SavedOpportunity(user_id=current_user.id,
                                opportunity_id=opportunity_id))
        try:
            db.commit()
        except IntegrityError:      # race with a double-click
            db.rollback()
    return {"detail": "Saved."}


@router.delete("/saved/{opportunity_id}")
def unsave_opportunity(opportunity_id: int,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """Remove a bookmark. Safe to call even if it wasn't saved."""
    row = db.scalar(select(SavedOpportunity).where(
        SavedOpportunity.user_id == current_user.id,
        SavedOpportunity.opportunity_id == opportunity_id))
    if row:
        db.delete(row)
        db.commit()
    return {"detail": "Removed."}


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
