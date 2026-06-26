"""Load real, pre-extracted funding opportunities into the database.

These are genuine current calls gathered for the demo. They are already
structured, so we mark them processed=True and let the normalizer fill
amount_value/currency and auto-close past deadlines.

Run:  python -m app.ingest.load_demo_opportunities
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db.database import SessionLocal, init_db
from app.db.models import Agency, Opportunity
from app.llm.normalize import normalize_amount, parse_deadline

JSON_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_opportunities.json"


def load():
    init_db()
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    db = SessionLocal()
    created = skipped = 0
    try:
        for rec in data:
            agency = db.scalar(select(Agency).where(Agency.agency_code == rec["agency_code"]))
            if not agency:
                print(f"  ! no agency {rec['agency_code']} (run seed_agencies first); skipping")
                continue
            # avoid duplicates on re-run
            exists = db.scalar(select(Opportunity).where(
                Opportunity.program_name == rec["program_name"],
                Opportunity.agency_id == agency.id))
            if exists:
                skipped += 1
                continue

            value, currency = normalize_amount(rec.get("funding_amount"))
            deadline = parse_deadline(rec.get("deadline"))
            status = "open"
            if deadline and deadline < date.today():
                status = "closed"
            elif not deadline:
                status = "unknown"

            db.add(Opportunity(
                agency_id=agency.id,
                program_name=rec["program_name"],
                funding_amount=rec.get("funding_amount"),
                amount_value=value,
                currency=currency,
                eligibility=rec.get("eligibility"),
                research_area=rec.get("research_area"),
                deadline=deadline,
                application_link=rec.get("application_link"),
                summary=rec.get("summary"),
                tags=", ".join(rec.get("tags", [])) or None,
                status=status,
                source_url=rec.get("source_url"),
                processed=True,
            ))
            created += 1
        db.commit()
    finally:
        db.close()
    print(f"Loaded demo opportunities -> created: {created}, skipped(existing): {skipped}")


if __name__ == "__main__":
    load()
