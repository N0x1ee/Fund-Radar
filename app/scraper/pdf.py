"""Download and extract text from PDF funding documents.

Some agencies (notably the Indian science academies) publish scheme details
only as PDFs. The HTML scraper captures the link but never the contents, so the
opportunity ends up with a title and nothing else. This module downloads such a
PDF politely and pulls its text, so the SAME AI extraction stage can run on it.

Scope: text-based PDFs. Scanned / image-only PDFs would need OCR, which is
heavier and left for later -- we detect that case and report it instead of
guessing.

Imports note: httpx and the fetcher politeness helpers are imported lazily
inside fetch_pdf_text(), the same way extractor.py imports BeautifulSoup. That
keeps extract_text() usable on raw bytes without requiring httpx.
"""
from __future__ import annotations

import io
import re
from urllib.parse import urlparse

MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB safety cap, avoids huge downloads
MIN_USEFUL_CHARS = 50             # below this we assume no real text was found


def looks_like_pdf(url: str) -> bool:
    """True if the URL path points at a .pdf file (ignores query string)."""
    return urlparse(url).path.lower().endswith(".pdf")


def is_pdf_bytes(data: bytes) -> bool:
    """Every PDF file starts with the magic marker `%PDF-`."""
    return data[:5] == b"%PDF-"


def extract_text(data: bytes) -> str:
    """Pull readable text from PDF bytes using pypdf. Returns '' on failure."""
    try:
        from pypdf import PdfReader
    except Exception:
        return ""  # dependency missing -> degrade safely, pipeline keeps running
    try:
        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue  # one bad page shouldn't lose the rest
        text = "\n".join(parts)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except Exception:
        return ""


def fetch_pdf_text(url: str, *, timeout: float | None = None) -> tuple[str, str | None]:
    """Download a PDF politely and extract its text.

    Returns (text, None) on success, or ("", reason) on any failure so the
    caller can count it as an error without crashing the scrape.
    """
    import httpx
    from app.scraper.fetcher import (
        DEFAULT_TIMEOUT,
        USER_AGENT,
        _robots_allows,
        _throttle,
    )

    if timeout is None:
        timeout = DEFAULT_TIMEOUT

    if not _robots_allows(url):
        return "", "blocked by robots.txt"

    _throttle(url)
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout,
                          headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
    except httpx.HTTPError as e:
        return "", f"download failed: {e}"

    if resp.status_code >= 400:
        return "", f"status {resp.status_code}"

    data = resp.content
    if len(data) > MAX_PDF_BYTES:
        return "", f"pdf too large ({len(data)} bytes)"
    if not is_pdf_bytes(data):
        return "", "not a PDF (missing %PDF header)"

    text = extract_text(data)
    if len(text.strip()) < MIN_USEFUL_CHARS:
        # Got a PDF but almost no text -> most likely a scanned image PDF.
        return "", "no extractable text (scanned PDF? needs OCR)"
    return text, None
