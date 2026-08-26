"""Fund-size classification for FundRadar.

Turns a messy free-text funding amount into:
  - a number normalised to INR per year
  - a size tier: small | medium | large | xlarge | unknown

This is a NEW file - it does not change app/llm/normalize.py. It exists
because the original parser mis-reads several real records in our data:

  "Rs 3.000/month"                 -> 3 rupees        (German decimal comma)
  "Funded (J-1 visa, travel...)"   -> 1               (grabbed the 1 in "J-1")
  "Up to CHF 1 million"            -> currency None   (CHF unknown)
  "JPY 362,000 per month"          -> currency None   (JPY unknown)
  "Rs. 80,000/- per month"         -> 80,000          (periodicity ignored)

Run  python -m app.core.fundsize  to see how it classifies the current data.
"""
from __future__ import annotations

import re

# --- Currency -> INR. Approximate, for BUCKETING ONLY, not for display. ------
# Edit these if you want; they only decide which tier something lands in.
FX_TO_INR: dict[str, float] = {
    "INR": 1.0,
    "USD": 88.0, "EUR": 96.0, "GBP": 112.0, "CHF": 100.0,
    "JPY": 0.58, "AUD": 58.0, "CAD": 64.0, "SGD": 66.0,
    "SEK": 8.4, "NOK": 8.3, "DKK": 12.9, "AED": 24.0,
}

# Longest / most specific tokens first so "us$" wins over "$".
CURRENCY_TOKENS: list[tuple[str, str]] = [
    ("₹", "INR"), ("rs.", "INR"), ("rs ", "INR"), ("inr", "INR"), ("rupee", "INR"),
    ("us$", "USD"), ("usd", "USD"), ("$", "USD"),
    ("€", "EUR"), ("eur", "EUR"),
    ("£", "GBP"), ("gbp", "GBP"),
    ("chf", "CHF"), ("sfr", "CHF"),
    ("¥", "JPY"), ("jpy", "JPY"),
    ("aud", "AUD"), ("cad", "CAD"), ("sgd", "SGD"),
    ("sek", "SEK"), ("nok", "NOK"), ("dkk", "DKK"), ("aed", "AED"),
]

MULTIPLIERS: dict[str, float] = {
    "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
    "crore": 1e7, "crores": 1e7, "cr": 1e7,
    "k": 1e3, "thousand": 1e3,
    "m": 1e6, "mn": 1e6, "million": 1e6,
    "b": 1e9, "bn": 1e9, "billion": 1e9,
}

# The dashboard shows Hindi translations, so amounts arrive in Devanagari too.
# These are matched by plain substring (\b word boundaries do not work on
# Devanagari), so the longest ones must be tried first.
DEVANAGARI_MULTIPLIERS: dict[str, float] = {
    "करोड़": 1e7, "करोड": 1e7,          # crore
    "लाख": 1e5,                          # lakh
    "हज़ार": 1e3, "हजार": 1e3,           # thousand
    "मिलियन": 1e6,                       # million
    "बिलियन": 1e9, "अरब": 1e9,           # billion
}

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Devanagari words that carry no scale, so seeing them is not a reason to bail:
# periodicity, currency names and common connectors.
HARMLESS_DEVANAGARI = [
    "प्रति", "माह", "प्रतिमाह", "मासिक", "वर्ष", "वार्षिक", "सप्ताह", "साप्ताहिक",
    "रुपये", "रुपए", "रूपये", "रु", "तक", "से", "और", "अधिक", "लगभग", "कुल",
]

_DEVANAGARI_WORD = re.compile(r"[ऀ-ॿ]+")


def _unreadable_devanagari(low: str) -> bool:
    """True when Devanagari remains that we could not account for.

    Those leftover words may well be the scale ("करोड़" = 10 million), so a
    bare number would be off by orders of magnitude. Better to report
    "not specified" than a confidently wrong tier.
    """
    rest = low
    for word in sorted(list(DEVANAGARI_MULTIPLIERS) + HARMLESS_DEVANAGARI, key=len, reverse=True):
        rest = rest.replace(word, " ")
    return bool(_DEVANAGARI_WORD.search(rest))

# per-month / per-week amounts are scaled to a yearly figure so a stipend
# can be compared against a one-off project grant.
PERIODICITY: list[tuple[str, float]] = [
    (r"per\s*month|/\s*month|monthly|p\.?m\.?\b|a\s*month|प्रति\s*माह|प्रतिमाह|मासिक", 12.0),
    (r"per\s*week|/\s*week|weekly|प्रति\s*सप्ताह|साप्ताहिक", 52.0),
    (r"per\s*year|/\s*year|per\s*annum|annually|yearly|p\.?a\.?\b|प्रति\s*वर्ष|वार्षिक", 1.0),
]

