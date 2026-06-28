"""Security & reliability middleware for the public API.

Adds, with no external dependencies:
- security response headers (clickjacking, MIME-sniffing, referrer, etc.)
- a simple in-memory per-IP rate limiter (protects the public endpoint)
- a catch-all exception handler that never leaks stack traces

All are lightweight and safe for a single-instance free-tier deployment.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "1; mode=block",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window-ish limiter: max N requests per IP per 60s. In-memory."""

    def __init__(self, app, limit_per_min: int = 120):
        super().__init__(app)
        self.limit = limit_per_min
        self.hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        q = self.hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.limit:
            return JSONResponse(status_code=429,
                                content={"detail": "Too many requests. Please slow down."})
        q.append(now)
        return await call_next(request)


def install_security(app):
    """Attach middleware + a generic error handler to the FastAPI app."""
    app.add_middleware(SecurityHeadersMiddleware)
    if settings.rate_limit_per_min > 0:
        app.add_middleware(RateLimitMiddleware, limit_per_min=settings.rate_limit_per_min)

    # optional CORS, only if explicitly configured
    origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    if origins:
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(CORSMiddleware, allow_origins=origins,
                           allow_methods=["GET"], allow_headers=["*"])

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # never leak internals to the client
        return JSONResponse(status_code=500,
                            content={"detail": "An internal error occurred."})
