"""Pydantic request/response schemas for authentication.

Decoupled from the ORM (same pattern as app/db/schemas.py) so the API contract
is explicit and the password hash is never serialized back to clients.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def _normalize_email(value: str) -> str:
    """Lowercase + trim so email uniqueness and lookups are case-insensitive."""
    return value.strip().lower()


# Reusable email type: validate the format (EmailStr), THEN normalize. Applied to
# every inbound email (signup + login) so normalization lives in exactly one place.
NormalizedEmail = Annotated[EmailStr, AfterValidator(_normalize_email)]


class SignupIn(BaseModel):
    """Payload for creating an account."""
    email: NormalizedEmail
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginIn(BaseModel):
    """Payload for logging in."""
    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class UserOut(BaseModel):
    """Safe, public representation of a user (no password hash)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    institution: str | None = None
    linkedin: str | None = None
    orcid: str | None = None
    website: str | None = None
    research_interests: str | None = None
    is_active: bool
    is_admin: bool
    is_verified: bool = False
    created_at: datetime | None = None


class ProfileUpdateIn(BaseModel):
    """Editable profile fields (PATCH /auth/me). Only sent fields are changed."""
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    institution: str | None = Field(default=None, max_length=255)
    linkedin: str | None = Field(default=None, max_length=500)
    orcid: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=500)
    research_interests: str | None = Field(default=None, max_length=1000)


class PasswordChangeIn(BaseModel):
    """Payload for changing the account password."""
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ResendVerificationIn(BaseModel):
    """Payload for requesting another verification email."""
    email: NormalizedEmail


class GoogleAuthIn(BaseModel):
    """The signed ID token ("credential") returned by Google Identity Services.

    Length-capped so a malformed or hostile request is rejected by validation
    before any network call to Google is made.
    """
    credential: str = Field(min_length=1, max_length=8192)
    remember_me: bool = False


class AuthConfigOut(BaseModel):
    """Public, non-secret auth settings the sign-in page needs to render itself.

    The Google Client ID is designed to be public (it is embedded in the page
    by every Google Sign-In integration); no secret is exposed here.
    """
    google_enabled: bool = False
    google_client_id: str = ""


class TokenOut(BaseModel):
    """Returned when an access token is issued."""
    access_token: str
    token_type: str = "bearer"
