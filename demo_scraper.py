"""Offline demo of the scraper pipeline — run it to SEE how scraping works.

Uses the project's REAL functions (discovery + extractor, BeautifulSoup-based)
against a fake agency site held in memory, so it needs no internet.

Run:
    python demo_scraper.py

To try a REAL website instead, set LIVE_URL below to an agency URL and run again
(this will use the real network fetcher and respect robots.txt + rate limits).
"""
from __future__ import annotations

from app.scraper.discovery import find_funding_links
from app.scraper.extractor import extract_text, page_title, guess_program_name, content_hash

LIVE_URL = None  # e.g. "https://dst.gov.in" to scrape a real site instead of the fixture

# --- a fake agency website (homepage + two funding pages) -------------------
FIXTURE = {
    "https://nsc.example.gov": """
      <html><body>
        <a href="/about">About Us</a>
        <a href="/schemes/research-grants">Research Grants Scheme</a>
        <a href="/fellowships/doctoral">Doctoral Fellowship Programme</a>
        <a href="/login">Login</a>
        <a href="https://twitter.com/nsc">Follow us</a>
        <a href="/contact">Contact Us</a>
      </body></html>""",
    "https://nsc.example.gov/schemes/research-grants": """
      <html><body><h1>Research Grants Scheme 2026</h1>
        <p>The National Science Council invites proposals. Funding up to
        Rs 50,00,000 per project for researchers in Indian institutions.
        Eligibility: faculty with a PhD. Deadline: 30 September 2026.
        Contact: grants@nsc.example.gov</p></body></html>""",
    "https://nsc.example.gov/fellowships/doctoral": """
      <html><body><h1>Doctoral Fellowship Programme</h1>
        <p>Monthly fellowship of Rs 35,000 for PhD students in science and
        engineering. Open to Indian citizens under 28. Last date: 15 August 2026.
        </p></body></html>""",
}


def get_html(url: str) -> str:
    if LIVE_URL:
        from app.scraper.fetcher import fetch
        return fetch(url).html
    return FIXTURE.get(url, "")


def main():
    home = LIVE_URL or "https://nsc.example.gov"
    print(f"\nScraping homepage: {home}")
    home_html = get_html(home)
    print(f"  downloaded {len(home_html)} chars")

    print("\nStep A — discover & rank funding links (real find_funding_links):")
    candidates = find_funding_links(home_html, home)
    for c in candidates:
        print(f"  score={c.score:>3}  {c.text[:40]:<40} -> {c.url}")
    if not candidates:
        print("  (none found — likely a JS-heavy site; needs Playwright, Phase 2b)")

    print("\nStep B — visit each page, extract text, build a raw record:")
    for c in candidates:
        html = get_html(c.url)
        text = extract_text(html)
        if len(text) < 100:
            print(f"  skip (too thin): {c.url}")
            continue
        name = guess_program_name(c.text, page_title(html), c.url)
        print(f"  • {name}")
        print(f"      url:   {c.url}")
        print(f"      hash:  {content_hash(text)[:16]}  (used to detect changes later)")
        print(f"      text:  {text[:80]}...")

    print("\nThat raw text is what the AI step (python -m app.llm.run_extraction)")
    print("turns into amount / deadline / eligibility / summary / tags.\n")


if __name__ == "__main__":
    main()
