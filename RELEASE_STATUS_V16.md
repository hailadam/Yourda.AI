# Yourda.AI V16 — implementation and release status

## What is actually implemented

- React 18 + Vite responsive frontend with approved editorial landing, original white Y logo, navy/gold research area and motion-reduction handling.
- Python FastAPI local backend with SQLite for development and PostgreSQL support for a separately configured environment.
- Persistent accounts, password hashing, opaque server-revocable sessions, public strategy posts, nested discussions, fork versioning, creator follows, likes, bookmarks, public free communities and paper trading.
- Account-level API for the user's saved posts, follows, likes and joined communities; React now hydrates these values after login. Authored strategies appear in the profile.
- Research feed pagination, filtering and more-results control.
- Historical market chart interface and bottom-left dock request **real provider observations only**, without synthetic live quotes. Missing credentials produce clear unavailable-data states.
- Historical SMA backtest and anomaly computations from authorized provider observations; not a forecasting service.
- An authenticated deterministic **local research assistant**: grounded summaries of your own posts, your paper ledger, or public strategies with source references. It is **not** a generative language model.
- Mac-friendly launcher (`bash scripts/run_local.sh`), local verification script, and example CI test/build workflow. Neither script pushes or deploys anything.

## Verified in build environment

- `python -m pytest -q`: 13 tests passed.
- `node --test frontend/tests/*.test.mjs`: 4 tests passed.
- React source parsed as JSX with TypeScript's installed parser; no syntax diagnostics.
- Source import paths and ZIP CRC checked after packaging.
- Real local HTTP smoke test passed: startup/health, account creation, publishing a research post, feed query, saved-bookmark persistence, source-citing assistant answer, disabled market feed, logout and session revocation.

## Not verified or not yet launch-ready

- **Vite production bundle has not run in this environment**: npm registry access is unavailable. Run `cd frontend && npm install && npm run build` on a machine with internet.
- React browser interaction/a11y/end-to-end checks need a local browser after dependencies are installed.
- Market provider credentials/market data redistribution licenses are not supplied. The provider is IEX-specific, not a consolidated national market feed.
- Generative LLM, paid/private communities and real-money brokerage transactions are not enabled. The local assistant is not generative AI.
- Email verification, password reset, hardened session handling and abuse moderation, migrations, production Postgres, public hosting, privacy/legal reviews, monitoring, penetration testing and licensed market-data distribution are needed before launch.

## How to run on a Mac (NO Docker and NO Flutter)

Open the extracted folder in VS Code, then from project root:

```bash
bash scripts/run_local.sh
```

This starts the local SQLite-backed FastAPI server and the React dev server. Open http://localhost:5173. For backend status open http://localhost:8000/health. Stop with Ctrl+C. First run downloads packages and requires internet.

**Frontend only:** `cd frontend && npm install && npm run dev`. You can preview the landing page without the backend, but accounts, saved posts and real data will be offline.

**Build:** `bash scripts/check_local.sh` after dependencies are installed. React static build output is `frontend/dist/`.

**Production caution:** This is a tested local full-stack MVP, **not** a completed production deployment. No push, deployment, live trading or billing action has been taken.
