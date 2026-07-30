# FundRadar — how everything works and where it lives

A plain-language tour of the whole system. Written to be read start to finish
before a demo, and to answer the questions a reviewer is most likely to ask.

---

## 1. The one-sentence version

FundRadar visits funding-agency websites, uses AI to turn their messy pages
into clean structured records (amount, deadline, eligibility, research area),
stores those in a database, and serves them through a website, a chatbot and a
public API.

---

## 2. The four pieces, and who runs them

| Piece | What it does | Where it runs | When |
|---|---|---|---|
| **Scraper + AI extraction** | Reads agency websites, pulls out opportunities | GitHub Actions (free cloud) | Automatically every 2 days |
| **Database** | Holds agencies, opportunities, users, bookmarks | Inside the web service (SQLite file) | Always |
| **Web app + API** | Dashboard, chatbot, login, JSON API | Render.com | Always (sleeps when idle) |
| **Source code** | Everything above | GitHub | — |

The important thing to understand: **the scraping does not happen on the
website.** They are deliberately separated.

### Why they're separated

Scraping is slow, needs heavy libraries (a browser engine, a PDF reader, an AI
SDK) and can fail when a site is down. If that ran inside the web service, a
visitor could hit a slow or broken page.

So the heavy work runs on a schedule in GitHub's cloud, and the website only
ever reads a finished database. The website stays small and fast, and a failed
scrape can never take the demo down.

---

## 3. Walking through the data's journey

### Step 1 — The agency list (the starting point)

`data/Funding_Agency_Database.xlsx` lists **41 funding organisations** —
Indian agencies (DST, CSIR, ICMR, DBT, BIRAC…), international bodies (Horizon
Europe, SNSF, JSPS, CEFIPRA…), and universities. Each has a code (`IND001`),
a website, a category, and a priority.

`python -m app.ingest.seed_agencies` loads that spreadsheet into the database.
Re-running is safe — it updates existing rows rather than duplicating them.

### Step 2 — Scraping (`app/scraper/`)

For each agency the scraper:

1. Fetches the homepage.
2. Scores the links to find funding-related pages ("call for proposals",
   "grants", "fellowships"), rather than crawling the whole site.
3. Downloads those pages — and PDFs, which it reads too.
4. Saves the raw text plus a **hash** (a short fingerprint of the content).

The hash is what makes re-runs cheap: if a page's fingerprint hasn't changed
since last time, there's nothing new, so the AI is never asked about it.

It's a polite scraper by design: it obeys `robots.txt`, identifies itself with
a real User-Agent, waits ~2 seconds between requests to the same site, and
retries with backoff instead of hammering a struggling server.

### Step 3 — AI extraction (`app/llm/`)

Raw page text is unstructured — a human can read it, a database can't. Each new
page is sent to an AI model with an instruction to return structured JSON:
programme name, amount, deadline, eligibility, research area, summary, tags.

Then plain Python code cleans the result (`app/llm/normalize.py`):

- **Amounts**: `"Rs 10 lakh"` → `1,000,000 INR`. It understands ₹/$/€/£ and
  Indian units (lakh, crore) as well as western ones (k, million).
- **Deadlines**: `"30 June 2026"`, `"30/06/2026"`, `"2026-06-30"` → one real
  date. Anything already past is marked **closed** automatically.
- **Language**: some Indian agencies were scraped from their Hindi pages, so
  titles arrived as `"रोलैंड फैलोशिप (Rowland Fellowship)"`. These are flipped to
  read English-first: `"Rowland Fellowship (रोलैंड फैलोशिप)"`.

**Which AI?** This is deliberately swappable. `LLM_PROVIDER` in `.env` accepts:

- `auto` — try Google Gemini, fall back to Groq, then a local model. Used by
  the scheduled job so one provider's daily free quota running out doesn't
  stop the pipeline.
- `gemini` / `groq` / `ollama` — force one.
- `mock` — no AI at all. **This is what the live website runs**, because the
  website never extracts anything; it only reads already-extracted data.

No part of the code imports an AI vendor directly. Everything calls
`get_llm()`, so switching provider is a one-line change in `.env`.

### Step 4 — Cleanup before display

Real scraped data is messy, so the loader removes what a reviewer would
otherwise spot:

- **Not-actually-opportunities** — budget documents like "Detailed Demands for
  Grants" that sit in the same section of an agency site.
- **Duplicates** — the same call published on several pages of one agency's
  site. Rather than deleting one, the two rows are **merged**: if one page has
  the funding amount and the other has the eligibility text, the surviving row
  keeps both.

The duplicate rule is intentionally cautious, because wrongly merging two real
programmes would *hide* an opportunity from a researcher. Two rows only merge
if the names match closely **and** they don't state different deadlines. That's
why "Horizon Europe" and "Horizon Europe – Cancer Mission Calls 2026" correctly
stay separate — different deadlines mean they're different things.

### Step 5 — Serving it

A FastAPI application (`app/api/main.py`) serves everything from one process:

