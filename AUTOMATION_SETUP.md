# FundRadar — Fully Automated Scraping (GitHub Actions, free)

Once set up, GitHub runs the scraper **every 2 days in the cloud** — your PC can
be off. Each run scrapes all agencies, AI-extracts anything new, and commits the
updated database to the repo, which automatically redeploys Hugging Face and
Render with fresh data. Total cost: ₹0.

The workflow file is `.github/workflows/scrape.yml` (already written).
You only need to do the 3 steps below **once**.

---

## Step 1 — Get your free AI keys (5 minutes)

The pipeline uses `LLM_PROVIDER=auto`: it tries **Gemini** first, and when
Gemini's free daily limit runs out it automatically switches to **Groq**
(free, thousands of requests per day). With both keys you'll basically never
hit a wall — and after the first big run, only *new or changed* pages need AI,
which is usually just a handful per run.

**Gemini key (free):**
1. Go to https://aistudio.google.com/app/apikey (sign in with Google)
2. Click **Create API key** → copy it (starts with `AIza...`)
3. Note: free limits are per *model per day*. FundRadar uses `gemini-2.0-flash`
   and paces itself + retries automatically, so limits pause it, not break it.

**Groq key (free, the safety net):**
1. Go to https://console.groq.com/keys (sign up free)
2. Click **Create API Key** → copy it (starts with `gsk_...`)

## Step 2 — Add the keys to GitHub as secrets

1. Open your repo: https://github.com/N0x1ee/Fund-Radar
2. **Settings** tab → left menu **Secrets and variables** → **Actions**
3. Click **New repository secret**:
   - Name: `GEMINI_API_KEY` — Value: your `AIza...` key → **Add secret**
4. Click **New repository secret** again:
   - Name: `GROQ_API_KEY` — Value: your `gsk_...` key → **Add secret**

Secrets are encrypted; nobody (including you) can read them back.

## Step 3 — Push the new files and test once

```bash
git add .
git commit -m "Add automated 2-day scraping via GitHub Actions"
git push
```

Then test it immediately (don't wait 2 days):

1. On GitHub, open the **Actions** tab
2. Click **Scheduled scrape** in the left list
3. Click **Run workflow** → green **Run workflow** button
4. Watch it run (~10–60 min the first time; much faster after that because
   unchanged pages are skipped)

When it finishes, the repo gets a new commit `Auto-scrape: refresh data (...)`
containing `data/fundradar.db` — and Hugging Face + Render redeploy from it
automatically.

---

## How it works (plain language)

```
every 2 days, 02:00 UTC
        │
GitHub Actions (free cloud computer)
        │  1. restores last database from data/fundradar.db
        │  2. seeds agencies from the Excel (picks up new ones you added)
        │  3. scrapes all 41+ agency websites (unchanged pages skipped)
        │  4. AI-extracts only new/changed pages (Gemini → Groq fallback)
        │  5. commits the updated database back to the repo
        ▼
git push  ──►  sync-to-hf.yml redeploys Hugging Face
          ──►  Render auto-deploys (both boot from data/fundradar.db)
```

## Checking on it later

- **Did it run?** Actions tab → green tick on the latest "Scheduled scrape"
- **What did it find?** Click the run → "Run pipeline" step shows per-agency
  results; the full log is attached as the `pipeline-log` artifact
- **Did the data update?** The site shows fresh opportunities after redeploy

## Changing the schedule

Edit the `cron` line in `.github/workflows/scrape.yml`:

| Want | cron line |
|---|---|
| every 2 days at 02:00 UTC (current) | `0 2 */2 * *` |
| every day | `0 2 * * *` |
| twice a week (Mon+Thu) | `0 2 * * 1,4` |
| weekly (Monday) | `0 2 * * 1` |

## If a run fails

Open the run in the Actions tab and read the red step. The most common causes:
a secret name typo (must be exactly `GEMINI_API_KEY` / `GROQ_API_KEY`), or a
temporary website/API outage — the next scheduled run usually just succeeds.
Nothing breaks: the database only gets committed when a run completes.
