"""Add a new funding-agency website to FundRadar with one command.

Writes the agency into BOTH:
  1. data/Funding_Agency_Database.xlsx  (the source of truth), and
  2. the database (so it's scraped on the very next pipeline run).

Example:
    python -m app.ingest.add_agency --name "Wellcome Trust" \
        --website https://wellcome.org --country "United Kingdom" \
        --category "Charity/Foundation" --priority high

Only --name and --website are required. The agency code (e.g. UNI004) is
generated automatically from the country unless you pass --code.

After adding, either wait for the next scheduled run, or scrape it now:
    python -m app.scraper.run --agency <CODE>
"""
from __future__ import annotations

import argparse
import re

import openpyxl

from app.db.database import SessionLocal, init_db
from app.db.models import Agency
from app.ingest.seed_agencies import COLUMN_MAP, XLSX_PATH, _clean


def _next_code(db, country: str) -> str:
    """Generate the next free code like IND007 from the country name."""
    prefix = re.sub(r"[^A-Za-z]", "", country or "GEN").upper()[:3] or "GEN"
    codes = [a.agency_code for a in db.query(Agency).all()
             if a.agency_code and a.agency_code.startswith(prefix)]
    highest = 0
    for c in codes:
        m = re.search(r"(\d+)$", c)
        if m:
            highest = max(highest, int(m.group(1)))
    return f"{prefix}{highest + 1:03d}"


def _append_to_excel(record: dict) -> None:
    """Append one row to the spreadsheet, matching its existing headers."""
    wb = openpyxl.load_workbook(XLSX_PATH)
    ws = wb.active
    headers = [(_clean(c.value) or "") for c in ws[1]]
    row = []
    for header in headers:
        attr = COLUMN_MAP.get(header)
        row.append(record.get(attr) if attr else None)
    ws.append(row)
    wb.save(XLSX_PATH)


def add(record: dict) -> str:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Agency).filter_by(website=record["website"]).one_or_none():
            raise SystemExit(f"An agency with website {record['website']} already exists.")
        if not record.get("agency_code"):
            record["agency_code"] = _next_code(db, record.get("country") or "")
        elif db.query(Agency).filter_by(agency_code=record["agency_code"]).one_or_none():
            raise SystemExit(f"Agency code {record['agency_code']} already exists.")
        _append_to_excel(record)
        db.add(Agency(**record))
        db.commit()
        return record["agency_code"]
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser(description="Add a funding-agency website to FundRadar")
    ap.add_argument("--name", required=True, help='e.g. "Wellcome Trust"')
    ap.add_argument("--website", required=True, help="https://... homepage of the agency")
    ap.add_argument("--country", default="", help='e.g. "India", "United Kingdom"')
    ap.add_argument("--category", default="", help='e.g. "Government", "Charity/Foundation"')
    ap.add_argument("--funding-type", default="", help='e.g. "Research grants, fellowships"')
    ap.add_argument("--areas", default="", help="research areas it funds")
    ap.add_argument("--eligibility", default="", help="who can apply")
    ap.add_argument("--priority", default="medium", choices=["high", "medium", "low"],
                    help="scraping priority (high = scraped first)")
    ap.add_argument("--notes", default="")
    ap.add_argument("--code", default=None, help="agency code, e.g. UK001 (auto if omitted)")
    args = ap.parse_args()

    record = {
        "agency_code": args.code,
        "name": args.name.strip(),
        "website": args.website.strip().rstrip("/"),
        "country": _clean(args.country),
        "category": _clean(args.category),
        "funding_type": _clean(args.funding_type),
        "research_areas": _clean(args.areas),
        "eligibility": _clean(args.eligibility),
        "scraping_priority": args.priority,
        "notes": _clean(args.notes),
    }
    code = add(record)
    print(f"Added {record['name']}  ->  code {code}")
    print(f"Scrape it now with:  python -m app.scraper.run --agency {code}")
    print("Or commit + push, and the scheduled GitHub Action picks it up next run.")


if __name__ == "__main__":
    main()
