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


import ast


def _first_meaningful(items):
    """First non-empty, non-null element of a list (as a string), else None."""
    for x in items:
        if x is None:
            continue
        s = str(x).strip()
        if s and s.lower() != "null":
            return s
    return None


def _clean_scalar(value):
    """Coerce a value that should be a single string.

    Bad AI extractions sometimes store a Python-list *string* (e.g.
    "['a', 'b']") in a scalar field, which then renders as raw brackets in the
    chatbot. Turn any such value into its first meaningful element.
    """
    if isinstance(value, list):
        return _first_meaningful(value)
    if isinstance(value, str) and value.lstrip().startswith("[") and ("'" in value or '"' in value):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value
        if isinstance(parsed, list):
            return _first_meaningful(parsed)
    return value


def load():
    init_db()
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    db = SessionLocal()
    created = skipped = 0
    try:
        for rec in data:
            # Drop aggregate junk rows whose program_name is itself a list of
            # several programs (a broken extraction), and clean any scalar field
            # that arrived as a list so it never renders as raw "[...]".
            pn = rec.get("program_name")
            if isinstance(pn, list) or (isinstance(pn, str) and pn.lstrip().startswith("[") and "'" in pn):
                skipped += 1
                continue
            for _f in ("program_name", "funding_amount", "eligibility",
                       "research_area", "application_link", "summary", "deadline"):
                if _f in rec:
                    rec[_f] = _clean_scalar(rec[_f])

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
