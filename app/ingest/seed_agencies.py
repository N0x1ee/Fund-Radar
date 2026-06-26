"""Seed the agencies table from Funding_Agency_Database.xlsx.

Idempotent: upserts on agency_code so re-running won't create duplicates.
Run:  python -m app.ingest.seed_agencies
"""
from pathlib import Path

import openpyxl

from app.db.database import SessionLocal, init_db
from app.db.models import Agency

XLSX_PATH = Path(__file__).resolve().parents[2] / "data" / "Funding_Agency_Database.xlsx"

# spreadsheet header -> model attribute
COLUMN_MAP = {
    "Agency ID": "agency_code",
    "Funding Agency": "name",
    "Country": "country",
    "Category": "category",
    "Funding Type": "funding_type",
    "Website": "website",
    "Research Areas": "research_areas",
    "Eligibility": "eligibility",
    "Deadline Frequency": "deadline_frequency",
    "Current Open Calls": "current_open_calls",
    "Scraping Priority": "scraping_priority",
    "Notes": "notes",
}


def _clean(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def load_rows():
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = [(_clean(h) or "") for h in rows[0]]
    for raw in rows[1:]:
        if not any(raw):
            continue
        record = {}
        for header, value in zip(headers, raw):
            attr = COLUMN_MAP.get(header)
            if attr:
                record[attr] = _clean(value)
        if record.get("agency_code"):
            yield record


def seed():
    init_db()
    db = SessionLocal()
    created, updated = 0, 0
    try:
        for rec in load_rows():
            existing = db.query(Agency).filter_by(agency_code=rec["agency_code"]).one_or_none()
            if existing:
                for k, v in rec.items():
                    setattr(existing, k, v)
                updated += 1
            else:
                db.add(Agency(**rec))
                created += 1
        db.commit()
    finally:
        db.close()
    print(f"Seed complete -> created: {created}, updated: {updated}")


if __name__ == "__main__":
    seed()
