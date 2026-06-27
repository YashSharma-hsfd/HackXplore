# Hirth Knowledge Engine — Frontend (React + Vite)

Pixel-faithful implementation of `design_handoff_hirth_knowledge_engine/`, wired
to the real FastAPI backend documented in `../FRONTEND.md`.

## Run

```powershell
# 1. Start the backend first (separate terminal, from repo root)
uv run uvicorn rag_service.main:app --reload      # → http://localhost:8000

# 2. Start the frontend
cd frontend
npm install
copy .env.example .env       # edit if the backend isn't on localhost:8000
npm run dev                  # → http://localhost:4200
```

CORS is already enabled on the backend, so no proxy is needed.

## How the design maps to the real backend

The design handoff uses placeholder `/api/*` names. They are mapped to the real
endpoints here:

| Design concept | Real endpoint | Where |
|---|---|---|
| Submit query | `POST /query` | `lib/api.js` → `App.runQuery` |
| Related domains | `GET /related?entity=` | `App.runQuery` → `RelatedDomains` |
| Edit a fact (chip) | `PATCH /fact` | `FactChip` → `App.onEditFact` |
| "Update vector space" | `POST /tip` | `ReviewOverlay` → `App.onSubmitTip` |
| Upload documents | `POST /ingest` (multipart) | `UploadView` |
| Header / upload stats | `GET /graph` stats + `GET /metrics` | `App.refreshStats` |
| Vector status dot | `GET /health` | `App` mount |

### Derived fields

The backend doesn't return `domain`, `confidence`, or `source`, so the UI derives them:
- **domain** — keyword classification in `lib/domains.js`
- **confidence** — top citation `score`
- **mode** — the Web toggle (`knowledge_base` vs `web`)

## ⚠️ Web search is stubbed

The **Web toggle** and the **"Around the web"** panel are wired to
`src/lib/webSearch.js`, which **returns no results on purpose** — the backend
team's web-search tool isn't ready yet. When it lands, point `webSearch.search()`
at the real endpoint (instructions are in that file). No component changes needed.

## Notes / known gaps

- There is no `/documents` list endpoint, so the Upload view's document list is
  **session-local** (tracks files uploaded in the current session).
- `/ingest` is slow (an AI pass per chunk). For a quick live demo, prefer the
  "Update vector space" tip flow (instant) in the Review overlay.
