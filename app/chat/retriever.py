"""Chatbot retrieval: turn a plain-language question into matching opportunities.

Pure functions (no database, no LLM) so they're easy to test:
- parse_query(text)  -> intents: status, min_amount, country hint, search terms
- rank(opps, parsed) -> opportunities sorted by relevance, filtered by intents

`opps` are plain dicts so this works the same in tests and in the live bot.
"""
from __future__ import annotations

import re

from app.llm.normalize import normalize_amount

STOPWORDS = {
    "the","a","an","is","are","for","of","to","in","on","what","which","show","me",
    "can","i","apply","funding","grant","grants","opportunity","opportunities","with",
    "and","or","any","there","that","do","you","have","get","find","list","give","all",
    "available","open","please","tell","about","under","whose","who","how","much",
}
COUNTRY_WORDS = {
    "india","indian","france","french","germany","german","switzerland","swiss",
    "japan","japanese","usa","us","american","europe","european","taiwan","finland",
    "israel","brics","asean",
}


def parse_query(text: str) -> dict:
    q = text.lower()

    status = None
    if any(w in q for w in ("closed", "expired", "past")):
        status = "closed"
    elif any(w in q for w in ("open", "available", "currently", "active", "ongoing")):
        status = "open"

    min_amount = None
    m = re.search(
        r"(?:above|over|more than|greater than|at least|minimum|min|>)\s*"
        r"(₹|rs\.?|inr|\$|usd|us\$|€|eur|£|gbp)?\s*([\d.,]+)\s*"
        r"(lakhs?|lac|crores?|cr|millions?|mn|m|k|thousand|billions?|bn)?",
        q,
    )
    if m:
        amt_text = f"{m.group(1) or ''}{m.group(2)} {m.group(3) or ''}"
        val, _ = normalize_amount(amt_text)
        min_amount = val

    countries = [w for w in COUNTRY_WORDS if re.search(rf"\b{w}\b", q)]
    terms = [w for w in re.findall(r"[a-z0-9]+", q) if w not in STOPWORDS and len(w) > 2]
    return {"status": status, "min_amount": min_amount, "countries": countries, "terms": terms}


def _haystack(o: dict) -> str:
    parts = [o.get("program_name"), o.get("research_area"), o.get("tags"),
             o.get("eligibility"), o.get("summary"), o.get("agency_name"), o.get("country")]
    return " ".join(p for p in parts if p).lower()


def score(o: dict, parsed: dict) -> int:
    text = _haystack(o)
    s = 0
    for term in parsed["terms"]:
        if term in text:
            # weight matches in the title/area higher than body
            s += 3 if term in (o.get("program_name", "") + " " + (o.get("research_area") or "")).lower() else 1
    for c in parsed["countries"]:
        if c in text:
            s += 2
    return s


def rank(opps: list[dict], parsed: dict, limit: int = 8) -> list[dict]:
    out = []
    for o in opps:
        if parsed["status"] and o.get("status") != parsed["status"]:
            continue
        if parsed["min_amount"] is not None:
            av = o.get("amount_value")
            if av is None or float(av) < parsed["min_amount"]:
                continue
        sc = score(o, parsed)
        # if the user gave only filters (no search terms), keep everything that passed
        if parsed["terms"] or parsed["countries"]:
            if sc <= 0:
                continue
        out.append((sc, o))
    # sort by score, then open-first, then soonest deadline
    out.sort(key=lambda t: (-t[0], t[1].get("status") != "open", t[1].get("deadline") or "9999"))
    return [o for _, o in out[:limit]]
