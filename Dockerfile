# FundRadar — container image. Portable across Hugging Face Spaces, Koyeb,
# Fly.io, Render, or any container host.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + data
COPY . .

# Write the SQLite DB to /tmp, the one path guaranteed writable on every host
# (Hugging Face Spaces only allow writes to /tmp). Harmless elsewhere.
ENV DATABASE_URL=sqlite:////tmp/fundradar.db \
    LLM_PROVIDER=mock \
    PYTHONUNBUFFERED=1

# Hugging Face Spaces expect the app on port 7860 by default. Hosts that inject
# their own $PORT (Koyeb, Render, Fly) override this automatically.
EXPOSE 7860

# Boot from the scraped snapshot committed by the GitHub Action (if present),
# then seed (idempotent) and start the server. The app also self-seeds on
# startup if the DB is empty, so this is belt-and-suspenders.
CMD ["sh", "-c", "if [ -f data/fundradar.db ]; then cp data/fundradar.db /tmp/fundradar.db; fi && python -m app.ingest.seed_agencies && python -m app.ingest.load_demo_opportunities && uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
