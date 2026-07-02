# FundRadar — Project Documentation (Single Source of Truth)

> AI-powered Funding Opportunity Intelligence Platform.
> Collects, monitors, structures and serves funding opportunities (grants,
> fellowships, scholarships, startup funding, research calls) from many agencies,
> and exposes them through a REST API, two web frontends, and a chatbot.

Status: Phases 0–1 complete; Phases 2–5 in progress; deployed live on Hugging Face
Spaces (Docker). This document is the onboarding reference for the codebase.

---

## 1. Folder structure

```
Fund-Radar/
├── app/                          # All application code (one Python package)
│   ├── __init__.py
│   ├── config.py                 # Central settings (env-driven): DB, LLM, security
│   ├── run_pipeline.py           # Scheduled job: scrape all agencies + AI-extract
│   │
│   ├── api/                      # Web layer (FastAPI)
│   │   ├── main.py               # App, routes, startup auto-seed, security install
│   │   ├── deps.py               # get_db() DB-session dependency
│   │   ├── security.py           # Headers, rate limit, error handler, CORS
│   │   └── static/
│   │       ├── dashboard.html    # Branded single-page dashboard  → served at "/"
│   │       └── index.html        # Multi-page SPA (8 pages)        → served at "/app"
│   │
│   ├── db/                       # Data layer
│   │   ├── database.py           # Engine/session, Base, init_db()
│   │   ├── models.py             # ORM: Agency, Opportunity
│   │   └── schemas.py            # Pydantic response models (AgencyOut, OpportunityOut, Page)
│   │
│   ├── ingest/                   # Getting data IN
│   │   ├── seed_agencies.py      # Excel  → agencies table (idempotent upsert)
│   │   └── load_demo_opportunities.py  # JSON → opportunities (curated demo set)
│   │
│   ├── chat/                     # Chatbot (Phase 5)
│   │   ├── bot.py                # answer(): retrieve → LLM phrasing or list fallback
│   │   ├── retriever.py          # parse_query() + rank() (pure keyword/intent logic)
│   │   └── cli.py                # Terminal chatbot
│   │
│   ├── llm/                      # Pluggable AI layer (Phase 3)
│   │   ├── base.py               # LLMProvider abstract interface
│   │   ├── providers.py          # Gemini | Ollama | Mock + get_llm() factory
│   │   ├── extraction.py         # raw_text → structured JSON (prompt/parse/apply)
│   │   ├── normalize.py          # Amount + date normalization (₹/$/€, lakh/crore)
│   │   └── run_extraction.py     # CLI over unprocessed opportunities
│   │
│   └── scraper/                  # Scraping engine (Phase 2)
│       ├── fetcher.py            # Polite HTTP: robots.txt, rate-limit, retries
│       ├── discovery.py          # Keyword-score & find funding links
│       ├── extractor.py          # HTML → clean text, title, content hash
│       ├── pdf.py                # PDF download + text extraction (pypdf)
│       ├── pipeline.py           # Per-agency orchestration (HTML + PDF)
│       └── run.py                # CLI to run the scraper
│
├── data/
│   ├── Funding_Agency_Database.xlsx   # 41 agencies (seed source)
│   └── demo_opportunities.json        # 25 curated real opportunities
│
├── Dockerfile                    # Portable container (HF Spaces: /tmp DB, port 7860)
├── requirements.txt              # Core deps + optional scraper/AI deps
├── render.yaml                   # Alternative deploy blueprint (Render)
├── .env.example                  # Template for local secrets/config
├── .gitignore / .gitattributes / .dockerignore
└── docs: README, ROADMAP, SECURITY.md, PRODUCT_VISION.md, DEPLOYMENT.md,
        RENDER_GUIDE, GITHUB_GUIDE, DEPLOY_NOW, PROJECT_GUIDE, SHARING, DEMO_RESULTS
        (+ report PDFs/DOCX/images — documentation only, NOT used at runtime)
```

### Directory responsibilities

