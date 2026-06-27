# Deploy FundRadar — quick path to a public URL

The app is a single FastAPI service that serves the multi-page web app + JSON API
and **self-seeds the database on startup** (41 agencies + 25 demo opportunities),
so a fresh deploy shows real data with zero manual steps.

## Recommended: Render (config already in `render.yaml`)

### Step 1 — Put the code on GitHub (one time)
From a terminal in this project folder:

```bash
git init
git add .
git commit -m "FundRadar demo: multi-page web app + API"
git branch -M main
git remote add origin https://github.com/<your-username>/fundradar.git
git push -u origin main
```

(Create the empty `fundradar` repo first at https://github.com/new — no README.)

### Step 2 — Deploy on Render (free, no card)
1. Sign in at https://render.com with **GitHub**.
2. **New +** → **Blueprint** → pick the `fundradar` repo → **Apply**.
3. Wait ~3–5 min for **Building → Live**.
4. Copy the public URL, e.g. `https://fundradar.onrender.com`.

That URL is what your professor opens. Pages: Dashboard, Funding Agencies,
Funding Opportunities, Scraper Status, Database, API, Project Progress, About.

> Free tier sleeps after 15 min idle; first visit after a pause takes ~30–60s to
> wake. Normal.

## Environment variables
| Key | Value | Why |
|-----|-------|-----|
| `LLM_PROVIDER` | `mock` | App + chatbot work with no API key (list-based answers). Set to `gemini` + `GEMINI_API_KEY` for natural-language chatbot replies. |
| `PYTHON_VERSION` | `3.12.4` | Pinned for reproducible builds (Render). |

All are already declared in `render.yaml` — nothing to set by hand for the basic demo.

## Alternative: Docker (Railway / Fly.io / any host)
A `Dockerfile` is included.

```bash
docker build -t fundradar .
docker run -p 8000:8000 fundradar
# open http://localhost:8000
```
