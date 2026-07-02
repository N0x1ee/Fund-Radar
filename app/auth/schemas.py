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
    is_active: bool
    is_admin: bool
    created_at: datetime | None = None


class TokenOut(BaseModel):
    """Returned when an access token is issued."""
    access_token: str
    token_type: str = "bearer"
