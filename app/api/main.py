"""FastAPI read API for FundRadar (Phase 1).

Serves the seeded agency data and (once Phase 2/3 populate them) funding
opportunities, with filtering and pagination. Interactive docs at /docs.

Run:  uvicorn app.api.main:app --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.models import Agency, Opportunity
from app.db.schemas import AgencyOut, OpportunityOut, Page
from app.chat.bot import answer as chat_answer

app = FastAPI(
    title="FundRadar API",
    version="0.1.0",
    description="Funding Opportunity Intelligence Platform — read API.",
)


_DASHBOARD = (Path(__file__).parent / "static" / "dashboard.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse, tags=["meta"])
def dashboard():
    """Professional dashboard view of the data."""
    return _DASHBOARD


@app.get("/api", tags=["meta"])
def api_info():
    return {"name": "FundRadar API", "version": "0.1.0", "docs": "/docs"}


@app.get("/chat", tags=["chat"])
def chat(q: str = Query(..., description="A plain-language question about funding"),
         db: Session = Depends(get_db)):
    """Ask the chatbot about the funding opportunities in the database."""
    return {"question": q, "answer": chat_answer(q, db)}


@app.get("/health", tags=["meta"])
def health(db: Session = Depends(get_db)):
    agencies = db.scalar(select(func.count()).select_from(Agency))
    opportunities = db.scalar(select(func.count()).select_from(Opportunity))
    return {"status": "ok", "agencies": agencies, "opportunities": opportunities}


@app.get("/agencies", response_model=Page[AgencyOut], tags=["agencies"])
def list_agencies(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Search agency name (case-insensitive)"),
    country: str | None = None,
    category: str | None = None,
    funding_type: str | None = None,
    priority: str | None = Query(None, description="Filter by scraping_priority"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(Agency)
    if q:
        stmt = stmt.where(Agency.name.ilike(f"%{q}%"))
    if country:
        stmt = stmt.where(Agency.country == country)
    if category:
        stmt = stmt.where(Agency.category.ilike(f"%{category}%"))
    if funding_type:
        stmt = stmt.where(Agency.funding_type.ilike(f"%{funding_type}%"))
    if priority:
        stmt = stmt.where(Agency.scraping_priority == priority)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Agency.agency_code).limit(limit).offset(offset)).all()
    return Page[AgencyOut](total=total, limit=limit, offset=offset, items=rows)


@app.get("/agencies/{agency_code}", response_model=AgencyOut, tags=["agencies"])
def get_agency(agency_code: str, db: Session = Depends(get_db)):
    agency = db.scalar(select(Agency).where(Agency.agency_code == agency_code))
    if not agency:
        raise HTTPException(status_code=404, detail=f"Agency '{agency_code}' not found")
    return agency


@app.get("/opportunities", response_model=Page[OpportunityOut], tags=["opportunities"])
def list_opportunities(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Search program name"),
    research_area: str | None = None,
    status: str | None = Query(None, description="open | closed | unknown"),
    min_amount: float | None = Query(None, description="Minimum normalized amount_value"),
    agency_code: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(Opportunity)
    if q:
        stmt = stmt.where(Opportunity.program_name.ilike(f"%{q}%"))
    if research_area:
        stmt = stmt.where(Opportunity.research_area.ilike(f"%{research_area}%"))
    if status:
        stmt = stmt.where(Opportunity.status == status)
    if min_amount is not None:
        stmt = stmt.where(Opportunity.amount_value >= min_amount)
    if agency_code:
        stmt = stmt.join(Agency).where(Agency.agency_code == agency_code)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(Opportunity.deadline.is_(None), Opportunity.deadline)
        .limit(limit).offset(offset)
    ).all()
    return Page[OpportunityOut](total=total, limit=limit, offset=offset, items=rows)
