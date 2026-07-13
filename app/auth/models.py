"""Authentication ORM models.

Kept in its own module (rather than in app/db/models.py) so the auth feature is
self-contained and to minimize merge conflicts with the shared models file that
teammates also edit. It uses the SAME declarative Base + engine as the rest of
the app, so `User` lives in the same database as Agency/Opportunity.

Mirrors the style of app/db/models.py (Mapped / mapped_column, server defaults).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (Boolean, DateTime, ForeignKey, String,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 320 = max length of a valid email address (RFC 5321).
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # Stores only the hash (bcrypt ~60 chars); never the plaintext password.
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))

    # Profile fields (editable on /profile). All optional.
    phone: Mapped[str | None] = mapped_column(String(20))
    institution: Mapped[str | None] = mapped_column(String(255))
    linkedin: Mapped[str | None] = mapped_column(String(500))
    orcid: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(500))
    research_interests: Mapped[str | None] = mapped_column(String(1000))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


class SavedOpportunity(Base):
    """A user's bookmark on a funding opportunity (unique per user+opportunity)."""
    __tablename__ = "saved_opportunities"
    __table_args__ = (UniqueConstraint("user_id", "opportunity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("opportunities.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
