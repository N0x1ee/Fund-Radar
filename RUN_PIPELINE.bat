@echo off
REM FundRadar automated pipeline: scrape all agencies, AI-extract new pages,
REM then clean duplicates. Safe to run any time; unchanged pages are skipped
REM and quota-exhausted extractions are retried automatically on the next run.
REM Logs go to logs\pipeline_YYYY-MM-DD.log
cd /d "%~dp0"
".venv\Scripts\python.exe" -m app.run_pipeline
".venv\Scripts\python.exe" -m app.ingest.dedupe
