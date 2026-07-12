"""CLI: run AI extraction over scraped-but-unprocessed opportunities (Phase 3).

Examples:
  python -m app.llm.run_extraction                 # process all unprocessed
  python -m app.llm.run_extraction --limit 10      # cap how many
  python -m app.llm.run_extraction --reprocess     # redo all, even processed

Requires LLM_PROVIDER set in .env (gemini recommended; mock just marks rows done).
"""
from __future__ import annotations

import argparse

from sqlalchemy import select

from app.config import settings
from app.db.database import SessionLocal, init_db
from app.db.models import Opportunity
from app.llm.extraction import extract_opportunity
from app.llm.providers import get_llm


def main():
    ap = argparse.ArgumentParser(description="FundRadar AI extraction")
    ap.add_argument("--limit", type=int, default=None, help="max records to process")
    ap.add_argument("--reprocess", action="store_true", help="include already-processed rows")
    args = ap.parse_args()

    init_db()
    if settings.llm_provider == "mock":
        print("WARNING: LLM_PROVIDER=mock — rows will be marked processed without real extraction.")
        print("Set LLM_PROVIDER=gemini and GEMINI_API_KEY in .env for real results.\n")

    llm = get_llm()
    db = SessionLocal()
    try:
        stmt = select(Opportunity)
        if not args.reprocess:
            stmt = stmt.where(Opportunity.processed.is_(False))
        if args.limit:
            stmt = stmt.limit(args.limit)
        rows = db.scalars(stmt).all()

        if not rows:
            print("Nothing to process. Run the scraper first.")
            return

        print(f"Extracting {len(rows)} opportunit{'y' if len(rows)==1 else 'ies'} "
              f"with provider='{settings.llm_provider}'...\n")
        ok = 0
        for opp in rows:
            try:
                data = extract_opportunity(opp, llm=llm)
                ok += 1
                if data.get("is_funding_opportunity") is False:
                    print(f"  [{opp.id}] skipped (not an opportunity)")
                    db.delete(opp)
                else:
                    name = (opp.program_name or "")[:40]
                    print(f"  [{opp.id}] {name:<40} amount={opp.amount_value} "
                          f"deadline={opp.deadline} status={opp.status}")
            except Exception as e:
                print(f"  [{opp.id}] ERROR: {e}")
            db.commit()
        print(f"\nDone. processed {ok}/{len(rows)}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
