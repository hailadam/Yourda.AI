#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
command -v python3 >/dev/null || { echo 'Python 3 missing'; exit 1; }
if [[ ! -d .venv ]]; then
 python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export ENVIRONMENT=development
export DATABASE_URL="sqlite:///./yourda_dev.db"
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
