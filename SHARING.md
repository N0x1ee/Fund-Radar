# Sharing FundRadar — teammate access + a live link for your professor

Two parts:
- **Part A** puts everything on GitHub so your teammate has the full project (and
  can review the code).
- **Part B** deploys the app to a free host so your professor gets a permanent
  link to the live dashboard + chatbot.

Do Part A first — Part B deploys *from* GitHub.

---

## Part A — Share everything with your teammate (GitHub)

One-time, on your computer:

1. Install Git from https://git-scm.com and create a free account at github.com.
2. If a leftover `.git` folder exists in the project, delete it (File Explorer,
   or `rmdir /s /q .git`). Then, in `C:\internship\project`:

```
git init
git add .
git commit -m "FundRadar project"
```

3. On github.com click **New repository**, name it `fundradar`, leave it empty
   (no README), and create it. Then connect and push:

```
git remote add origin https://github.com/<your-username>/fundradar.git
git branch -M main
git push -u origin main
```

4. Add your teammate: on the repo page, **Settings → Collaborators → Add people**,
   enter their GitHub username. They accept the invite, then clone it:

```
git clone https://github.com/<your-username>/fundradar.git
```

Day-to-day: `git pull` before you start, then `git add .`, `git commit -m "what
you did"`, `git push` when done. Your `.env` and the `.db` file are not shared
(they're gitignored) — each person keeps their own and runs the seed commands.

> This same GitHub link is also what your professor would use if she wants to
> review the **code and documents**, not just the live app.

---

## Part B — A permanent live link for your professor (deploy on Render)

Render runs your app on the internet for free and gives you a public URL. It
reads the included `render.yaml`, so there's almost nothing to configure.

1. Finish Part A (your code must be on GitHub).
2. Go to https://render.com and **Sign up with GitHub** (free).
3. Click **New +  →  Blueprint**.
4. Select your `fundradar` repository. Render detects `render.yaml` and shows a
   service called "fundradar". Click **Apply / Create**.
5. Wait a few minutes for "Build" then "Live". Render gives you a URL like:

```
https://fundradar.onrender.com
```

6. Share that link with your professor. Opening it shows the dashboard; the
   stats, tables and the Ask FundRadar chatbot all work, loaded with the real
   demo data (the app seeds itself automatically on startup).

### Good to know
- **Free tier sleeps when idle.** After ~15 minutes of no visitors the app
  pauses; the next visit takes ~30–50 seconds to wake, then it's fast. Tell your
  professor the first load may be slow — that's normal, not an error.
- **Updating the live site:** just `git push` your changes; Render redeploys
  automatically.
- **Alternative host:** Railway (railway.app) works similarly if you prefer it.

### Optional — natural-language chatbot on the live site
By default the deployed chatbot replies with a tidy list (no API key needed). To
make it answer in full sentences:
1. Add `google-generativeai>=0.8` to `requirements.txt` and push.
2. In Render → your service → **Environment**, add:
   `LLM_PROVIDER = gemini` and `GEMINI_API_KEY = <your free key>`.
3. Save — Render redeploys and the chatbot now phrases natural answers.

---

## Quick summary

| Goal | Tool | What to share |
|------|------|---------------|
| Teammate has the full project | GitHub | the repo link (+ add as collaborator) |
| Professor reviews the code/docs | GitHub | the repo link |
| Professor uses the live app | Render | the `https://...onrender.com` link |