| URL | What it is |
|---|---|
| `/` | Public landing page |
| `/dashboard` | The main dashboard (requires sign-in) |
| `/profile` | User profile and saved opportunities |
| `/opportunities` | JSON API, filterable by area, status, amount, country |
| `/agencies` | JSON API for the 41 organisations |
| `/chat?q=…` | The chatbot |
| `/stats` | Counts and breakdowns that fill the dashboard cards |
| `/health` | Row counts — quickest way to check the site is alive |
| `/docs` | Auto-generated interactive API documentation |

`/docs` is worth showing in a demo: FastAPI generates it from the code, and a
reviewer can run live queries from the browser.

---

## 4. How the chatbot works

Ask *"AI grants open now"* and:

1. `retriever.py` parses the question for research area, status, amount and
   country.
2. It ranks the stored opportunities against those filters.
3. It returns the matches.

Without an AI key it replies with a clean formatted list. With one, the same
matches are handed to the model to phrase as a sentence.

The key point for a reviewer: **the chatbot answers from the database, not from
the model's memory.** The model only does the wording. That's why it can't
invent a grant that doesn't exist — every item it names is a row in the
database with a real source URL.

---

## 5. Accounts and security

- Passwords are hashed with **bcrypt**. The database stores only the hash; the
  plain password is never written anywhere.
- Logging in issues a **JWT** in an **httpOnly cookie** — JavaScript cannot
  read it, which blocks the most common session-stealing attack. `SameSite=lax`
  guards against cross-site request forgery, and on the live HTTPS site the
  cookie is marked `Secure` so it never travels unencrypted.
- **"Continue with Google"** is available (see `GOOGLE_SIGNIN_SETUP.md`).
  FundRadar never sees a Google password: Google returns a signed token, and the
  server verifies both that Google really signed it *and* that it was issued for
  FundRadar specifically — checking only the signature would let a token minted
  for a different app through.
- Also built in: security headers, per-IP rate limiting, input length limits,
  an error handler that never leaks internal details, and parameterised SQL via
  SQLAlchemy (so user input can't become SQL). See `SECURITY.md`.
- Secrets live in `.env`, which is **git-ignored** — no API key is in the repo.

---

## 6. Hosting — what is where

### GitHub — `https://github.com/N0x1ee/Fund-Radar`

The source of truth. Also runs two scheduled jobs:

- `.github/workflows/scrape.yml` — every 2 days: scrape all agencies, run AI
  extraction, commit the refreshed database back to the repo. Your computer can
  be switched off; this runs in GitHub's cloud. API keys are stored as GitHub
  **Secrets**, not in the code.
- `.github/workflows/sync-to-hf.yml` — mirrors the repo to Hugging Face Spaces.

### Render — `https://fundradar-ee69.onrender.com`

The live website. Configured by `render.yaml`, so the setup is version-
controlled rather than clicked together by hand.

**What happens on every deploy:**

1. Render installs the Python packages in `requirements.txt`.
2. If the scheduled job has committed a fresh `data/fundradar.db`, that becomes
   the starting database.
3. It seeds the 41 agencies from the Excel file.
4. It loads the demo opportunities (cleaning and de-duplicating as above).
5. It creates the demo account.
6. It starts the web server.

Every step is idempotent — safe to run repeatedly — and the app *also*
re-seeds itself on startup if it finds an empty database. Belt and braces: a
fresh deploy always has data.

**A deploy happens automatically whenever you push to `main`.** No manual step.

### Two things to know about the free tier

1. **It sleeps.** After ~15 minutes with no visitors the service shuts down.
   The next visit takes **30–60 seconds** to wake it. Open the link a couple of
   minutes before your demo so it's already awake.
2. **Storage is temporary.** The SQLite file lives on a disk that resets on each
   deploy — which is exactly why the app rebuilds its data on every boot.

### Docker (a spare route)

A `Dockerfile` is included, so the same app can run on Hugging Face Spaces,
Fly.io, Railway, or your own machine (`docker build -t fundradar . && docker run
-p 8000:8000 fundradar`). Nothing about the app is tied to Render.

---

## 7. Running it on your own laptop

```bash
.venv\Scripts\activate                       # Windows
pip install -r requirements.txt
python -m app.ingest.seed_agencies
python -m app.ingest.load_demo_opportunities
python -m app.ingest.seed_demo_user
uvicorn app.api.main:app --reload
```

Then open <http://127.0.0.1:8000>. Demo account: `demo@fundradar.com` /
`demo1234`.

This is your safety net: if the internet or Render misbehaves during the demo,
the identical app runs locally.

---

## 8. Honest limitations (better to say these first)

Being upfront about these tends to earn more credit than being caught out.

- **Only some agencies have extracted opportunities.** All 41 are in the
  database; a subset have been through the full scrape-and-extract cycle. The
  rest are configured and waiting.
- **Deadlines pass.** Some opportunities show as *closed* simply because their
  real deadline has gone by — that's the data being truthful, and the status
  updates itself on every refresh.
- **Some records have blank fields.** If an agency's page never states a
  funding amount, the field stays empty rather than being guessed. An empty
  field is better than an invented one.
- **AI extraction isn't perfect.** Every opportunity keeps its `source_url`, so
  anything can be traced back to the original page.
- **The free tier sleeps**, as described above.
