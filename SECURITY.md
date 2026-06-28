# FundRadar — Security & Reliability

A summary of the safeguards built into the project, and the safe practices to
follow when deploying.

## Built into the application

- **No secrets in the code.** API keys and the database URL live only in `.env`,
  which is git-ignored and never uploaded. On a host (Render), secrets are set as
  environment variables, not committed.
- **Security headers** on every response (`app/api/security.py`): `X-Content-Type-Options`,
  `X-Frame-Options: SAMEORIGIN` (anti-clickjacking), `Referrer-Policy`,
  `X-XSS-Protection`, and a restrictive `Permissions-Policy`.
- **Rate limiting** — a per-IP limit (default 120 requests/minute, configurable via
  `RATE_LIMIT_PER_MIN`) protects the public endpoint from abuse; excess requests get
  a clean `429` response.
- **No information leakage** — a catch-all error handler returns a generic message
  instead of stack traces or internal details.
- **Input limits** — the chatbot query is capped (1–300 characters); list endpoints
  cap page size (`limit` ≤ 200) to prevent oversized responses.
- **SQL-injection safe** — all database access goes through SQLAlchemy's
  parameterised ORM; no raw string-built SQL.
- **Read-only public surface** — the API and dashboard only read data. Scraping and
  AI extraction are separate offline jobs, not exposed on the web.
- **Polite, safe scraping** — the scraper respects `robots.txt`, rate-limits per
  host, retries with backoff, and only fetches the agency URLs in your database
  (no user-supplied URLs), avoiding SSRF.
- **Optional toggles** (in `.env`): `ENABLE_DOCS=false` hides the interactive API
  docs in production; `CORS_ALLOW_ORIGINS` restricts cross-origin access if needed.

## Reliability

- **HTTPS** is provided automatically by the host (Render).
- **Self-seeding** — the app loads its data on startup, so a fresh or restarted
  instance always comes up populated.
- **Graceful degradation** — if the optional LLM or Playwright isn't available, the
  app falls back safely (list-mode chatbot; static-only scraping) instead of crashing.
- **Health check** — `GET /health` reports status and row counts for monitoring.
- **Per-run logging** — the pipeline writes timestamped logs for auditability.

## Good practice when you deploy

1. Never commit `.env` or the database file (already enforced by `.gitignore`).
2. Put the Gemini key (if used) in the host's environment settings, not in code.
3. Keep the repository **private** unless you intend it to be public.
4. For production, set `ENABLE_DOCS=false` and consider lowering `RATE_LIMIT_PER_MIN`.
