# FundRadar — Automating the Scraper (every 2 days)

Goal: a server runs the scraper + AI extraction automatically every 2 days, so
the database stays fresh with no manual work.

The job itself is one command — `python -m app.run_pipeline` — which scrapes every
agency and AI-extracts anything new or changed. It is safe to re-run: unchanged
pages are skipped (content-hash check), only new/changed ones are processed.

---

## 1. Get a server

Any always-on Linux machine works. Cheapest practical options: a small cloud VM
(e.g. a $5-6/month instance on DigitalOcean, Hetzner, AWS Lightsail, etc.) running
Ubuntu 22.04+. "Always-on" is the point — unlike a laptop, it doesn't need to be
awake at run time.

## 2. One-time setup on the server

```bash
# install python + git
sudo apt update && sudo apt install -y python3 python3-venv git

# get the project onto the server (via git, or scp the folder up)
git clone <your-repo-url> fundradar     # or copy the folder
cd fundradar

# create the environment and install everything (core + scraper + AI)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install httpx beautifulsoup4 google-generativeai   # scraper + AI deps

# settings
cp .env.example .env
nano .env        # set: LLM_PROVIDER=gemini  and  GEMINI_API_KEY=your_key

# seed the agencies once
python -m app.ingest.seed_agencies
```

Get a free Gemini key at https://aistudio.google.com/app/apikey.

## 3. Make the job runnable

```bash
chmod +x run_pipeline.sh
./run_pipeline.sh        # test it once by hand; watch the output
```

A log is written to `logs/pipeline_YYYY-MM-DD.log` each run.

## 4. Schedule it every 2 days (cron)

```bash
crontab -e
```

Add this line (runs at 02:00 every second day):

```
0 2 */2 * * /full/path/to/fundradar/run_pipeline.sh >> /full/path/to/fundradar/logs/cron.log 2>&1
```

Replace `/full/path/to/fundradar` with the real path (run `pwd` in the project
folder to get it).

Note: `*/2` on the day-of-month means days 1,3,5,…; at month boundaries the gap
can be 1 day. If you need an exact 48-hour cycle, use a systemd timer instead
(below).

### Precise alternative — systemd timer (exact 48h)

`/etc/systemd/system/fundradar.service`
```
[Service]
Type=oneshot
WorkingDirectory=/full/path/to/fundradar
ExecStart=/full/path/to/fundradar/run_pipeline.sh
```

`/etc/systemd/system/fundradar.timer`
```
[Timer]
OnUnitActiveSec=2d
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fundradar.timer
systemctl list-timers fundradar.timer     # confirm next run
```

## 5. Keep the website running too (optional)

The scheduled job updates the data. To also serve the dashboard/API continuously,
run uvicorn as its own service:

`/etc/systemd/system/fundradar-web.service`
```
[Service]
WorkingDirectory=/full/path/to/fundradar
ExecStart=/full/path/to/fundradar/.venv/bin/uvicorn app.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now fundradar-web
```
Then the dashboard is reachable at `http://<server-ip>:8000/`.

## 6. Checking it works

- `tail -f logs/pipeline_*.log` — watch a run live.
- Each run logs: agencies scraped, new/changed/unchanged counts, and extraction results.
- `systemctl list-timers` — see when the next run is scheduled.

---

### Notes / honest caveats
- JavaScript-heavy agency sites and PDF-only calls still need the Playwright +
  PDF steps (Phase 2b) for full coverage; without them those sites return little.
- The Gemini free tier (~1,500 requests/day) is plenty for a 2-day cycle over
  ~41 agencies.
- Start with `python -m app.run_pipeline --limit 5` to validate before scaling to all.
