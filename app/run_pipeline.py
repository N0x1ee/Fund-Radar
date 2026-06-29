"""Full monitoring pipeline: scrape every agency, then AI-extract new/changed pages.

This is the job scheduled to run every 2 days. It is idempotent:
- the scraper upserts by source_url and uses content hashes, so unchanged pages
  are skipped and changed ones are refreshed;
- extraction only processes rows marked processed=False.

Run manually:   python -m app.run_pipeline
Options:        --limit N (only N agencies)  --max-pages N  --no-extract
Logs to:        logs/pipeline_YYYY-MM-DD.log  (and stdout)
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.db.database import SessionLocal, init_db
from app.db.models import Agency, Opportunity
from app.scraper.pipeline import scrape_agency

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def _setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logfile = LOG_DIR / f"pipeline_{datetime.now():%Y-%m-%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        handlers=[logging.FileHandler(logfile, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("fundradar")


def run(limit: int | None, max_pages: int, do_extract: bool) -> None:
    log = _setup_logging()
    log.info("=" * 60)
    log.info("PIPELINE START  provider=%s  limit=%s", settings.llm_provider, limit or "all")
    init_db()
    db = SessionLocal()
    try:
        agencies = list(db.scalars(select(Agency)).all())
        agencies.sort(key=lambda a: PRIORITY_RANK.get((a.scraping_priority or "").lower(), 1))
        if limit:
            agencies = agencies[:limit]

        totals = {"created": 0, "updated": 0, "unchanged": 0, "errors": 0}
        for agency in agencies:
            try:
                rep = scrape_agency(db, agency, max_pages=max_pages)
                for k in totals:
                    totals[k] += getattr(rep, k)
                status = "ok" if rep.homepage_ok else f"skip ({rep.note})"
                log.info("  %-8s %-28s +%d ~%d =%d err%d  %s",
                         rep.agency_code, agency.name[:28], rep.created, rep.updated,
                         rep.unchanged, rep.errors, status)
            except Exception as e:
                log.error("  %-8s FAILED: %s", agency.agency_code, e)
        log.info("SCRAPE DONE  new=%d changed=%d unchanged=%d errors=%d",
                 totals["created"], totals["updated"], totals["unchanged"], totals["errors"])

        if do_extract:
            from app.llm.extraction import extract_opportunity
            from app.llm.providers import get_llm
            llm = get_llm()
            todo = db.scalars(select(Opportunity).where(Opportunity.processed.is_(False))).all()
            log.info("EXTRACT START  %d new/changed opportunities  provider=%s",
                     len(todo), settings.llm_provider)
            done = 0
            for opp in todo:
                try:
                    extract_opportunity(opp, llm=llm)
                    db.commit()
                    done += 1
                    log.info("  extracted %d/%d  %s", done, len(todo),
                             (opp.program_name or "")[:55])
                except Exception as e:
                    log.error("  extract [%s] failed: %s", opp.id, e)
            log.info("EXTRACT DONE  processed=%d/%d", done, len(todo))
        else:
            log.info("EXTRACT SKIPPED (--no-extract)")

        log.info("PIPELINE END")
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser(description="FundRadar full monitoring pipeline")
    ap.add_argument("--limit", type=int, default=None, help="scrape only N agencies")
    ap.add_argument("--max-pages", type=int, default=8, help="max pages per agency")
    ap.add_argument("--no-extract", action="store_true", help="scrape only, skip AI")
    args = ap.parse_args()
    run(limit=args.limit, max_pages=args.max_pages, do_extract=not args.no_extract)


if __name__ == "__main__":
    main()
