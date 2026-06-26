# FundRadar

AI-powered Funding Opportunity Intelligence Platform — collects, monitors,
organizes, and serves funding opportunities (grants, fellowships, scholarships,
research calls) from many agencies via search and a chatbot.

See **ROADMAP.md** for the full phased plan. This repo currently implements
**Phase 0 (Foundation)**.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
python -m app.ingest.seed_agencies
```

This creates `fundradar.db` (SQLite) and loads the 41 agencies from
`data/Funding_Agency_Database.xlsx`. Re-running is safe (upsert on agency code).

### Run the API (Phase 1)

```bash
uvicorn app.api.main:app --reload
```

Then open http://127.0.0.1:8000/docs for interactive API docs. Useful calls:

- `GET /health` — row counts
- `GET /agencies?country=India&limit=10`
- `GET /agencies?q=biotech`
- `GET /agencies/IND001`
- `GET /opportunities?research_area=AI&status=open&min_amount=1000000`

Opportunities are empty until Phase 2 (scraping) populates them.

### Run the scraper (Phase 2)

```bash
python -m app.scraper.run --limit 5          # 5 highest-priority agencies
python -m app.scraper.run --agency IND001    # a single agency
python -m app.scraper.run --priority High    # all High-priority agencies
```

This fetches agency homepages, finds funding-related pages, and stores raw
opportunity records (`raw_text` + change-detection hash). It is polite by
design: respects robots.txt, rate-limits per host, and retries transient
failures. Structured fields stay empty until Phase 3 (AI) processes the raw text.

### Run AI extraction (Phase 3)

```bash
python -m app.llm.run_extraction              # process scraped, unprocessed rows
python -m app.llm.run_extraction --limit 10   # cap how many
python -m app.llm.run_extraction --reprocess  # redo everything
```

Reads each opportunity's `raw_text`, asks the LLM for structured JSON, then
normalizes amounts (₹/$/€, lakh/crore) and deadlines, fills research area,
summary and tags, and marks the row processed. Set `LLM_PROVIDER=gemini` and
`GEMINI_API_KEY` in `.env` for real results (mock just marks rows done).

After this, the `/opportunities` API returns clean, filterable data.

### Load the real demo dataset (25 live opportunities, 11 agencies)

```bash
python -m app.ingest.load_demo_opportunities
```

Loads genuine current funding calls (see `data/demo_opportunities.json` and the
`DEMO_RESULTS.md` report) so `/opportunities` shows real data immediately — handy
for a presentation without depending on live scraping during the demo.

### Automate it (every 2 days)

```bash
python -m app.run_pipeline            # full pass: scrape all agencies + AI extract
python -m app.run_pipeline --limit 5  # test on 5 first
```

To run it automatically every 2 days on a server (cron or systemd timer), see
`DEPLOYMENT.md`. Each run logs to `logs/pipeline_YYYY-MM-DD.log`.

### Ask the chatbot (Phase 5)

```bash
python -m app.chat.cli           # interactive Q&A in the terminal
```

Or via the API / dashboard: `GET /chat?q=...`, and the "Ask FundRadar" box at the
top of http://127.0.0.1:8000/. Example questions: "AI grants open now",
"fellowships for PhD students", "funding above 10 lakh", "opportunities in Germany".

The chatbot reads the extracted opportunities. Without a key it returns a clean
matched list; with `LLM_PROVIDER=gemini` it phrases a natural-language answer.

## Project layout

```
app/
  config.py            # settings from .env (DB url, LLM provider)
  db/
    database.py        # engine/session; SQLite dev, Postgres-ready
    models.py          # Agency + Opportunity tables
  ingest/
    seed_agencies.py   # Excel -> agencies table
  llm/
    base.py            # LLMProvider interface
    providers.py       # Gemini | Ollama | Mock + get_llm() factory
  scraper/             # Phase 2
  api/                 # Phase 1 (FastAPI)
data/
  Funding_Agency_Database.xlsx
```

## Choosing an LLM (free/cheap)

Set `LLM_PROVIDER` in `.env`:

- `gemini` — **Google Gemini Flash**, free tier ~1,500 requests/day, 1M-token
  context, no credit card. Key: https://aistudio.google.com/app/apikey  ← recommended
- `ollama` — fully local models (Llama 3.1, etc.), zero cost, needs a decent machine.
- `mock` — no model; lets the pipeline run for testing without any key (default).

The rest of the code never imports a vendor directly — it calls `get_llm()`,
so you can switch providers by editing one line in `.env`.

## Database

Dev uses SQLite (`DATABASE_URL=sqlite:///./fundradar.db`). To move to Postgres
later, install `psycopg2-binary` and set e.g.
`DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/fundradar`.
The models are written to be Postgres-compatible.
