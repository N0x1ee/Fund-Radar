"""FastAPI read API for FundRadar (Phase 1).

Serves the seeded agency data and (once Phase 2/3 populate them) funding
opportunities, with filtering and pagination. Interactive docs at /docs.

Run:  uvicorn app.api.main:app --reload
"""
from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.security import install_security
from app.config import settings
from app.db.database import SessionLocal, init_db
from app.db.models import Agency, Opportunity
from app.db.schemas import AgencyOut, OpportunityOut, Page
from app.chat.bot import answer as chat_answer
from app.auth.routes import router as auth_router

log = logging.getLogger("fundradar.api")

app = FastAPI(
    title="FundRadar API",
    version="0.1.0",
    description="Funding Opportunity Intelligence Platform — read API.",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
)
install_security(app)
app.include_router(auth_router)


@app.on_event("startup")
def _bootstrap_db() -> None:
    """Ensure tables exist and seed data if the database is empty.

    On ephemeral hosts (e.g. Render free tier) the SQLite file is recreated on
    every boot, so this guarantees the demo always has data even if the start
    command's seed step is skipped. Safe + idempotent: only seeds when empty.
    """
    try:
        init_db()
        db = SessionLocal()
        try:
            if db.scalar(select(func.count()).select_from(Agency)) == 0:
                from app.ingest.seed_agencies import seed
                seed()
            if db.scalar(select(func.count()).select_from(Opportunity)) == 0:
                from app.ingest.load_demo_opportunities import load
                load()
        finally:
            db.close()
    except Exception as e:  # never block startup over seeding
        log.warning("startup bootstrap skipped: %s", e)


_STATIC = Path(__file__).parent / "static"


def _page(name: str) -> str:
    """Read a static HTML page at request time.

    Read per request (not cached at import) so edits to the HTML are served
    immediately without restarting the process. The files are small, so the
    read cost is negligible.
    """
    return (_STATIC / name).read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse, tags=["meta"])
def home():
    """Default dashboard — project's white/blue/green theme."""
    return _page("dashboard.html")


@app.get("/app", response_class=HTMLResponse, tags=["meta"])
def new_app():
    """Friend's alternate multi-page web app — preview here (indigo/dark theme)."""
    return _page("index.html")


@app.get("/api", tags=["meta"])
def api_info():
    return {"name": "FundRadar API", "version": "0.1.0", "docs": "/docs"}


@app.get("/stats", tags=["meta"])
def stats(db: Session = Depends(get_db)):
    """Aggregate statistics for the dashboard (counts + breakdowns)."""
    agencies = db.scalars(select(Agency)).all()
    opps = db.scalars(select(Opportunity)).all()

    countries = Counter(a.country for a in agencies if a.country)
    categories = Counter(a.category for a in agencies if a.category)
    funding_types = Counter(a.funding_type for a in agencies if a.funding_type)
    status_counts = Counter((o.status or "unknown") for o in opps)
    areas = Counter(o.research_area for o in opps if o.research_area)

    times = [o.last_checked for o in opps if o.last_checked]
    times += [a.updated_at for a in agencies if a.updated_at]
    last_updated = max(times) if times else None

    return {
        "agencies": len(agencies),
        "opportunities": len(opps),
        "open": status_counts.get("open", 0),
        "closed": status_counts.get("closed", 0),
        "unknown": status_counts.get("unknown", 0),
        "processed": sum(1 for o in opps if o.processed),
        "countries": len(countries),
        "categories": len(categories),
        "funding_types": len(funding_types),
        "with_opportunities": len({o.agency_id for o in opps}),
        "countries_breakdown": dict(countries.most_common()),
        "categories_breakdown": dict(categories.most_common(12)),
        "funding_types_breakdown": dict(funding_types.most_common()),
        "status_breakdown": dict(status_counts),
        "research_areas_breakdown": dict(areas.most_common(10)),
        "last_updated": last_updated.isoformat() if last_updated else None,
    }


