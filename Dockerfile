# FundRadar — container image (portable: Render, Railway, Fly.io, any host).
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + data
COPY . .

ENV LLM_PROVIDER=mock \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Seed the DB (idempotent) then start the server. The app also self-seeds on
# startup if the DB is empty, so this is belt-and-suspenders.
CMD ["sh", "-c", "python -m app.ingest.seed_agencies && python -m app.ingest.load_demo_opportunities && uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
