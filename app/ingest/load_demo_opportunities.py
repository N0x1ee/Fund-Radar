"""Load real, pre-extracted funding opportunities into the database.

These are genuine current calls gathered for the demo. They are already
structured, so we mark them processed=True and let the normalizer fill
amount_value/currency and auto-close past deadlines.

Run:  python -m app.ingest.load_demo_opportunities
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db.database import SessionLocal, init_db
from app.db.models import Agency, Opportunity
from app.llm.normalize import english_first, normalize_amount, parse_deadline

# Pages that live under an agency's "call for proposals" section but are NOT
# funding opportunities — they are budget/accounting documents the scraper
# picked up by association. Listing them here keeps the dashboard honest
# instead of padding the count with rows a reviewer would call out.
# Matched case-insensitively against the programme name.
NOT_AN_OPPORTUNITY = (
    "detailed demands for grants",       # ministry budget document
    "grants/funds released to csir",     # annual funds-released disclosure
    "annual report",
    "annual grants",
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# Words that carry no identifying information when comparing two programme
# names, so they're ignored when deciding whether two rows are the same call.
_SIGNATURE_STOPWORDS = {
    "the", "for", "and", "of", "a", "an", "call", "calls", "proposal",
    "proposals", "programme", "program", "scheme", "schemes", "cfp",
    "invitation", "under", "new",
}


def _signature(name: str | None) -> str:
    """A comparable fingerprint of a programme name.

    Strips punctuation, years, and filler words, keeps only the distinctive
    English words, and sorts them — so "Prime Minister's Research Chair (PMRC)"
    and "Prime Minister's Research Chair (PMRC) Scheme" collapse to the same
    fingerprint, while genuinely different programmes do not.
    """
    text = re.sub(r"[^A-Za-z0-9 ]", " ", name or "")     # also drops Hindi text
    text = re.sub(r"\b(19|20)\d{2}\b", " ", text)        # years aren't identifying
    words = [w for w in text.lower().split()
             if len(w) > 2 and w not in _SIGNATURE_STOPWORDS]
    return " ".join(sorted(set(words)))


def _completeness(rec: dict) -> int:
    """How many useful fields this record actually fills in."""
    return sum(1 for f in ("deadline", "funding_amount", "eligibility",
                           "research_area", "summary", "application_link")
               if rec.get(f))


_MERGEABLE_FIELDS = ("funding_amount", "eligibility", "research_area", "deadline",
                     "application_link", "summary", "source_url", "tags")


# Guards that stop an umbrella listing from swallowing the specific calls under
# it. A short, generic name like "Fulbright Fellowships" is a *category*, not a
# duplicate of "Fulbright-Nehru Doctoral Research Fellowships 2027-28".
_MIN_SHARED_WORDS = 3        # the shorter name must be specific enough to trust
_MAX_EXTRA_WORDS = 2         # the longer name may only add a little (a year, an acronym)


def _deadlines_compatible(a: dict, b: dict) -> bool:
    """True when two records don't state *different* deadlines."""
    deadline_a, deadline_b = a.get("deadline"), b.get("deadline")
    if deadline_a and deadline_b:
        return str(deadline_a)[:10] == str(deadline_b)[:10]
    return True              # one is unknown — not evidence that they differ


def _same_programme(a: dict, b: dict) -> bool:
    """Decide whether two records from one agency describe the same call.

    Deliberately cautious: wrongly merging two real programmes hides a funding
    opportunity from the user, which is far worse than showing a near-duplicate.
    A merge needs BOTH a name match and compatible deadlines.

    Name match, either:
      * identical fingerprints — e.g. "…Research Chair (PMRC)" and
        "…Research Chair (PMRC) Scheme" (filler words already stripped); or
      * one fingerprint is a subset of the other AND the shared part is
        specific (>= 3 distinctive words) AND the longer name only adds a word
        or two. This catches "Collaborative Scientific Research Programme
        (CSRP)" vs "CEFIPRA Collaborative Scientific Research Programme (CSRP)
        2026", while refusing to fold four different Fulbright fellowships into
        the generic "Fulbright Fellowships".

    Deadline check: "Horizon Europe" (2027-12-31) and "Horizon Europe – Cancer
    Mission Calls 2026" (2026-09-15) pass the name test but state different
    deadlines, so they stay separate — correctly.
    """
    words_a = set(_signature(a.get("program_name")).split())
    words_b = set(_signature(b.get("program_name")).split())
    if not words_a or not words_b:
        return False

    if words_a == words_b:
        return _deadlines_compatible(a, b)

    shorter, longer = sorted((words_a, words_b), key=len)
    if not shorter < longer:                       # not a subset at all
        return False
    if len(shorter) < _MIN_SHARED_WORDS:           # too generic to be sure
        return False
    if len(longer) - len(shorter) > _MAX_EXTRA_WORDS:
        return False
    return _deadlines_compatible(a, b)


