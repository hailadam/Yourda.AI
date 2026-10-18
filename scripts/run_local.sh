#!/usr/bin/env bash
# Start the complete free/local Yourda.AI development MVP (without Docker/Flutter).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v python3 >/dev/null || { echo 'Python 3.11+ is required (3.12 recommended).'; exit 1; }
command -v npm >/dev/null || { echo 'Node.js/npm are required. On Mac: brew install node'; exit 1; }
cd "$ROOT/backend"
if [[ ! -x .venv/bin/python ]]; then
 echo 'Creating a Python virtual environment...'
 python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import fastapi, sqlalchemy, argon2, uvicorn' >/dev/null 2>&1; then
 echo 'Installing Python dependencies for the local API...'
 .venv/bin/python -m pip install -r requirements-dev.txt
fi
export ENVIRONMENT=development
export DATABASE_URL="sqlite:///./yourda_dev.db"
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > "$ROOT/backend/yourda_api.log" 2>&1 &
API_PID=$!
cleanup(){ kill "$API_PID" 2>/dev/null || true; wait "$API_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
for _ in {1..30}; do
 if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then break; fi
 if ! kill -0 "$API_PID" 2>/dev/null; then echo 'Backend failed to start. Review backend/yourda_api.log'; exit 1; fi
 sleep 1
done
if ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then echo 'Backend did not become healthy; see backend/yourda_api.log'; exit 1; fi
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
 echo 'Installing React dependencies (first run only)...'
 npm install
fi
echo
printf 'Yourda.AI backend: http://localhost:8000/docs\nYourda.AI website: http://localhost:5173\nPress Ctrl+C to stop both services.\n\n'
npm run dev
