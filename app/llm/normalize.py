"""Pure normalization helpers for AI-extracted fields.

No external dependencies so they're easy to test in isolation. Used by the
extraction step to turn messy strings into clean values:
- normalize_amount("Rs 10 lakh") -> (1000000.0, "INR")
- parse_deadline("30 June 2026")  -> date(2026, 6, 30)
"""
from __future__ import annotations

import re
from datetime import date, datetime

# --- Amount parsing ---------------------------------------------------------

CURRENCY_SIGNS = {
    "₹": "INR", "rs": "INR", "inr": "INR", "rupee": "INR",
    "$": "USD", "usd": "USD", "us$": "USD",
    "€": "EUR", "eur": "EUR",
    "£": "GBP", "gbp": "GBP",
}
INDIAN_MULTIPLIERS = {"lakh": 100_000, "lakhs": 100_000, "lac": 100_000,
                      "crore": 10_000_000, "crores": 10_000_000, "cr": 10_000_000}
WESTERN_MULTIPLIERS = {"k": 1_000, "thousand": 1_000,
                       "m": 1_000_000, "mn": 1_000_000, "million": 1_000_000,
                       "b": 1_000_000_000, "bn": 1_000_000_000, "billion": 1_000_000_000}


def detect_currency(text: str) -> str | None:
    low = text.lower()
    for sign, code in CURRENCY_SIGNS.items():
        if sign in low:
            return code
    return None


def normalize_amount(text: str | None) -> tuple[float | None, str | None]:
    """Extract a numeric value and currency from a free-text amount string."""
    if not text:
        return None, None
    # strip commas (thousand/lakh separators) and the Indian "/-" suffix
    low = text.lower().replace(",", "").replace("/-", " ")
    currency = detect_currency(text)

    # number possibly followed by a multiplier word
    m = re.search(r"(\d+(?:\.\d+)?)\s*([a-z]+)?", low)
    if not m:
        return None, currency
    value = float(m.group(1))
    unit = (m.group(2) or "").strip()
    if unit in INDIAN_MULTIPLIERS:
        value *= INDIAN_MULTIPLIERS[unit]
    elif unit in WESTERN_MULTIPLIERS:
        value *= WESTERN_MULTIPLIERS[unit]
    return value, currency


# --- Date parsing -----------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
    "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y",
    "%B %d, %Y", "%b %d, %Y", "%d %B, %Y",
]


def parse_deadline(text: str | None) -> date | None:
    """Parse common deadline formats. Returns None if nothing parseable."""
    if not text:
        return None
    # LLMs occasionally return a list of dates — take the first one.
    if isinstance(text, (list, tuple)):
        text = text[0] if text else None
        if not text:
            return None
    s = str(text).strip()
    # ISO first (handles values the LLM is told to return)
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


# --- Language tidy-up -------------------------------------------------------

# Devanagari block: covers Hindi/Marathi/Sanskrit text.
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")

# "देवनागरी शीर्षक (English Title)" -> capture the trailing parenthesised part.
# Non-greedy body + end anchor so we take the LAST bracketed group, which is
# where the translation sits.
_TRAILING_PARENS = re.compile(r"^(?P<head>.*?)\s*\((?P<inside>[^()]*(?:\([^()]*\)[^()]*)*)\)\s*$",
                              re.DOTALL)


def has_devanagari(text: str | None) -> bool:
    """True if the string contains Hindi/Devanagari characters."""
    return bool(text) and bool(_DEVANAGARI.search(text))


def english_first(text: str | None) -> str | None:
    """Promote a bracketed English translation to the front of the string.

    Several Indian agency sites (notably CSIR) are scraped from their Hindi
    (/hi/) pages, so the AI returns titles shaped like:

        "रोलैंड फैलोशिप (Rowland Fellowship)"

    An English-speaking reviewer should see the English first, so this rewrites
    it to:

        "Rowland Fellowship (रोलैंड फैलोशिप)"

    Rules — deliberately conservative, because a wrong swap is worse than no
    swap: only act when the head really is Devanagari AND the bracketed part
    really is not. Anything else (ordinary acronyms like "(PMRC)", pure-English
    titles, pure-Hindi titles with no translation) is returned untouched.
    """
    if not text:
        return text
    s = str(text).strip()
    if not has_devanagari(s):
        return s                      # already English — nothing to do

    match = _TRAILING_PARENS.match(s)
    if not match:
        return s                      # no bracketed translation available

    head = match.group("head").strip()
    inside = match.group("inside").strip()

    # Only swap when the two halves are genuinely different scripts.
    if not head or not inside:
        return s
    if not has_devanagari(head) or has_devanagari(inside):
        return s
    # Require the translation to contain real words, not just "(2026)" or "(a)".
    if not re.search(r"[A-Za-z]{3}", inside):
        return s

    return f"{inside} ({head})"