| Directory | Responsibility |
|-----------|----------------|
| `app/api` | HTTP surface: FastAPI routes, dependencies, security middleware, static frontends |
| `app/db` | SQLAlchemy engine/session, ORM models, Pydantic response schemas |
| `app/ingest` | One-shot loaders that populate the DB from the Excel + JSON sources |
| `app/chat` | Natural-language Q&A over the stored opportunities |
| `app/llm` | Vendor-agnostic LLM access + extraction/normalization utilities |
| `app/scraper` | Fetch agency sites, discover funding pages, extract raw text/PDF, change-detect |
| `data` | Seed inputs (agency master list + curated demo opportunities) |

---

## 2. Architecture

```
                         ┌──────────────────────────────────────────┐
                         │                FundRadar                  │
                         │        (single FastAPI service)           │
                         └──────────────────────────────────────────┘

  DATA PIPELINE (offline / scheduled) ───────────────────────────────────────────
  ┌────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────┐
  │  Seed  │──▶│  Scrape  │──▶│  AI Extract  │──▶│   Monitor    │──▶│  Serve   │
  │ Excel/ │   │ agency   │   │ LLM → fields │   │ re-run every │   │ API/UI/  │
  │ JSON   │   │ sites+PDF│   │ + normalize  │   │ N days, hash │   │ chatbot  │
  └────────┘   └──────────┘   └──────────────┘   └──────────────┘   └──────────┘
       │             │               │                  │                 │
       ▼             ▼               ▼                  ▼                 ▼
  ┌───────────────────────────────────────────────────────────────────────────┐
  │                     SQLite DB  (agencies, opportunities)                    │
  │                       SQLAlchemy ORM · Postgres-ready                       │
  └───────────────────────────────────────────────────────────────────────────┘

  REQUEST PATH (online) ──────────────────────────────────────────────────────
     Browser ─HTTP─▶ FastAPI (security middleware) ─▶ route ─▶ SQLAlchemy ─▶ DB
                                                        │
                                     /chat ─▶ retriever + (optional) LLM
```

Layered design (top → bottom): **Frontend (static HTML+JS)** → **API (FastAPI)** →
**Security middleware** → **ORM (SQLAlchemy)** → **SQLite**. The **scraper**, **LLM**
and **ingest** layers are *offline producers* that write into the DB; the API is an
*online consumer* that reads from it. Nothing in the request path calls the network.

---

## 3. Backend

**Framework:** FastAPI + Uvicorn (ASGI). **ORM:** SQLAlchemy 2.x. **Validation:**
Pydantic v2 + pydantic-settings.

- `app/api/main.py` — creates the `FastAPI` app, installs security middleware, runs a
  **startup hook** (`_bootstrap_db`) that creates tables and seeds the DB if empty
  (so a fresh/ephemeral host always has data), and defines all routes.
- `app/api/deps.py` — `get_db()` yields a scoped SQLAlchemy session per request.
- `app/api/security.py` — `install_security(app)` attaches: security headers,
  per-IP rate limiter, generic exception handler, optional CORS.
- `app/db/database.py` — engine (SQLite dev, `check_same_thread=False`; Postgres via
  `DATABASE_URL`), `SessionLocal`, `Base`, `init_db()`.
- `app/db/models.py` — `Agency` (12 cols) and `Opportunity` (18 cols).
- `app/db/schemas.py` — response DTOs decoupled from ORM (`from_attributes=True`),
  plus a generic paginated `Page[T]` envelope.

---

## 4. API reference

Base URL (live): `https://shreshthaa15-fundradarv2.hf.space`

| Method | Path | Params | Purpose | Response |
|--------|------|--------|---------|----------|
| GET | `/` | – | Branded dashboard (HTML) | `text/html` |
| GET | `/legacy` | – | Dashboard alias (kept from shreshtha-dev) | `text/html` |
| GET | `/app` | – | Multi-page SPA (8 pages) | `text/html` |
| GET | `/api` | – | Service info | JSON |
| GET | `/health` | – | Row counts + status | `{status, agencies, opportunities}` |
| GET | `/stats` | – | Aggregates + breakdowns for dashboard | JSON |
| GET | `/scrapers` | – | Per-agency scraper status + engine capabilities | JSON |
| GET | `/agencies` | `q, country, category, funding_type, priority, limit, offset` | Paginated agencies | `Page[AgencyOut]` |
| GET | `/agencies/{agency_code}` | path | Single agency | `AgencyOut` |
| GET | `/opportunities` | `q, research_area, status, min_amount, agency_code, limit, offset` | Paginated, filterable opportunities | `Page[OpportunityOut]` |
| GET | `/chat` | `q` (1–300 chars, required) | NL Q&A over the DB | `{question, answer}` |
| GET | `/docs`, `/redoc` | – | Interactive OpenAPI (toggle via `ENABLE_DOCS`) | HTML |

