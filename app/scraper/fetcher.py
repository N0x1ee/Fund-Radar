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
DEFAULT_TIMEOUT = 20.0
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
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle(url)
        try:
            with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
                resp = client.get(url)
            if resp.status_code >= 500:
                last_err = f"server error {resp.status_code}"
                time.sleep(2 ** attempt)
                continue
            return FetchResult(url, resp.status_code, resp.text, ok=resp.status_code < 400)
        except httpx.HTTPError as e:
            last_err = str(e)
            time.sleep(2 ** attempt)
    return FetchResult(url, 0, "", ok=False, error=last_err)


def fetch_rendered(url: str) -> FetchResult:
    """Placeholder for Playwright-rendered fetch (JS-heavy sites).

    Wire this up when a site returns near-empty HTML from fetch(). Kept as a
    stub so the pipeline can fall back without importing Playwright eagerly.
    """
    raise NotImplementedError("Playwright rendering not yet enabled (Phase 2b).")