def _merge_into(keep: dict, other: dict) -> None:
    """Fill blanks in `keep` from `other` — a merge, not a discard.

    Duplicate rows usually complement each other: one page carries the funding
    amount, another the eligibility text and a deeper source link. Taking the
    union keeps every fact instead of throwing half of them away.
    """
    for field in _MERGEABLE_FIELDS:
        if not keep.get(field) and other.get(field):
            keep[field] = other[field]


def _drop_near_duplicates(records: list[dict]) -> tuple[list[dict], int]:
    """Collapse repeats of the same call within one agency.

    The same programme often appears on several pages of an agency's site with
    slightly different wording, which looks sloppy on the dashboard. Grouping is
    per agency on purpose: when two *different* agencies both announce a joint
    call (e.g. DST and CSIR on the BRICS programme), those are separate,
    legitimate listings and both are kept.
    """
    kept: list[dict] = []
    by_agency: dict[str, list[dict]] = {}
    dropped = 0

    for rec in records:
        agency = rec.get("agency_code")
        candidates = by_agency.setdefault(agency, [])
        match = next((c for c in candidates if _same_programme(rec, c)), None)

        if match is None:
            kept.append(rec)
            candidates.append(rec)
            continue

        dropped += 1
        if _completeness(rec) > _completeness(match):
            # The newcomer is richer: swap it in, then absorb the old one.
            kept[kept.index(match)] = rec
            candidates[candidates.index(match)] = rec
            _merge_into(rec, match)
        else:
            _merge_into(match, rec)

    return kept, dropped


# A bare domain the page wrote without the scheme, e.g. "www.ias.ac.in/apply".
_BARE_DOMAIN_RE = re.compile(r"^(?:www\.)?[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}(?:[/?#]\S*)?$")

# Placeholder junk that means "no link", not an address.
_NULL_LINKS = {"null", "none", "n/a", "na", "-", "tbd", "nil"}


def _clean_link(value):
    """Return something safe to put in an href, or None.

    AI extraction fills this field from whatever looked like an "apply" target,
    which is not always a URL. Left alone, each of these becomes a broken
    *relative* link — clicking "Apply" on the dashboard would go to
    `/Click here to Register` and 404. So:

    - `"null"` / `"N/A"`            -> None (the UI falls back to the source URL)
    - `"contact@agency.org"`        -> `mailto:contact@agency.org`
    - `"www.agency.org/apply"`      -> `https://www.agency.org/apply`
    - `"a.org; b.org and c.org"`    -> the first one, made absolute
    - `"Click here to Register"`    -> None (it's button text, not an address)
    """
    if not value:
        return None
    s = str(value).strip().strip('"\'')
    if not s or s.lower() in _NULL_LINKS:
        return None

    # Several addresses crammed into one field — keep the first.
    first = re.split(r"[;,]| and ", s, maxsplit=1)[0].strip()

    if first.lower().startswith(("http://", "https://", "mailto:")):
        return first
    if _EMAIL_RE.match(first):
        return f"mailto:{first}"
    if _BARE_DOMAIN_RE.match(first):
        return f"https://{first}"
    return None          # prose, phone numbers, button labels: not a link

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


def _tidy(records: list[dict]) -> tuple[list[dict], int]:
    """Clean every record and drop the ones that aren't funding opportunities.

    Runs as its own pass before anything touches the database, so the
    de-duplication step downstream compares already-cleaned names.
    """
    cleaned: list[dict] = []
    dropped = 0
    for rec in records:
        # Drop aggregate junk rows whose program_name is itself a list of
        # several programs (a broken extraction), and clean any scalar field
        # that arrived as a list so it never renders as raw "[...]".
        pn = rec.get("program_name")
        if isinstance(pn, list) or (isinstance(pn, str) and pn.lstrip().startswith("[") and "'" in pn):
            dropped += 1
            continue
        for _f in ("program_name", "funding_amount", "eligibility",
                   "research_area", "application_link", "summary", "deadline"):
            if _f in rec:
                rec[_f] = _clean_scalar(rec[_f])

        # Show English first when the source page was the Hindi version of
        # an agency site, so titles read naturally for a reviewer.
        rec["program_name"] = english_first(rec.get("program_name"))
        rec["summary"] = english_first(rec.get("summary"))
        rec["application_link"] = _clean_link(rec.get("application_link"))

        # Drop budget/report pages that aren't actually funding calls.
        name_low = (rec.get("program_name") or "").lower()
        if any(pattern in name_low for pattern in NOT_AN_OPPORTUNITY):
            dropped += 1
            continue

        cleaned.append(rec)
    return cleaned, dropped


def load():
    init_db()
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    data, junk = _tidy(data)
    data, dupes = _drop_near_duplicates(data)

    db = SessionLocal()
    created = 0
    skipped = junk + dupes
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
    print(f"Loaded demo opportunities -> created: {created}, skipped: {skipped} "
          f"(non-opportunity/junk: {junk}, duplicates: {dupes})")


if __name__ == "__main__":
    load()
