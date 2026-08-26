"""Tests for app/core/fundsize.py — every case here is a real string from our data.

Run:  python test_fundsize.py       (no pytest needed)
"""
from app.core.fundsize import parse_amount

L, C = 100_000, 10_000_000          # lakh, crore

CASES = [
    # text,                                              expected tier, expected INR/yr
    ("Up to Rs 5 crore",                                 "xlarge", 5 * C),
    ("Up to Rs 5 crore per project",                     "xlarge", 5 * C),
    ("Up to Rs 1 crore",                                 "large",  1 * C),
    ("Up to Rs 60 lakh",                                 "large",  60 * L),
    ("Up to Rs 50 lakh",                                 "large",  50 * L),
    ("Rs. 25,00,000 annually (recurring head)",          "medium", 25 * L),
    ("Rs 40,000/month",                                  "small",  4.8 * L),

    # --- the cases the original parser got wrong -------------------------
    # German decimal point: 3.000 means three thousand, not three
    ("Rs 3.000/month (Postdocs), Rs 3.600/month",         "small",  36_000),
    # a bare "1" inside "J-1" is not an amount
    ("Funded (J-1 visa, travel, living costs)",           "unknown", None),
    ("Funded",                                            "unknown", None),
    # currencies the old table did not know
    ("Up to CHF 1 million",                               "xlarge", 100 * C / 10),
    ("JPY 362,000 per month + travel & allowances",       "medium", 362_000 * 12 * 0.58),
    # a monthly stipend must be compared as a yearly figure
    ("Rs. 80,000/- per month plus applicable HRA",         "medium", 9.6 * L),
    ("Rs 1,35,000/- per month (consolidated including HRA)", "medium", 16.2 * L),
    # a range takes the lower bound
    ("EUR 3,000-3,600 per month",                         "medium", 3_000 * 12 * 96),
    ("$89,999/year",                                      "large",  89_999 * 88),
    ("$55,000",                                           "medium", 55_000 * 88),
    ("Up to EUR 220,000",                                 "large",  220_000 * 96),

    # --- Hindi / Devanagari amounts (the dashboard ships Hindi text) -------
    ("\u20b965 \u0915\u0930\u094b\u0921\u093c",                                      "xlarge", 65 * C),
    ("\u20b910 \u0932\u093e\u0916",                                        "medium", 10 * L),
    ("\u20b950,000 \u092a\u094d\u0930\u0924\u093f \u092e\u093e\u0939",                              "medium", 6 * L),
    ("\u20b92 \u0915\u0930\u094b\u0921\u093c \u092a\u094d\u0930\u0924\u093f \u0935\u0930\u094d\u0937",                            "large",  2 * C),
    # Devanagari we cannot interpret must NOT become a tiny number
    ("\u20b965 \u0915\u094b\u0908 \u0905\u091c\u094d\u091e\u093e\u0924 \u0936\u092c\u094d\u0926",                             "unknown", None),

    # --- two amounts in one string: the scale word belongs to the SECOND one,
    #     so it must not be applied to the first (was off by 100,000x) --------
    ("Rs. 1,35,000 per month (consolidated including HRA) + Rs. 15.00 lakh per annum",
                                                          "medium", 16.2 * L),
    ("Rs. 25,000 per month (fellowship) + Rs. 15.00 lakh contingency",
                                                          "small",  3 * L),
    ("Up to Rs 3 crores/month",                           "xlarge", 36 * C),
    ("Rs 50,000 per month plus Rs 2 crore project cost",  "medium", 6 * L),

    # --- edges -----------------------------------------------------------
    (None,                                                "unknown", None),
    ("",                                                  "unknown", None),
    ("Category 2 award",                                  "unknown", None),
    ("Varies by project",                                 "unknown", None),
]


def main() -> int:
    failures = []
    for text, want_tier, want_inr in CASES:
        got = parse_amount(text)
        if got["tier"] != want_tier:
            failures.append(f"tier  {text!r}: expected {want_tier}, got {got['tier']}")
        elif want_inr is not None and abs((got["per_year_inr"] or 0) - want_inr) > 1:
            failures.append(f"value {text!r}: expected {want_inr:,.0f}, got {got['per_year_inr']:,.0f}")

    for line in failures:
        print("FAIL:", line)
    print(f"\n{len(CASES) - len(failures)}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
