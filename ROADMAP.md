# FundRadar — Build Roadmap

An AI-powered Funding Opportunity Intelligence Platform that collects, monitors,
organizes, and serves funding information through search and a chatbot.

Status legend: [x] done · [~] in progress · [ ] not started

---

## Phase 0 — Foundation  [x]  ← you are here
Goal: a runnable backbone with the agency seed data in a database.

- [x] Repo structure (`app/` with db, ingest, llm, scraper, api packages)
- [x] Config via `.env` (`app/config.py`) — DB URL + LLM provider switch
- [x] Database layer (`app/db/database.py`) — SQLite for dev, Postgres-ready
- [x] Schema (`app/db/models.py`) — `Agency` + `Opportunity` tables
- [x] Seed loader (`app/ingest/seed_agencies.py`) — 41 agencies from the Excel file
- [x] Pluggable LLM layer (`app/llm/`) — Gemini / Ollama / Mock
- [x] Verified: spreadsheet -> 41 agency rows, field mapping correct

Run it:
    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env
    python -m app.ingest.seed_agencies

## Phase 1 — Read API  [x]
Goal: expose the seeded data over HTTP so a UI/chatbot can query it.

- [x] FastAPI app (`app/api/main.py`) with `uvicorn` entrypoint
- [x] `GET /agencies` (filters: q, country, category, funding_type, priority) + `GET /agencies/{code}`
- [x] `GET /opportunities` (filters: q, research_area, status, min_amount, agency_code)
- [x] Pydantic response schemas (`app/db/schemas.py`); paginated envelope
- [x] `GET /health` + interactive docs at `/docs`

## Phase 2 — Scraping & ingestion  [~]
Goal: turn agency websites into raw opportunity records.

- [x] Fetch layer: `httpx` static fetch (`app/scraper/fetcher.py`); Playwright stub for JS sites (Phase 2b)
- [x] Per-agency discovery (`app/scraper/discovery.py`): keyword-scored funding links, on-domain only
- [x] Raw content store: `Opportunity.raw_text` + `content_hash` change detection (`app/scraper/extractor.py`)
- [x] Politeness: robots.txt, per-host rate limiting, retries with backoff
- [x] CLI ordered by `scraping_priority` (`app/scraper/run.py`): `--limit`, `--agency`, `--priority`
- [x] Playwright rendering for JS-heavy sites (`fetch_rendered` + `smart_fetch` fallback)
- [ ] PDF text extraction (Phase 2b)

## Phase 3 — AI extraction & enrichment  [~]
Goal: structured, tagged opportunity records from messy content.

- [x] Extraction prompt -> JSON (`app/llm/extraction.py`): program, amount, eligibility, deadline, link, contact
- [x] Normalize amounts (₹/$/€, lakh/crore/million -> value + currency) and parse deadlines to dates (`app/llm/normalize.py`)
- [x] AI enrichment: research-area, summary, tags; auto-close past-deadline rows
- [x] CLI over unprocessed rows (`app/llm/run_extraction.py`), provider-agnostic
- [ ] Backfill the empty agency columns (research_areas, eligibility, open calls)
- [ ] Validation + confidence; flag low-confidence rows for review

## Phase 4 — Monitoring & updates  [~]
Goal: keep data fresh automatically.

- [x] Single full-pipeline job (`app/run_pipeline.py`): scrape all + AI-extract, with logging
- [x] Idempotent re-runs: `content_hash` skips unchanged, refreshes changed pages
- [x] Past-deadline rows auto-marked `closed`; per-run log in `logs/`
- [x] Scheduling: cron + systemd-timer setup for every-2-days (`run_pipeline.sh`, `DEPLOYMENT.md`)
- [x] Free cloud automation: GitHub Action scrapes every 2 days, commits the DB,
      auto-redeploys HF/Render (`.github/workflows/scrape.yml`, `AUTOMATION_SETUP.md`)
- [x] One-command agency onboarding (`app/ingest/add_agency.py`, `ADDING_WEBSITES.md`)
- [ ] Explicit change-log table (what changed, when) for audit/history

## Phase 5 — Semantic search & chatbot  [~]
Goal: natural-language access to the database.

- [x] Query parser + keyword/intent retriever (`app/chat/retriever.py`): status, amount, country, terms
- [x] Chatbot brain (`app/chat/bot.py`): retrieve -> optional LLM phrasing, list fallback (no key needed)
- [x] Interfaces: CLI (`app/chat/cli.py`), `GET /chat` endpoint, dashboard "Ask FundRadar" box
- [x] Handles "AI grants open", "funding above 10 lakh", "opportunities in Germany", etc.
- [ ] Embeddings + vector store for true semantic ranking (pgvector/Chroma)

## Phase 6 — Frontend  [ ]
Goal: usable product surface.

- [ ] React/Next.js: search + filters, opportunity detail, chatbot widget
- [ ] Agency directory view
- [ ] Deploy notes

## Phase 7 — Hardening  [~]
- [x] Security layer: headers, rate limiting, error handling, input limits (`app/api/security.py`, SECURITY.md)
- [x] Deploy config for managed hosting (`render.yaml`); HTTPS via host
- [ ] Move dev SQLite -> PostgreSQL; Alembic migrations
- [ ] Auth (saved searches, alerts), tests, Docker, CI

---

### Recommended next step
Phase 2b (Playwright + PDF) to widen scraper coverage, then add vector embeddings
to upgrade the chatbot from keyword matching to true semantic search.
