"""AI extraction: raw scraped text -> structured opportunity fields (Phase 3).

Flow per opportunity:
  build_prompt(raw_text) -> llm.complete() -> parse_llm_json() -> apply_extraction()

The LLM is told to return strict JSON. We then normalize the amount and deadline
with the pure helpers in normalize.py and mark the record processed.

Top-level imports are stdlib only so this module loads without the LLM SDKs;
the provider is imported lazily inside extract_opportunity().
"""
from __future__ import annotations

import json
import re
from datetime import date

from app.llm.normalize import normalize_amount, parse_deadline

EXTRACTION_FIELDS = [
    "program_name", "funding_amount", "eligibility", "research_area",
    "deadline", "application_link", "contact_info", "summary", "tags", "status",
]

SYSTEM_PROMPT = (
    "You extract structured funding-opportunity data from raw web page text. "
    "Return ONLY a JSON object, no prose, no markdown fences."
)


def build_prompt(raw_text: str, *, max_chars: int = 8000) -> str:
    snippet = raw_text[:max_chars]
    return (
        "From the funding opportunity page text below, extract these fields as JSON:\n"
        '- program_name (the official scheme/fellowship/grant name. Ignore navigation '
        'or link text like "Read More", "Apply", "Click here", "Funding opportunities", '
        '"Programmsuche".)\n'
        '- funding_amount (a SHORT amount only, e.g. "Rs 35,000/month", '
        '"Up to Rs 50 lakh", "$10,000", or null if no specific figure is stated. '
        'Never write a sentence; put descriptions in summary/eligibility.)\n'
        '- eligibility (string or null)\n'
        '- research_area (short string, e.g. "Artificial Intelligence", or null)\n'
        '- deadline (the LAST DATE to apply as YYYY-MM-DD. Look hard for "last date", '
        '"deadline", "closing date", "apply by", "submission by", "due". null if truly none.)\n'
        '- application_link (string or null)\n'
        '- contact_info (string or null)\n'
        '- summary (2-3 sentence plain summary)\n'
        '- tags (array of short topic strings)\n'
        '- status ("open", "closed", or "unknown")\n\n'
        "Return null for anything not present. JSON only.\n\n"
        f"PAGE TEXT:\n{snippet}"
    )


def parse_llm_json(text: str) -> dict:
    """Parse a JSON object from an LLM response, tolerating code fences/prose."""
    if not text:
        return {}
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # fall back: grab the first {...} block
    m = re.search(r"\{.*\}", cleaned, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


def apply_extraction(opp, data: dict) -> None:
    """Write extracted/normalized fields onto an Opportunity ORM object."""
    if not data:
        opp.processed = True
        return

    if data.get("program_name"):
        opp.program_name = str(data["program_name"])[:480]
    opp.funding_amount = _s(data.get("funding_amount"))
    opp.eligibility = _s(data.get("eligibility"))
    opp.research_area = _s(data.get("research_area"), limit=255)
    opp.contact_info = _s(data.get("contact_info"), limit=500)
    opp.summary = _s(data.get("summary"))
    if data.get("application_link"):
        opp.application_link = str(data["application_link"])[:800]

    tags = data.get("tags")
    if isinstance(tags, list):
        opp.tags = ", ".join(str(t) for t in tags)[:1000]
    elif tags:
        opp.tags = str(tags)[:1000]

    # normalize amount + deadline
    value, currency = normalize_amount(opp.funding_amount)
    opp.amount_value = value
    opp.currency = currency

    deadline = parse_deadline(data.get("deadline"))
    opp.deadline = deadline

    # status: trust LLM, but a past deadline means closed
    status = (data.get("status") or "unknown").lower()
    if status not in {"open", "closed", "unknown"}:
        status = "unknown"
    if deadline and deadline < date.today():
        status = "closed"
    opp.status = status

    opp.processed = True


def _s(v, limit: int | None = None):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in {"null", "none", "n/a"}:
        return None
    return s[:limit] if limit else s


def extract_opportunity(opp, llm=None) -> dict:
    """Run the LLM on one opportunity's raw_text and apply the result."""
    if llm is None:
        from app.llm.providers import get_llm
        llm = get_llm()
    if not opp.raw_text:
        opp.processed = True
        return {}
    response = llm.complete(build_prompt(opp.raw_text), system=SYSTEM_PROMPT)
    data = parse_llm_json(response)
    apply_extraction(opp, data)
    return data
