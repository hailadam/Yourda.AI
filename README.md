# Yourda.AI V16 — React + FastAPI local MVP

The approved **editorial public homepage and original white Y logo** are preserved. A responsive navy-and-gold social financial-research workspace sits behind “Enter Yourda”. This V16 version is React + Vite, **not Flutter**. No Docker is needed for local use.

## Run the entire project with one command (Mac/Linux)

Install Node.js 20+ and Python 3.11–3.12 (Python 3.12 recommended). Open this folder in VS Code, open a terminal at the folder root and run:

```bash
bash scripts/run_local.sh
```

The first run installs Python and npm dependencies. Open **http://localhost:5173** in your browser. The API documentation is at **http://localhost:8000/docs**. Press `Ctrl+C` in the terminal to stop both servers.

This command uses a **local SQLite database** at `backend/yourda_dev.db`. It does not install Flutter or Docker. It does not deploy or connect to a real brokerage.

If you only want to preview the frontend:

```bash
cd frontend
npm install
npm run dev
```

The landing page works without Python; accounts, social features and financial data will display unavailable/offline states when the backend is not running.

## What V16 includes

- Original branding, editorial landing, full-width “RESEARCH IS BETTER TOGETHER” banner, accessible responsive workspace, subtle animations.
- Registration, sign-in/out, public strategy posts, comments/replies, bookmarks, likes, follows, versioned strategy forks, free public communities, simulated paper portfolio.
- **Persistent social state**: your likes, saved research, followed creators and joined communities are loaded from the database when you sign in. The profile displays real account posts and counts.
- **Feed pagination**: explore more research posts beyond the initial result page.
- **Real-data-only price charts**: market dock and research dashboard use licensed provider observations when configured. No fake live prices.
- **Deterministic local research assistant**: explains your account's own research and paper ledger or public strategies, citing their database records. It is explicitly **not** a generative LLM.
- Historic SMA backtest/anomaly endpoints calculate from genuine provider bars when configured, never fabricated statistics.

## Tests and build

```bash
bash scripts/check_local.sh
```

This runs API tests, frontend unit tests and the Vite production build. You must run `npm install` before the build (the one-command launcher does it automatically).

Alternatively:

```bash
cd backend && python -m pytest -q
cd ../frontend && npm test && npm run build
```

Static web output is `frontend/dist/`. Hosting it separately from FastAPI requires API base URL and CORS/HTTPS configuration; development proxy settings do not apply to public hosting.

## Configure actual market data

The existing backend supports an optional Alpaca IEX market-data adapter via `ALPACA_API_KEY` and `ALPACA_API_SECRET` environment variables. Its feed is not a full-market consolidated feed. Verify the data-provider permissions and distribution licensing **before public display**. Without credentials, market-data endpoints fail honestly with HTTP 503. No fabricated fallback prices are used.

## Launch status

This is a **working local MVP**. It is **not** a production-deployed financial platform. External blockers include full Vite/browser checks on a machine with npm access, production authentication with email verification/password recovery, database migrations, abuse moderation, market data licensing, external LLM provider integration, production hosting/security review and payments (currently disabled). The local research assistant is not generative AI. No GitHub push, deployment, paid services or billing has been authorized.

For detailed tested functionality and blockers, see [`RELEASE_STATUS_V16.md`](RELEASE_STATUS_V16.md). The earlier V15 source remains separate and unchanged.
