"""Remove duplicate opportunities, keeping the most complete row of each group.

Duplicates happen when the same programme is scraped from several URLs
(e.g. "Horizon Europe" appearing on 7 different pages). Rows are grouped by
(agency_id, normalized program_name); within each group the row with the most
filled-in fields wins and the rest are deleted.

Run:  python -m app.ingest.dedupe            # report + delete
      python -m app.ingest.dedupe --dry-run  # report only
"""
from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.database import SessionLocal, init_db
from app.db.models import Opportunity


def _score(o: Opportunity) -> int:
    """How complete is this row? Higher = better."""
    return sum(1 for v in (
        o.deadline, o.amount_value, o.funding_amount, o.eligibility,
        o.research_area, o.summary, o.application_link, o.contact_info,
    ) if v)


def main() -> None:
    ap = argparse.ArgumentParser(description="FundRadar duplicate cleaner")
    ap.add_argument("--dry-run", action="store_true", help="report, don't delete")
    args = ap.parse_args()

    init_db()
    db = SessionLocal()
    try:
        rows = db.scalars(select(Opportunity)).all()
        groups: dict[tuple, list[Opportunity]] = {}
        for o in rows:
            key = (o.agency_id, (o.program_name or "").strip().lower())
            groups.setdefault(key, []).append(o)

        removed = 0
        for key, group in groups.items():
            if len(group) < 2 or not key[1]:
                continue
            # keep the most complete row (ties: newest id)
            group.sort(key=lambda o: (_score(o), o.id), reverse=True)
            keep, rest = group[0], group[1:]
            print(f'"{keep.program_name}" x{len(group)} -> keeping id={keep.id}, '
                  f"removing {[o.id for o in rest]}")
            for o in rest:
                removed += 1
                if not args.dry_run:
                    db.delete(o)
        # also close anything whose deadline has passed
        from datetime import date
        expired = [o for o in rows if o.deadline and o.deadline < date.today()
                   and o.status == "open"]
        for o in expired:
            print(f'closing (deadline passed): "{o.program_name}" ({o.deadline})')
            if not args.dry_run:
                o.status = "closed"

        if not args.dry_run:
            db.commit()
        print(f"\n{'Would remove' if args.dry_run else 'Removed'} {removed} duplicates, "
              f"{'would close' if args.dry_run else 'closed'} {len(expired)} expired, "
              f"out of {len(rows)} opportunities.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
