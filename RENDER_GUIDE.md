# Deploying FundRadar for your professor — step by step (Render)

This gives your professor a permanent link (e.g. https://fundradar.onrender.com)
to the live dashboard + chatbot. Free, no credit card, deploys from your GitHub.

Prerequisite: your project is already on GitHub (see GITHUB_GUIDE.md). The repo
already contains `render.yaml`, which tells Render exactly how to run everything.

---

## Steps

1. Go to https://render.com and click **Get Started** / **Sign in**. Choose
   **Sign in with GitHub** and log in with the same GitHub account. No credit
   card is required.
2. When GitHub asks, **Authorize Render** so it can see your repositories. You can
   allow just the `fundradar` repo or all of them.
3. In the Render dashboard, click **New +** (top right) and choose **Blueprint**.
   (A "blueprint" means Render reads the `render.yaml` file in your repo.)
4. Find and select your **fundradar** repository, then click **Connect**.
5. Render reads `render.yaml` and shows a service named **fundradar**. It may ask
   for a "Blueprint name" — anything is fine. Click **Apply** (or **Create
   Services**).
6. Render now builds it: you'll see logs scrolling. Wait until the status turns
   from **Building** to **Live** (usually 2–5 minutes the first time).
7. At the top of the service page you'll see the public URL, like:

   `https://fundradar.onrender.com`

   Click it to check it works — you should see your dashboard. 

8. Copy that URL and send it to your professor.

---

## Tell your professor one thing

On the free plan the app "sleeps" after 15 minutes with no visitors. The **first**
time she opens the link after a quiet period, it takes about **30–60 seconds** to
wake up and load. That's normal — after that it's quick. (If a paid, always-awake
version is needed later, that's a small upgrade.)

## Updating the live site later

Whenever you push changes to GitHub (Commit → Push in GitHub Desktop), Render
automatically rebuilds and updates the live link. Nothing else to do.

## If something goes wrong

- **Build failed:** open the **Logs** tab on the service and read the last red
  lines. Most issues are a missing package — tell me the error and I'll fix it.
- **No "Blueprint" option:** use **New + → Web Service** instead, connect the repo,
  and set Build Command to `pip install -r requirements.txt` and Start Command to:
  `python -m app.ingest.seed_agencies && python -m app.ingest.load_demo_opportunities && uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
- **Page loads but no data:** the app seeds itself on startup; if the table is
  empty, open Logs and check the seed step ran — share it with me.

## Optional — natural-language chatbot on the live site

By default the live chatbot replies with a tidy list (no key needed). To make it
answer in full sentences: add `google-generativeai>=0.8` to `requirements.txt`,
push, then in Render → your service → **Environment** add `LLM_PROVIDER=gemini`
and `GEMINI_API_KEY=<your key>`, and save.