All endpoints are **read-only**. Scraping/AI are separate offline jobs, never exposed.

---

## 5. Database

**Engine:** SQLite (`sqlite:///./fundradar.db` dev; `/tmp/fundradar.db` in container).
Postgres-ready via `DATABASE_URL`. Managed by SQLAlchemy; `init_db()` creates tables.

```
┌──────────────────────────┐        ┌───────────────────────────────────┐
│         agencies         │ 1    * │           opportunities           │
├──────────────────────────┤◀───────├───────────────────────────────────┤
│ id (PK)                  │        │ id (PK)                           │
│ agency_code (unique)     │        │ agency_id (FK → agencies.id)      │
│ name, country, category  │        │ program_name, funding_amount      │
│ funding_type, website    │        │ amount_value, currency            │
│ research_areas           │        │ eligibility, research_area        │
│ eligibility              │        │ deadline, application_link        │
│ deadline_frequency       │        │ contact_info, summary, tags       │
│ current_open_calls       │        │ raw_text (pre-AI), processed      │
│ scraping_priority, notes │        │ status (open|closed|unknown)      │
│ created_at, updated_at   │        │ source_url, content_hash          │
└──────────────────────────┘        │ first_seen, last_checked          │
                                     └───────────────────────────────────┘
```

Key columns: `Opportunity.raw_text` holds pre-AI scraped text; `content_hash` powers
change-detection; `processed` flags whether AI extraction ran; `amount_value`/`currency`
are normalized from the free-text `funding_amount`.

---

## 6. Scraper (Phase 2)

Per-agency flow (`app/scraper/pipeline.py`):

```
agency.website ─▶ fetcher.fetch() ─▶ discovery.find_funding_links()
      │                                        │  (keyword-scored, on-domain)
      │                                        ▼
      └──────────────────▶ for each candidate link:
                              ├─ if .pdf  → pdf.fetch_pdf_text()   (pypdf)
                              └─ else     → fetcher.fetch() + extractor.extract_text()
                                             │
                                             ▼
                              content_hash → upsert Opportunity(raw_text, processed=False)
```

- **fetcher.py** — custom User-Agent, robots.txt compliance, per-host 2s rate-limit,
  retry-with-backoff. `fetch_rendered()` is a Playwright stub (Phase 2b).
- **discovery.py** — scores anchors (strong words: grant/fellowship/RFP; negatives:
  login/careers), resolves relative URLs, stays on-domain.
- **extractor.py** — strips scripts/nav, returns clean text + title + SHA-256 hash.
- **pdf.py** — downloads PDFs politely, extracts text with `pypdf`, caps at 20 MB,
  detects scanned/image-only PDFs (reports instead of guessing).
- **run.py** — CLI: `--agency`, `--priority`, `--limit`, `--max-pages`.

---

## 7. AI / LLM pipeline (Phase 3)

Vendor-agnostic via `get_llm()` — switch with one env var, no code changes.

```
Opportunity.raw_text ─▶ extraction.build_prompt() ─▶ llm.complete()
                          ▶ parse_llm_json() ─▶ apply_extraction():
                              • program_name, eligibility, research_area, summary, tags
                              • normalize_amount()  ("Rs 10 lakh" → 1_000_000, INR)
                              • parse_deadline()    ("30 June 2026" → date)
                              • status (past deadline ⇒ closed); processed = True
```

Providers (`providers.py`): **Gemini** (free tier, recommended), **Ollama** (local),
**Mock** (default; no key — lets the pipeline/chatbot run without credentials).

---

## 8. Search / chatbot pipeline (Phase 5)