# tier -> (label, lower bound inclusive, upper bound exclusive) in INR/year
TIERS: list[tuple[str, str, float, float]] = [
    ("small",  "Small",       0.0,   5e5),
    ("medium", "Medium",      5e5,   5e6),
    ("large",  "Large",       5e6,   5e7),
    ("xlarge", "Extra Large", 5e7,   float("inf")),
]

TIER_LABELS = {k: label for k, label, _, _ in TIERS}
TIER_LABELS["unknown"] = "Not specified"


def detect_currency(text: str) -> str | None:
    low = " " + text.lower().replace(",", "") + " "
    for token, code in CURRENCY_TOKENS:
        if token in low:
            return code
    return None


# A number, then whatever word immediately follows it. The scale word must be
# ATTACHED to the number: "Rs 1,35,000 per month + Rs 15 lakh" holds two
# amounts, and the "lakh" belongs to the second one. Scanning the whole string
# for a multiplier multiplied the stipend by 100,000.
_NUM_UNIT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([a-zऀ-ॿ]+)?")


def _number_and_unit(low: str) -> tuple[float | None, str | None]:
    """First number in the string plus the scale word directly after it."""
    m = _NUM_UNIT.search(low)
    if not m:
        return None, None
    token = m.group(1)
    # European thousands separator: 3.000 means three thousand, not three
    if re.fullmatch(r"\d{1,3}\.\d{3}", token):
        value = float(token.replace(".", ""))
    else:
        value = float(token.replace(",", ""))
    return value, (m.group(2) or None)


def parse_amount(text: str | None) -> dict:
    """Parse free text into {value, currency, per_year_inr, tier, monthly}.

    Returns tier 'unknown' whenever the text has no trustworthy amount.
    """
    blank = {"value": None, "currency": None, "per_year_inr": None,
             "tier": "unknown", "monthly": False}
    if not text:
        return blank

    raw = str(text).strip()
    if not raw:
        return blank

    currency = detect_currency(raw)
    low = raw.lower().replace("/-", " ").translate(DEVANAGARI_DIGITS)

    # Which multiplier appears anywhere in the text? Devanagari first: those
    # need substring matching, and "करोड़" contains "करोड".
    value, unit = _number_and_unit(low)

    factor_mult = None
    hindi = False
    if unit:
        if unit in DEVANAGARI_MULTIPLIERS:
            factor_mult = DEVANAGARI_MULTIPLIERS[unit]
            hindi = True
        elif unit in MULTIPLIERS:
            factor_mult = MULTIPLIERS[unit]

    # A Hindi amount without a symbol ("१० लाख") is rupees - this dashboard's
    # Hindi text is Indian funding, so assume INR rather than give up.
    if currency is None and hindi:
        currency = "INR"

    # A number with NO currency and NO attached multiplier is almost always
    # noise ("J-1 visa", "Category 2 award"). Refuse to guess.
    if currency is None and factor_mult is None:
        return blank

    if _unreadable_devanagari(low):
        return blank

    if value is None or value <= 0:
        return blank
    if factor_mult:
        value *= factor_mult

    factor, monthly = 1.0, False
    for pattern, f in PERIODICITY:
        if re.search(pattern, low):
            factor = f
            monthly = f > 1.0
            break

    per_year = value * factor
    if currency and currency in FX_TO_INR:
        per_year *= FX_TO_INR[currency]
    elif currency is None:
        per_year = None                     # amount known, currency isn't

    tier = "unknown"
    if per_year is not None:
        for key, _label, lo, hi in TIERS:
            if lo <= per_year < hi:
                tier = key
                break

    return {"value": value, "currency": currency, "per_year_inr": per_year,
            "tier": tier, "monthly": monthly}


def tier_of(text: str | None) -> str:
    return parse_amount(text)["tier"]


if __name__ == "__main__":  # pragma: no cover
    import json
    from collections import Counter
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "data" / "demo_opportunities.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    counts = Counter()
    for rec in records:
        amount_text = rec.get("funding_amount")
        result = parse_amount(amount_text)
        counts[result["tier"]] += 1
        if amount_text:
            inr = result["per_year_inr"]
            shown = f"{inr:>16,.0f}" if inr else " " * 16
            print(f"{result['tier']:<8}{shown}  <- {amount_text[:64]}")
    print("\nTier counts:", dict(counts))
