#!/usr/bin/env bash
# FundRadar — every-2-days job. Called by cron on the server.
# Make executable once:  chmod +x run_pipeline.sh
set -euo pipefail
cd "$(dirname "$0")"                 # project directory
source .venv/bin/activate            # virtual environment
python -m app.run_pipeline           # scrape all agencies + AI extract
