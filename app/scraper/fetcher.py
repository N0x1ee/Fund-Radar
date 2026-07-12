"""Polite HTTP fetcher for agency pages.

Responsibilities:
- identify ourselves with a clear User-Agent
- respect robots.txt
- rate-limit per host so we don't hammer a site
- retry transient failures with backoff

Static pages are fetched with httpx. JS-heavy sites that return little/no
content can later be routed through Playwright (see fetch_rendered stub).
"""
from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

USER_AGENT = "FundRadarBot/0.1 (+https://github.com/your-org/fundradar; research aggregator)"
DEFAULT_TIMEOUT = 35.0   # some government sites are slow (DBT timed out at 20s)
MIN_INTERVAL_PER_HOST = 2.0   # seconds between requests to the same host
MAX_RETRIES = 3

_last_request_at: dict[str, float] = {}
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


@dataclass
class FetchResult:
    url: str
    status: int
    html: str
    ok: bool
    error: str | None = None


def _host(url: str) -> str:
    return urlparse(url).netloc


def _robots_allows(url: str) -> bool:
    host = _host(url)
    rp = _robots_cache.get(host)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{urlparse(url).scheme}://{host}/robots.txt")
        try:
            rp.read()
        except Exception:
            # If robots is unreachable, default to allowing but stay polite.
            rp = None
        _robots_cache[host] = rp
    if rp is None:
        return True
    return rp.can_fetch(USER_AGENT, url)


def _throttle(url: str) -> None:
    host = _host(url)
    last = _last_request_at.get(host)
    if last is not None:
        wait = MIN_INTERVAL_PER_HOST - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
    _last_request_at[host] = time.monotonic()


def fetch(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> FetchResult:
    """Fetch a static page politely. Returns FetchResult (never raises)."""
    if not _robots_allows(url):
        return FetchResult(url, 0, "", ok=False, error="blocked by robots.txt")

    headers = {"User-Agent": USER_AGENT}
    last_err: str | None = None
    verify = True  # downgraded once (with a warning in the result) on broken certs
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle(url)
        try:
            with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers,
                              verify=verify) as client:
                resp = client.get(url)
            if resp.status_code >= 500:
                last_err = f"server error {resp.status_code}"
                time.sleep(2 ** attempt)
                continue
            err = None if verify else "insecure: served with invalid TLS certificate"
            return FetchResult(url, resp.status_code, resp.text,
                               ok=resp.status_code < 400, error=err)
        except httpx.HTTPError as e:
            last_err = str(e)
            # Many (esp. government) sites have misconfigured certificate chains.
            # The page content is public, so retry once without verification
            # rather than dropping the agency entirely.
            if verify and "CERTIFICATE_VERIFY_FAILED" in last_err.upper().replace(" ", "_"):
                verify = False
                continue
            time.sleep(2 ** attempt)
    return FetchResult(url, 0, "", ok=False, error=last_err)


def fetch_rendered(url: str, *, timeout: float = 30.0) -> FetchResult:
    """Fetch a JS-heavy page by rendering it in a headless browser (Playwright).

    Playwright is an optional dependency. If it is not installed, this returns a
    clear FetchResult error instead of raising, so the pipeline degrades safely.
    Install with:  pip install playwright  &&  playwright install chromium
    """
    if not _robots_allows(url):
        return FetchResult(url, 0, "", ok=False, error="blocked by robots.txt")
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return FetchResult(url, 0, "", ok=False,
                           error="playwright not installed (pip install playwright)")
    _throttle(url)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
                html = page.content()
            finally:
                browser.close()
        return FetchResult(url, 200, html, ok=bool(html))
    except Exception as e:
        return FetchResult(url, 0, "", ok=False, error=f"render failed: {e}")


def _looks_thin(res: "FetchResult") -> bool:
    """Heuristic: did a static fetch fail to get real content (JS-rendered page)?"""
    if not res.ok or not res.html:
        return True
    low = res.html.lower()
    if len(res.html) < 1500:
        return True
    if "enable javascript" in low or "please enable js" in low:
        return True
    return False


def smart_fetch(url: str, *, render_fallback: bool = False, timeout: float = DEFAULT_TIMEOUT) -> FetchResult:
    """Fetch a page statically; if the result looks empty (JS site) and
    render_fallback is on, retry with the headless browser."""
    res = fetch(url, timeout=timeout)
    if render_fallback and _looks_thin(res):
        rendered = fetch_rendered(url)
        if rendered.ok and rendered.html:
            return rendered
    return res
