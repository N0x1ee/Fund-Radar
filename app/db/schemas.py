"""Pydantic response models for the API layer.

These define the JSON shape returned to clients, decoupled from the ORM models.
`from_attributes=True` lets us build them straight from SQLAlchemy rows.
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class AgencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agency_code: str
    name: str
    country: str | None = None
    category: str | None = None
    funding_type: str | None = None
    website: str | None = None
    research_areas: str | None = None
    eligibility: str | None = None
    deadline_frequency: str | None = None
    current_open_calls: str | None = None
    scraping_priority: str | None = None
    notes: str | None = None


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agency_id: int
    program_name: str
    funding_amount: str | None = None
    amount_value: float | None = None
    currency: str | None = None
    eligibility: str | None = None
    research_area: str | None = None
    deadline: date | None = None
    application_link: str | None = None
    contact_info: str | None = None
    summary: str | None = None
    tags: str | None = None
    status: str
    source_url: str | None = None
    last_checked: datetime | None = None


class Page(BaseModel, Generic[T]):
    """Generic paginated envelope."""
    total: int
    limit: int
    offset: int
    items: list[T]
