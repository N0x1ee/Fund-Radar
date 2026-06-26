# FundRadar — Plain-English Guide

## 1. What this project is (in one breath)

Funding opportunities — grants, fellowships, scholarships, research calls — are
scattered across hundreds of agency websites and keep changing. FundRadar is a
system that automatically collects them, keeps them up to date, organizes them,
and lets people find them by searching or by asking a chatbot in plain language.

Think of it like a "search engine for funding" that updates itself.

## 2. What we have actually built so far

We build it in stages. Three stages are done.

**Stage 1 — The base.** A skeleton that everything else plugs into: a settings
file, a database (a single file on disk for now), and two "tables" — one listing
funding **Agencies** (your 41 from the Excel sheet) and one for individual
funding **Opportunities**. A loader puts your Excel data into the database.

**Stage 2 — The website (API).** A small web server that hands out the data when
asked: "give me all agencies in India", "show me this one agency", and so on.
It even comes with a clickable test page in the browser.

**Stage 3 — The collector (scraper).** The part that visits each agency's
website, finds the pages about funding, and saves them. It is polite (doesn't
hammer sites), and it notices when a page changes so we can update.

**Stage 4 — The brain (AI extraction).** Takes the messy text the collector
saved and uses an AI model to pull out the useful bits — how much money, who can
apply, the deadline, the topic — plus a short summary and tags. It also tidies
amounts ("Rs 10 lakh" → 1,000,000) and dates into a standard form.

So today the machine can: store agencies → fetch their funding pages → and turn
those pages into clean, organized funding records.

## 3. What is still left

- **Stage 5 — Auto-updating:** re-check websites on a schedule and update changes.
- **Stage 6 — Smart search + chatbot:** ask questions in plain language.
- **Stage 7 — The app screen (frontend):** a proper website for users.
- **Stage 8 — Polish:** bigger database, logins, tests.

## 4. How to set it up (one time)

In a terminal, inside the project folder:

```
python -m venv .venv
.venv\Scripts\activate        # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env        # Windows   (Mac/Linux: cp .env.example .env)
```

Then open `.env` and, for real AI, set:
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_free_key_from_https://aistudio.google.com/app/apikey
```
(Leave it as `mock` to test the plumbing without a key.)

## 5. What each file does and how to run it

You only ever RUN four things. The rest are building blocks the four use.

### Things you run (commands)

| Command | What it does |
|---|---|
| `python -m app.ingest.seed_agencies` | Loads the 41 agencies from the Excel file into the database. Run this first. |
| `python -m app.scraper.run --limit 5` | Visits the top 5 agencies' websites and saves their funding pages. |
| `python -m app.llm.run_extraction` | Runs the AI over the saved pages to fill in amount, deadline, eligibility, etc. |
| `uvicorn app.api.main:app --reload` | Starts the web server. Then open http://127.0.0.1:8000/docs to click around. |

A normal run, in order: **seed → scrape → extract → start the API**.

### The building blocks (you don't run these directly)

- `app/config.py` — reads settings from `.env` (which database, which AI provider).
- `app/db/database.py` — the connection to the database.
- `app/db/models.py` — defines the two tables (Agency, Opportunity).
- `app/db/schemas.py` — the shape of the data the API gives back.
- `app/ingest/seed_agencies.py` — Excel → database loader (run via the command above).
- `app/scraper/fetcher.py` — politely downloads a web page.
- `app/scraper/discovery.py` — finds the funding-related links on a page.
- `app/scraper/extractor.py` — pulls clean text and detects changes.
- `app/scraper/pipeline.py` — runs the whole scrape for one agency.
- `app/scraper/run.py` — the scrape command (run via the command above).
- `app/llm/providers.py` — talks to the AI (Gemini / local / mock).
- `app/llm/extraction.py` — asks the AI to pull out structured fields.
- `app/llm/normalize.py` — tidies amounts and dates.
- `app/llm/run_extraction.py` — the AI command (run via the command above).
- `app/api/main.py` — the web server and its endpoints.

### Reference docs

- `README.md` — quick commands.
- `ROADMAP.md` — the full plan and what's done (checkboxes).
- `PROJECT_GUIDE.md` — this file.

## 6. How to present the progress to someone

Aim for a 5-minute live demo. Story arc: problem → what we built → show it working.

**Slide/talking points (keep it to ~5):**
1. **The problem.** Funding info is scattered and goes stale; people miss chances.
2. **The idea.** One self-updating place to find funding, with a chatbot.
3. **What works today.** A pipeline: store agencies → scrape their sites →
   AI turns messy pages into clean records. Show the roadmap with 4 stages ticked.
4. **Live demo** (see below).
5. **What's next.** Auto-updating, chatbot search, and the user website.

**The live demo (the part that impresses):**
1. Run `python -m app.ingest.seed_agencies` → "41 agencies loaded."
2. Start `uvicorn app.api.main:app --reload`, open `/docs` in the browser.
3. Click `GET /agencies` → show the real list. Filter by `country=India`.
4. (If you've run the scraper + extraction) click `GET /opportunities` →
   show structured funding data with amounts and deadlines the AI extracted.
5. Point out it's provider-agnostic and uses a FREE AI tier (Gemini).

**If you can't run a live demo,** screenshot the `/docs` page and one
`/agencies` result, and show the ROADMAP checkboxes. That alone communicates
"this is a real, working system, not just slides."

**One-line summary to lead with:** "We've built the engine that collects funding
opportunities from agency websites and uses AI to turn them into a clean,
searchable database — the next step is the chatbot and the user-facing website."
