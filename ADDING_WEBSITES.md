# FundRadar — Adding & Finding New Funding Websites

## Add a website (one command)

```bash
python -m app.ingest.add_agency --name "Wellcome Trust" \
    --website https://wellcome.org --country "United Kingdom" \
    --category "Charity/Foundation" --priority high
```

Only `--name` and `--website` are required. This writes the agency into both
the Excel file (`data/Funding_Agency_Database.xlsx`) and the database, and
prints its auto-generated code (e.g. `UNI004`).

Optional extras: `--funding-type`, `--areas`, `--eligibility`, `--notes`,
`--code` (choose your own code), `--priority high|medium|low` (high = scraped
first).

Then either:

- **Scrape it right now:** `python -m app.scraper.run --agency UNI004`
  followed by `python -m app.llm.run_extraction`, or
- **Let automation handle it:** `git add . && git commit -m "Add Wellcome Trust" && git push`
  — the next scheduled GitHub Action run seeds and scrapes it automatically.

## Add several at once (Excel)

Open `data/Funding_Agency_Database.xlsx`, add one row per agency (copy the
style of existing rows — `Agency ID`, `Funding Agency`, `Website` are the
important columns), save, then:

```bash
python -m app.ingest.seed_agencies    # loads new rows, never duplicates
```

Commit and push as above.

## What makes a website scrape well

- The scraper starts at the homepage, follows links whose text/URL contains
  funding words (grant, fellowship, call, proposal, scheme, funding…), and
  stores pages that look like opportunities. So sites with a normal
  **"Funding" / "Grants" / "Calls"** section work best.
- Prefer the **English version** of the site URL when one exists.
- Sites that publish everything as **PDF only** or behind logins extract
  poorly for now (PDF support is a listed next step).
- If a site is JavaScript-heavy and returns empty pages, it needs the
  Playwright fetcher (`USE_PLAYWRIGHT=true` in `.env`) — heavier, works
  locally, not enabled in the GitHub Action.

## How to FIND new funding websites

Practical search queries (Google/Bing):

- `"call for proposals" <your field> 2026`
- `research grants site:.gov.in` (swap the domain: `.gov`, `.eu`, `.ac.uk`…)
- `<country> science funding agency`
- `PhD fellowship funding <field>`

Rich directories to mine — each lists many funders you can add one by one:

- **grants.gov** — every US federal grant programme
- **EU Funding & Tenders Portal** (ec.europa.eu/info/funding-tenders) — all EU calls
- **EURAXESS** (euraxess.ec.europa.eu) — worldwide research funding, searchable
- **UKRI** (ukri.org) — umbrella for the 7 UK research councils
- **DAAD** (daad.de) and its funding database — German + international
- Wikipedia's "List of funders of ..." pages for a field or country

Tip: when you find an aggregator page, the *funders it links to* are your new
agencies — add each funder's own homepage with `add_agency`, since original
sites scrape more reliably than aggregators.

## Quick health check after adding

```bash
python -m app.scraper.run --agency <CODE>     # does it find pages? (see log)
python -m app.llm.run_extraction              # AI-extract what it found
```

Then open the dashboard — the new agency's opportunities should appear.
