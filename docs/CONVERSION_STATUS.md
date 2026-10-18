# Flutter V14 → React V15 migration

## Converted

- Public editorial homepage: headline, pale-blue hero, actual transparent white Y brand mark, visual research art, long-form feature sections, horizontal brand banner, footer
- Responsive navigation, navy/gold member workspace and fixed collapsible market dock
- Discover/Strategies: real API feed/search, ticker filters, recent research cards, creator follow, like/save, authenticated publishing, discussion threads, strategy forks with original-vs-fork rule comparison
- Markets: supported ETF proxies, observed quotes, interactive historical SVG line chart, 1D/1W/1M/3M/1Y, surge ranking, anomaly contract and fee-aware SMA backtesting
- Communities: backend-backed public/free community listing, creation and joining; premium teaser clearly disabled
- Portfolio: private paper account, virtual cash and user-entered simulated orders
- AI: research-assistant shell connected to actual endpoint, displays honest server error; no fake AI messages
- Profile: current signed-in identity and sign out

## Preserved

- `backend/app` and `backend/tests` from V14; no changes to FastAPI schemas required
- Exact uploaded white Y symbol asset from original Flutter project
- Approved editorial public visual identity and distinct navy-gold internal research workspace
- Security expectations: auth required for mutations, bearer token only in memory, no token storage in localStorage, client treats 503 from providers honestly

## Not converted / still blocked

- Native iOS/Android Flutter experiences (React is a browser frontend; consider React Native later if needed)
- Paid private groups, moderation dashboard, email verification, production session refresh, AI provider/citations
- Backend's unimplemented real chat service and licensing/keys for IEX/market providers
- Optional original Flutter-only animated chart rendering details; replaced with accessible responsive SVG line charts
- Real-time streaming, brokerage execution and high-fidelity backtest/signal verification

## Test evidence

- Source TSX parsing: passed locally on all React components
- Node unit tests: passed 4/4
- V14 FastAPI tests: passed 10/10
- npm dependencies unavailable in artifact-build environment (registry inaccessible) → final Vite build and browser QA pending on Mac; do not claim production build passed

## Backend APIs consumed

- `GET /api/v1/feed`
- `POST /api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/logout`
- `POST /api/v1/strategies`, `/api/v1/strategies/{id}/forks`, `/api/v1/strategies/{id}/comments`, `/api/v1/strategies/{id}/like`, `/api/v1/strategies/{id}/bookmark`
- `GET /api/v1/strategies/{id}/comments`
- `POST /api/v1/users/{handle}/follow`
- `GET/POST /api/v1/communities` and `/api/v1/communities/{id}/join`
- `GET /api/v1/portfolio/paper`, `POST /api/v1/portfolio/paper/orders`
- `GET /api/v1/markets/overview`, `/api/v1/markets/history`, `/api/v1/markets/anomalies`
- `POST /api/v1/backtests`, `/api/v1/assistant/messages`

No keys should be placed inside React source or any `VITE_*` variable; these are public once built. Provider secrets remain on the backend.