```
GET /chat?q=... ─▶ bot.answer():
   retriever.parse_query(q)  → {status, min_amount, countries, terms}
   retriever.rank(rows,...)  → filter (status/amount/country) + keyword score
        │
        ├─ LLM_PROVIDER == mock  → clean formatted list (always works, no key)
        └─ LLM_PROVIDER == gemini → LLM writes a natural answer using ONLY those rows
```

`retriever.py` is pure functions (no DB/LLM) → easily testable. Current ranking is
keyword/intent based; true semantic (embeddings/vector) search is a roadmap item.

---

## 9. Frontend

Two static, JS-driven frontends served by FastAPI, both consuming the JSON API:

- **`dashboard.html`** (`/`) — branded single page: stat cards, "Ask FundRadar"
  chatbot box, opportunities/agencies tables with search + filters. Organization
  branding: **green (`#16a34a`) primary + blue (`#2563eb`) accent** on white.
- **`index.html`** (`/app`) — multi-page SPA (hash-routed): Dashboard, Agencies,
  Opportunities, Scraper Status, Database viewer, API docs, Project Progress, About.
  Tailwind (CDN) + Chart.js (CDN), dark-mode, responsive sidebar.

No build step; both are plain HTML+JS that `fetch()` the API.

---

## 10. Deployment

**Primary: Hugging Face Spaces (Docker).** Card-free, HTTPS, persistent.

```
Dockerfile → HF build → container:
   ENV DATABASE_URL=sqlite:////tmp/fundradar.db   (only /tmp is writable on HF)
   EXPOSE 7860                                     (HF default port)
   CMD seed_agencies && load_demo_opportunities && uvicorn ... --port ${PORT:-7860}
```

Deployment strategy that works: push **only runtime files** (`app/`, `data/`,
`requirements.txt`, `Dockerfile`) to a clean Space repo — documentation binaries are
excluded so HF's binary/LFS check never trips; the one needed binary
(`data/*.xlsx`, 11 KB) rides HF's default LFS rules. **Alternative:** `render.yaml`
(Render blueprint, native Python runtime).

---

## 11. Environment variables & configuration (`app/config.py`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./fundradar.db` | DB connection (set to `/tmp/...` in container; Postgres URL for prod) |
| `LLM_PROVIDER` | `mock` | `gemini` \| `ollama` \| `mock` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | – / `gemini-2.0-flash` | Gemini config |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | `localhost:11434` / `llama3.1` | Local LLM |
| `USE_PLAYWRIGHT` | `false` | JS-site rendering (scraper) |
| `RATE_LIMIT_PER_MIN` | `120` | Per-IP request cap (0 = off) |
| `ENABLE_DOCS` | `true` | Expose `/docs` + `/redoc` |
| `CORS_ALLOW_ORIGINS` | `""` | Comma-separated allowlist (empty = same-origin) |

Secrets live only in `.env` (git-ignored) or host env vars — never committed.

---

## 12. Security (`app/api/security.py`, `SECURITY.md`)

- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`,
  `Referrer-Policy`, `X-XSS-Protection`, `Permissions-Policy`.
- **Rate limiting**: in-memory per-IP fixed window (default 120/min) → `429` on excess.
- **Error masking**: catch-all handler returns generic 500 (no stack traces).
- **Input limits**: `/chat` query 1–300 chars; list `limit` capped.
- **SQL-injection safe**: all access via parameterized SQLAlchemy ORM.
- **Read-only public surface**: scraping/AI are offline, never web-exposed.
- **No secrets in code**: `.env` + host env vars only.

---

## 13. Feature inventory

| Feature | Files | Status |
|---------|-------|--------|
| Agency directory + filters | `api/main.py`, `db/*`, both frontends | ✅ Done |
| Opportunity explorer (search/sort/filter) | `api/main.py`, `db/*`, `static/*` | ✅ Done |
| Aggregate statistics + charts | `/stats`, `static/*` | ✅ Done |
| Chatbot (mock + Gemini) | `chat/*`, `/chat` | ✅ Done (keyword retriever) |
| Scraper engine (HTML) | `scraper/{fetcher,discovery,extractor,pipeline,run}` | ✅ Built |
| PDF scraping | `scraper/pdf.py`, `scraper/pipeline.py` | ✅ Built |
| AI extraction + normalization | `llm/*` | ✅ Built |
| Scheduled monitoring pipeline | `run_pipeline.py` | ✅ Built |
| Security middleware | `api/security.py` | ✅ Done |
| Multi-page SPA + branded dashboard | `static/index.html`, `static/dashboard.html` | ✅ Done |
| Docker / HF deployment | `Dockerfile`, live Space | ✅ Live |
| Semantic (vector) search | – | ⬜ Planned |
| Playwright JS rendering | `fetcher.fetch_rendered` (stub) | ⬜ Planned |
| **Authentication (Login/Signup)** | *to be built (see §14)* | ⬜ Planned |

---

## 14. Authentication design (planned — NOT yet implemented)

**Goal:** add user accounts (signup/login/logout) to gate future user-specific
features (saved opportunities, alerts, admin) without disturbing the read-only demo.

### Recommended strategy
- **Auth mechanism:** **httpOnly, Secure, SameSite=Lax session cookie** carrying a
  **signed JWT** (stateless) — best fit for a browser frontend on a single service.
  Rationale: httpOnly cookie ⇒ not readable by JS (XSS-resistant); JWT ⇒ no server
  session store needed on the free tier. (Pure server-side sessions are the
  alternative if we later want instant revocation.)
- **Password hashing:** `passlib` with **bcrypt** (or argon2). Never store plaintext.
- **Token lifetime:** short access token (e.g. 30–60 min); **"Remember me"** ⇒ longer
  cookie `max-age` + refresh token (DB-stored) for silent renewal.
- **Protected routes:** a FastAPI dependency `get_current_user` that reads/validates
  the cookie and 401s if invalid; applied per-route via `Depends`.

### Data model (new `users` table)
```
users
├── id (PK)
├── email (unique, indexed)
├── password_hash
├── full_name (nullable)
├── is_active (bool)
├── is_admin (bool)
├── created_at, last_login_at
(optional) refresh_tokens(id, user_id FK, token_hash, expires_at, revoked)
```

### Where new files should live
```
app/auth/
├── __init__.py
├── models.py        # User (+ RefreshToken) ORM  (or add to app/db/models.py)
├── schemas.py       # SignupIn, LoginIn, UserOut, TokenOut (Pydantic)
├── security.py      # hash_password, verify_password, create/verify JWT
├── deps.py          # get_current_user, require_admin
└── routes.py        # POST /auth/signup, /auth/login, /auth/logout, GET /auth/me
app/api/static/
├── login.html       # login page  (served at /login)
└── signup.html      # signup page (served at /signup)
```
Wire-up: `app/api/main.py` includes the auth router; `app/db/database.py` `init_db()`
creates the new table; add `passlib[bcrypt]` + `python-jose[cryptography]` to
`requirements.txt`; add `JWT_SECRET` (+ optional `ACCESS_TOKEN_MINUTES`) to config/env.

### Flows
```
SIGNUP:  form → POST /auth/signup → validate + hash password → insert user
                → issue cookie(JWT) → redirect to dashboard
LOGIN:   form → POST /auth/login → verify email + bcrypt → issue cookie(JWT)
                → (Remember me ⇒ long-lived cookie + refresh token)
LOGOUT:  POST /auth/logout → clear cookie (+ revoke refresh token)
ACCESS:  request → get_current_user reads cookie → valid? proceed : 401
```

### Future scalability
Stateless JWT scales horizontally; move sessions/refresh tokens to Postgres/Redis
when multi-instance; add email verification, password reset, OAuth (Google), and RBAC
(`is_admin`) for an admin console over the scraper.

---

## 15. Future roadmap

- Semantic search (embeddings + pgvector/Chroma).
- PDF OCR for scanned documents; Playwright for JS-heavy agency sites.
- Change-log/audit table; email/alert notifications.
- Authentication (§14) → saved opportunities, alerts, admin console.
- Dedicated React/Next.js frontend (Phase 6).
- Postgres in production.

---

## 16. Onboarding quick start (local)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m app.ingest.seed_agencies
python -m app.ingest.load_demo_opportunities
uvicorn app.api.main:app --reload      # http://127.0.0.1:8000  (/, /app, /docs)
```
