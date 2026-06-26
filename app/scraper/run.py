"""CLI to run the scraper.

Examples:
  python -m app.scraper.run --limit 5            # 5 highest-priority agencies
  python -m app.scraper.run --agency IND001      # one agency by code
  python -m app.scraper.run --priority High      # all agencies with that priority
"""
from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.database import SessionLocal, init_db
from app.db.models import Agency
from app.scraper.pipeline import scrape_agency

# Order priorities so "High" gets scraped first when no explicit order exists.
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _select_agencies(db, args) -> list[Agency]:
    stmt = select(Agency)
    if args.agency:
        stmt = stmt.where(Agency.agency_code == args.agency)
    if args.priority:
        stmt = stmt.where(Agency.scraping_priority == args.priority)
    agencies = list(db.scalars(stmt).all())
    agencies.sort(key=lambda a: PRIORITY_RANK.get((a.scraping_priority or "").lower(), 1))
    if args.limit:
        agencies = agencies[: args.limit]
    return agencies


def main():
    ap = argparse.ArgumentParser(description="FundRadar scraper")
    ap.add_argument("--agency", help="single agency code, e.g. IND001")
    ap.add_argument("--priority", help="filter by scraping_priority (e.g. High)")
    ap.add_argument("--limit", type=int, default=5, help="max agencies to scrape")
    ap.add_argument("--max-pages", type=int, default=8, help="max pages per agency")
    args = ap.parse_args()

    init_db()
    db = SessionLocal()
    try:
        agencies = _select_agencies(db, args)
        if not agencies:
            print("No matching agencies. Did you run the seed script?")
            return
        print(f"Scraping {len(agencies)} agenc{'y' if len(agencies)==1 else 'ies'}...\n")
        totals = {"created": 0, "updated": 0, "unchanged": 0, "errors": 0}
        for agency in agencies:
            rep = scrape_agency(db, agency, max_pages=args.max_pages)
            for k in totals:
                totals[k] += getattr(rep, k)
            flag = "ok" if rep.homepage_ok else f"SKIP ({rep.note})"
            print(f"  {rep.agency_code:<8} {agency.name[:28]:<28} "
                  f"cand={rep.candidates:<2} +{rep.created} ~{rep.updated} ={rep.unchanged} "
                  f"err={rep.errors}  {flag}")
        print(f"\nDone. created={totals['created']} updated={totals['updated']} "
              f"unchanged={totals['unchanged']} errors={totals['errors']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
