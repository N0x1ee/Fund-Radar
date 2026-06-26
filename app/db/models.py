"""Database models for FundRadar.

Agency      -> the seed list (from Funding_Agency_Database.xlsx)
Opportunity -> individual grants/fellowships scraped + AI-extracted (Phase 2/3)
"""
from datetime import datetime, date

from sqlalchemy import (
    String, Text, Integer, Date, DateTime, ForeignKey, Numeric, Boolean, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Agency(Base):
    __tablename__ = "agencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agency_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g. IND001
    name: Mapped[str] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(180))
    funding_type: Mapped[str | None] = mapped_column(String(180))
    website: Mapped[str | None] = mapped_column(String(500))
    research_areas: Mapped[str | None] = mapped_column(Text)
    eligibility: Mapped[str | None] = mapped_column(Text)
    deadline_frequency: Mapped[str | None] = mapped_column(String(180))
    current_open_calls: Mapped[str | None] = mapped_column(Text)
    scraping_priority: Mapped[str | None] = mapped_column(String(60))
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    opportunities: Mapped[list["Opportunity"]] = relationship(back_populates="agency")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id"), index=True)

    program_name: Mapped[str] = mapped_column(String(500), index=True)
    funding_amount: Mapped[str | None] = mapped_column(String(255))   # free-text; amounts vary wildly
    amount_value: Mapped[float | None] = mapped_column(Numeric(18, 2))  # normalized when parseable
    currency: Mapped[str | None] = mapped_column(String(10))
    eligibility: Mapped[str | None] = mapped_column(Text)
    research_area: Mapped[str | None] = mapped_column(String(255), index=True)
    deadline: Mapped[date | None] = mapped_column(Date, index=True)
    application_link: Mapped[str | None] = mapped_column(String(800))
    contact_info: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)        # AI-generated
    tags: Mapped[str | None] = mapped_column(Text)           # comma-separated, AI-generated
    raw_text: Mapped[str | None] = mapped_column(Text)       # scraped page text (pre-AI, for Phase 3)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)  # AI extraction completed?
    status: Mapped[str] = mapped_column(String(40), default="open")  # open | closed | unknown

    source_url: Mapped[str | None] = mapped_column(String(800))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)  # change detection
    first_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_checked: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    agency: Mapped["Agency"] = relationship(back_populates="opportunities")
