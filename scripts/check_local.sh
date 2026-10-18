#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo '== Python backend =='
cd "$ROOT/backend"
if [[ -x .venv/bin/python ]]; then .venv/bin/python -m pytest -q; else python3 -m pytest -q; fi
echo '== React utility tests =='
cd "$ROOT/frontend"
node --test tests/*.test.mjs
echo '== Vite production build =='
if [[ ! -d node_modules ]]; then
 echo 'React dependencies not installed. Run npm install in frontend/ before checking the production build.'
 exit 2
fi
npm run build
