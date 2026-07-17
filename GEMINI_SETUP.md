# FundRadar — Paid Gemini Setup (for full auto-extraction every 2 days)

The free Gemini tier has tiny daily limits, so a full scrape gets throttled. A
**pay-as-you-go** key removes the limits. For this workload it costs only a few
cents a month. This guide covers the model, the real cost, and setup.

## Model

FundRadar now uses **`gemini-3.1-flash-lite`** — Google's cheapest current text
model. (The old `gemini-2.0-flash` was retired on 1 June 2026.) You don't need to
set the model anywhere; it's the default in `app/config.py`.

## What it will cost you

Pricing for `gemini-3.1-flash-lite` (pay-as-you-go):
`$0.25 per 1M input tokens`, `$1.50 per 1M output tokens`.

FundRadar only calls Gemini for the **extraction** step (turning one scraped page
into structured fields). Each call is a small page snippet in, a small JSON out:

| | tokens | cost |
|---|---|---|
| Input (page snippet + instructions) | ~2,500 | $0.000625 |
| Output (JSON: name, amount, summary…) | ~600 | $0.0009 |
| **Per opportunity** | | **~$0.0015 (about 0.15¢)** |

Putting that against real runs:

- **First full run** (extracts a few hundred pages once): roughly **$0.30–$0.60**.
- **Each 2-day run after** (only *new or changed* pages — usually a handful):
  **a few cents**, often under 5¢.
- **Per month** (~15 runs): typically **under $1**. Budget **$2–3** to be safe.

Because the pipeline is idempotent, it never re-pays to re-extract unchanged
pages — that's what keeps ongoing cost near zero.

## Setup (one time)

### 1. Create the key and enable billing
1. Go to https://aistudio.google.com/app/apikey and **Create API key**
   (starts with `AIza…`). Note which Google Cloud project it's in.
2. Turn on pay-as-you-go: in AI Studio click **Set up billing** (or go to
   https://console.cloud.google.com/billing, and link a billing account with a
   card to that project). The **same key** now runs on the paid tier.

### 2. Put a spending cap on it (recommended)
1. https://console.cloud.google.com/billing → **Budgets & alerts** →
   **Create budget**.
2. Set a small monthly amount (e.g. **$5**) with email alerts at 50% / 90% /
   100%. You'll be warned long before anything meaningful is spent.

### 3. Add the key where the scraping runs
The 2-day scrape runs in **GitHub Actions**, so the key goes there:
1. GitHub → your repo → **Settings → Secrets and variables → Actions**.
2. **New repository secret** → name `GEMINI_API_KEY`, value your `AIza…` key.
   (If it already exists from before, that's fine — the paid tier is decided by
   billing being on, not by the key itself.)
3. Nothing else to change — the workflow already runs the full pipeline every
   2 days with `LLM_PROVIDER=auto` (Gemini first, Groq as backup).

### 4. (Optional) run it locally too
In your `.env`:
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza_your_key
```
Then `python -m app.run_pipeline` scrapes everything and extracts with Gemini.

## Good to know

- **Translation is automatic now.** The extraction prompt tells Gemini to output
  every field in English, and to render non-English scheme names as
  "Original title (English translation)". So future Hindi pages come out
  bilingual on their own.
- **Speed.** The Gemini client paces itself to be gentle on limits, so a big
  first run can take 30–60 min inside the GitHub Action (well under its 2-hour
  cap). Ongoing runs are quick.
- **Groq stays as a free backup.** If Gemini ever errors, the pipeline falls
  back to your Groq key automatically, so a run never fails outright.
