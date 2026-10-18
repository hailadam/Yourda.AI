#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"
command -v npm >/dev/null || { echo 'Node.js/npm missing. Install Node.js LTS (e.g. brew install node).'; exit 1; }
if [[ ! -d node_modules ]]; then
 echo 'Installing React dependencies…'
 npm install
fi
npm run dev
