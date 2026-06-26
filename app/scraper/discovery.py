"""Find funding-related pages on an agency website.

Two parts:
- score_link(text, href): pure relevance heuristic (no deps) -> easy to test.
- find_funding_links(html, base_url): parse anchors with BeautifulSoup, score
  them, resolve relative URLs, return ranked unique candidates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

# Words that signal a funding opportunity page. Weighted: strong vs supporting.
STRONG_KEYWORDS = [
    "grant", "fellowship", "scholarship", "call for proposal", "call for proposals",
    "funding opportunit", "request for proposal", "rfp", "funding scheme",
]
SUPPORTING_KEYWORDS = [
    "funding", "fund", "award", "scheme", "programme", "program", "proposal",
    "apply", "application", "opportunit", "research support", "deadline",
]
# Pages we never want to treat as opportunities.
NEGATIVE_KEYWORDS = ["login", "privacy", "sitemap", "contact us", "careers", "tender"]


@dataclass(frozen=True)
class CandidateLink:
    url: str
    text: str
    score: int


def score_link(text: str, href: str) -> int:
    """Heuristic relevance score for a link. Higher = more likely funding page."""
    blob = f"{text} {href}".lower()
    score = 0
    for kw in STRONG_KEYWORDS:
        if kw in blob:
            score += 5
    for kw in SUPPORTING_KEYWORDS:
        if kw in blob:
            score += 2
    for kw in NEGATIVE_KEYWORDS:
        if kw in blob:
            score -= 4
    # Slight boost if the URL path itself contains a strong signal.
    path = urlparse(href).path.lower()
    if any(kw.replace(" ", "-") in path or kw.replace(" ", "") in path for kw in STRONG_KEYWORDS):
        score += 2
    return score


def find_funding_links(html: str, base_url: str, *, min_score: int = 4, limit: int = 25) -> list[CandidateLink]:
    """Extract and rank funding-related links from a page."""
    from bs4 import BeautifulSoup  # local import keeps module importable without bs4

    soup = BeautifulSoup(html, "html.parser")
    seen: dict[str, CandidateLink] = {}
    base_host = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        abs_url = urljoin(base_url, href)
        # Stay on the agency's own domain.
        if urlparse(abs_url).netloc and urlparse(abs_url).netloc != base_host:
            continue
        s = score_link(text, abs_url)
        if s >= min_score:
            existing = seen.get(abs_url)
            if not existing or s > existing.score:
                seen[abs_url] = CandidateLink(url=abs_url, text=text or abs_url, score=s)

    return sorted(seen.values(), key=lambda c: c.score, reverse=True)[:limit]
