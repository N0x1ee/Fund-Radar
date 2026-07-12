"""One-off: correct dead/wrong agency website URLs found during the July 2026
coverage audit (the old domains no longer resolve, so their scrapers always
failed with DNS errors).

Verified replacements:
- ASEAN-India S&T  : aseanindiast.in  -> aistic.gov.in (official AISTDF portal)
- BRICS STI        : https -> http    (their server does not serve HTTPS)
- Indo-Swiss JRP   : indo-swiss-jrp.org -> SNSF programme page (manages the calls)
- Sree PVF         : spvfoundation.org -> sreepvf.org

Run:  python -m app.ingest.fix_urls
"""
from __future__ import annotations

from sqlalchemy import select

from app.db.database import SessionLocal, init_db
from app.db.models import Agency

FIXES = {
    "https://aseanindiast.in": "https://www.aistic.gov.in",
    "https://brics-sti.org": "http://brics-sti.org",
    "https://indo-swiss-jrp.org":
        "https://www.snf.ch/en/UKQxILyeulyH9qfi/funding/programmes/bilateral-programmes-indo",
    "https://spvfoundation.org": "https://sreepvf.org",
}


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        changed = 0
        for a in db.scalars(select(Agency)).all():
            new = FIXES.get((a.website or "").rstrip("/"))
            if new:
                print(f"{a.name}: {a.website} -> {new}")
                a.website = new
                changed += 1
        db.commit()
        print(f"\nUpdated {changed} agency URLs.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