@app.get("/scrapers", tags=["scraper"])
def scrapers(db: Session = Depends(get_db)):
    """Per-agency scraper status, derived from the current implementation.

    The scraping engine (Phase 2) is built and shared across all agencies. Live
    runs are not executed on this demo host; agencies that already have records
    (from the curated demo dataset) are reported as 'data loaded'.
    """
    agencies = db.scalars(select(Agency).order_by(Agency.agency_code)).all()
    rows = db.execute(
        select(Opportunity.agency_id, func.count(), func.max(Opportunity.last_checked))
        .group_by(Opportunity.agency_id)
    ).all()
    counts = {aid: (c, ts) for aid, c, ts in rows}

    targets = []
    for a in agencies:
        n, ts = counts.get(a.id, (0, None))
        targets.append({
            "agency_code": a.agency_code,
            "agency": a.name,
            "country": a.country,
            "website": a.website,
            "priority": a.scraping_priority or "medium",
            "records": n,
            "last_run": ts.isoformat() if ts else None,
            "status": "data loaded" if n else "ready",
            "success": True if n else None,
        })

    return {
        "engine": {
            "phase": "Phase 2 - Scraping & ingestion (in progress)",
            "capabilities": [
                "Polite HTTP fetch (custom User-Agent)",
                "robots.txt compliance",
                "Per-host rate limiting (2s) + retry with backoff",
                "Keyword-scored funding-link discovery (on-domain only)",
                "Raw-text extraction + SHA-256 content-hash change detection",
                "Priority-ordered CLI (--agency / --priority / --limit)",
            ],
            "pending": [
                "PDF text extraction (Phase 2b)",
                "Playwright rendering for JS-heavy sites (Phase 2b)",
            ],
            "live_runs_executed": False,
            "total_targets": len(agencies),
            "targets_with_data": sum(1 for t in targets if t["records"]),
        },
        "targets": targets,
    }


@app.get("/chat", tags=["chat"])
def chat(q: str = Query(..., min_length=1, max_length=300, description="A plain-language question about funding"),
         db: Session = Depends(get_db)):
    """Ask the chatbot about the funding opportunities in the database."""
    return {"question": q, "answer": chat_answer(q, db)}


@app.get("/health", tags=["meta"])
def health(db: Session = Depends(get_db)):
    agencies = db.scalar(select(func.count()).select_from(Agency))
    opportunities = db.scalar(select(func.count()).select_from(Opportunity))
    return {"status": "ok", "agencies": agencies, "opportunities": opportunities}


# Sort keys accepted by /agencies?sort=...  "code" reproduces the original
# ordering, so omitting the parameter behaves exactly as before.
AGENCY_SORTS = ("code", "name_asc", "name_desc", "country", "opportunities", "updated")


def _agency_opportunity_count():
    """Correlated sub-query: number of opportunities belonging to each agency row."""
    return (
        select(func.count(Opportunity.id))
        .where(Opportunity.agency_id == Agency.id)
        .scalar_subquery()
    )


@app.get("/agencies", response_model=Page[AgencyOut], tags=["agencies"])
def list_agencies(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="Search agency name (case-insensitive)"),
    country: str | None = None,
    category: str | None = None,
    funding_type: str | None = None,
    priority: str | None = Query(None, description="Filter by scraping_priority"),
    has_opportunities: bool | None = Query(
        None,
        description="true = only agencies that have funding opportunities; false = only those without",
    ),
    sort: str = Query(
        "code",
        description="code | name_asc | name_desc | country | opportunities | updated",
    ),
    limit: int = Query(50, ge=1, le=500),
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
    if has_opportunities is not None:
        n_opps = _agency_opportunity_count()
        stmt = stmt.where(n_opps > 0 if has_opportunities else n_opps == 0)

    # total is computed before ordering, so sorting never affects the count
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    sort = sort if sort in AGENCY_SORTS else "code"
    if sort == "name_asc":
        order = (Agency.name.asc(),)
    elif sort == "name_desc":
        order = (Agency.name.desc(),)
    elif sort == "country":
        order = (Agency.country.asc(), Agency.name.asc())
    elif sort == "opportunities":
        order = (_agency_opportunity_count().desc(), Agency.name.asc())
    elif sort == "updated":
        order = (Agency.updated_at.desc(), Agency.agency_code.asc())
    else:
        order = (Agency.agency_code.asc(),)

    rows = db.scalars(stmt.order_by(*order).limit(limit).offset(offset)).all()
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
    limit: int = Query(50, ge=1, le=500),
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
