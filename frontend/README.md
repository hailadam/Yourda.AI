# Yourda.AI V16 React frontend

React 18 + Vite implementation of the approved Yourda.AI landing and social research workspace, with the original Y logo, navy-and-gold styling, responsive layouts, strategy feed, price-chart UI, communities, paper portfolio and source-citing local research assistant.

## Start only the frontend (no Flutter or Docker)

```bash
npm install
npm run dev
```

Open http://localhost:5173. The app can render without an API, but data-backed features need FastAPI at port 8000. The Vite development proxy routes `/api` requests to `http://127.0.0.1:8000`.

## Verify and package

```bash
npm test
npm run build
```

Output: `dist/`. Source data and icons are under `src/`; original Y image under `public/brand/`.

The built-in research assistant is deterministic and cites authorized database records; generative AI is not connected. Do not assume provider prices are real-time until configured and licensed.
