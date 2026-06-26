"""Per-agency scrape pipeline (Phase 2, raw stage).

For one agency:
  1. fetch its homepage
  2. discover funding-related links
  3. fetch each candidate page
  4. extract text + content hash
  5. upsert an Opportunity row (raw_text filled, processed=False)

Change detection: if an Opportunity with the same source_url exists and the
content hash is unchanged, we skip; if changed, we refresh raw_text and reset
`processed` so Phase 3 re-extracts. Structured fields are left for the AI stage.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Agency, Opportunity
from app.scraper import discovery, extractor, fetcher


@dataclass
class AgencyScrapeReport:
    agency_code: str
    homepage_ok: bool
    candidates: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: int = 0
    note: str = ""


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _upsert_opportunity(db: Session, agency: Agency, *, url: str, title, link_text, text) -> str:
    """Returns one of: created | updated | unchanged."""
    chash = extractor.content_hash(text)
    existing = db.scalar(select(Opportunity).where(Opportunity.source_url == url))
    if existing:
        if existing.content_hash == chash:
            return "unchanged"
        existing.raw_text = text
        existing.content_hash = chash
        existing.processed = False
        existing.program_name = extractor.guess_program_name(link_text, title, url)
        return "updated"
    db.add(Opportunity(
        agency_id=agency.id,
        program_name=extractor.guess_program_name(link_text, title, url),
        source_url=url,
        application_link=url,
        raw_text=text,
        content_hash=chash,
        status="unknown",
        processed=False,
    ))
    return "created"


def scrape_agency(db: Session, agency: Agency, *, max_pages: int = 8) -> AgencyScrapeReport:
    report = AgencyScrapeReport(agency_code=agency.agency_code, homepage_ok=False)
    home = _normalize_url(agency.website)
    if not home:
        report.note = "no website on record"
        return report

    res = fetcher.fetch(home)
    if not res.ok or not res.html:
        report.note = res.error or f"homepage status {res.status}"
        return report
    report.homepage_ok = True

    candidates = discovery.find_funding_links(res.html, home, limit=max_pages)
    report.candidates = len(candidates)

    for cand in candidates:
        page = fetcher.fetch(cand.url)
        if not page.ok or not page.html:
            report.errors += 1
            continue
        text = extractor.extract_text(page.html)
        if len(text) < 200:  # too thin to be a real opportunity page
            continue
        outcome = _upsert_opportunity(
            db, agency,
            url=cand.url,
            title=extractor.page_title(page.html),
            link_text=cand.text,
            text=text,
        )
        setattr(report, outcome, getattr(report, outcome) + 1)

    db.commit()
    return report
