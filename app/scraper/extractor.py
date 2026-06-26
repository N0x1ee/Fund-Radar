"""Turn a fetched page into a raw opportunity record.

This is the *raw* stage: we pull clean text, a title, and a content hash for
change detection. Phase 3 (AI) refines this raw text into structured fields
(amount, eligibility, deadline, etc.).
"""
from __future__ import annotations

import hashlib
import re


def extract_text(html: str) -> str:
    """Strip scripts/styles/markup and return readable text."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def page_title(html: str) -> str | None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return re.sub(r"\s+", " ", soup.title.string).strip()
    h1 = soup.find("h1")
    if h1:
        return re.sub(r"\s+", " ", h1.get_text(" ", strip=True)).strip()
    return None


def guess_program_name(link_text: str | None, title: str | None, url: str) -> str:
    """Best-effort program name before AI cleans it up."""
    for candidate in (link_text, title):
        if candidate and len(candidate.strip()) >= 4:
            return candidate.strip()[:480]
    return url


def content_hash(text: str) -> str:
    """Stable hash of normalized text, used to detect changes between scrapes."""
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
