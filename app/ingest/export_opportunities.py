"""Export the current database's opportunities into data/demo_opportunities.json.

This is how real, locally-scraped+extracted data gets onto the deployed site:
the deployed app loads that JSON on startup (no LLM needed in production). We
write it in the exact shape the loader expects, dropping junk nav-link rows and
de-duplicating so the live dashboard looks clean.

Run (with your real fundradar.db present):
  python -m app.ingest.export_opportunities
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Agency, Opportunity

OUT = Path(__file__).resolve().parents[2] / "data" / "demo_opportunities.json"

# Names that mean the scraper grabbed a nav link, not a real scheme.
JUNK_NAMES = {
    "read more", "read more →", "apply", "apply now", "click here", "more",
    "details", "home", "funding opportunities", "programmsuche", "programmsuche →",
    "untitled scheme", "view all", "learn more", "",
}


def is_junk(name: str | None) -> bool:
    if not name:
        return True
    n = name.strip().lower()
    return n in JUNK_NAMES or len(n) < 5


def export() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(
            select(Opportunity, Agency.agency_code)
            .join(Agency, Agency.id == Opportunity.agency_id)
        ).all()

        seen: set[tuple[str, str]] = set()
        out: list[dict] = []
        skipped = 0
        for opp, code in rows:
            name = (opp.program_name or "").strip()
            if is_junk(name):
                skipped += 1
                continue
            key = (code, name.lower())
            if key in seen:
                skipped += 1
                continue
            seen.add(key)

            tags = [t.strip() for t in (opp.tags or "").split(",") if t.strip()]
            out.append({
                "agency_code": code,
                "program_name": name,
                "funding_amount": opp.funding_amount,
                "eligibility": opp.eligibility,
                "research_area": opp.research_area,
                "deadline": opp.deadline.isoformat() if opp.deadline else None,
                "application_link": opp.application_link,
                "summary": opp.summary,
                "tags": tags,
                "source_url": opp.source_url,
            })

        # Sort: agencies with most schemes first, then by name — nicer default view.
        out.sort(key=lambda r: (r["agency_code"], r["program_name"]))
        OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exported {len(out)} opportunities to {OUT.name}  (skipped {skipped} junk/duplicate rows)")
    finally:
        db.close()


if __name__ == "__main__":
    export()
