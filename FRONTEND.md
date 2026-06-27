# FRONTEND.md — React + Vite integration guide (read this fully)

This backend is a REST API that returns JSON. Your React app just calls these
URLs with `fetch` (or axios). You do **not** need to understand the Python — only
the endpoints below. Everything you need is here.

---

## 0. The 60-second mental model

It's an AI knowledge database for two-stroke engines. The user asks a question;
the backend returns:
- an **answer** (text),
- **citations** (the source chunks it used),
- **facts** (exact structured values from a knowledge graph, which are editable).

There's also a **knowledge graph** you can draw, a **related topics** feature,
a **web-search toggle**, and the ability to **edit facts / add tips**. Build
screens around those.

---

## 1. Start the backend (do this first, or you have nothing to call)

```powershell
cd C:\Users\avish\Desktop\haka
uv sync                       # one-time: installs deps (downloads ~4GB of models on first run)
uv run uvicorn rag_service.main:app --reload
```

- API is now at **`http://localhost:8000`**.
- Open **`http://localhost:8000/docs`** in a browser → this is **Swagger**: a
  clickable page to test every endpoint by hand. Use it to see real responses
  before you write React code. (Swagger is just a testing tool — your React app
  does NOT use it.)
- The corpus is already loaded (the engine PDFs + spreadsheets). You can query
  immediately.

**CORS is already enabled** (wildcard), so your Vite dev server
(`http://localhost:5173`) can call `http://localhost:8000` with no extra setup —
no proxy needed.

---

## 2. React + Vite setup

Create `.env` in your React project root (Vite reads `VITE_`-prefixed vars):
```
VITE_API_URL=http://localhost:8000
```
Access it in code as `import.meta.env.VITE_API_URL`. **Never hardcode
`localhost:8000`** — when the backend deploys, you change only this one line.

> Vite env files: `.env` (all), `.env.development`, `.env.production`. Only vars
> starting with `VITE_` are exposed to the browser.

### Shortcut: auto-generate TypeScript types from the API
With the backend running:
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/api/types.ts
```
That gives you exact TS types for every request/response — no hand-writing them.
(Optional: `openapi-fetch` gives a tiny typed `fetch` wrapper that uses those
types. Both are optional — plain `fetch` works fine; see §4.)

---

## 3. The endpoints (the whole API)

Base URL = `import.meta.env.VITE_API_URL` (`http://localhost:8000`). All
request/response bodies are JSON (except file upload). Every endpoint with an
exact example:

### 🔹 POST `/query` — ask a question (THE main one)
Request:
```json
{ "question": "What is the freezing point of Jet A1?", "top_k": 8, "web_search": false }
```
(`top_k` optional, 1–20, default 8. `web_search` optional, default `false` — see
the **web-search toggle** note below.)

Response:
```json
{
  "answer": "The freezing point of Jet A1 is -47 °C.",
  "citations": [
    { "chunk_id": "a1b2c3...", "source": "Fuel_Kraftstoffe_Übersicht_Daten.xlsx",
      "title": "", "score": 0.87, "snippet": "Jet A1 | freezing point | -47 °C ...",
      "url": "", "source_type": "corpus" }
  ],
  "facts": [
    { "id": "spec::jet a1::freezing point", "subject": "Jet A1",
      "attribute": "freezing point", "value": "-47", "unit": "°C", "curated": false }
  ],
  "latency_ms": 1840,
  "cost_usd": 0.000013
}
```
- Show `answer` big. Show `citations` as expandable source cards (use `snippet`
  + `source`). Show `facts` as chips — **each fact is editable** (see `/fact`).
- Keep `chunk_id` (for editing a chunk) and `facts[].id` (for editing a fact).

#### 🌐 The web-search toggle (`web_search`)
Add a toggle/button next to the search box (like the web-search button in other
AI apps). When the user turns it **on**, send `"web_search": true` in the same
`/query` body — that's the **entire** integration; no new endpoint.

What changes in the response when `web_search: true`:
- The answer comes from a **live web search** (Tavily), not the local corpus.
- `citations[]` have **`source_type: "web"`** and a real **`url`**; `chunk_id` is
  `""` and `facts` is `[]` (web hits aren't editable graph facts).
- **Render web citations distinctly** — e.g. a 🌐 globe + the domain (`source`),
  and make the card a link that opens `url` in a new tab (`target="_blank"`).

Gotchas:
- Needs `TAVILY_API_KEY` set on the backend. If it's missing, `/query` returns
  **HTTP 503** with a message — show a friendly "web search unavailable" toast.
- Branch your citation card on `source_type` (`"corpus"` vs `"web"`).
- `web_search` defaults to `false`, so existing corpus queries are unchanged.

### 🔹 GET `/graph?limit=150` — the knowledge graph (for the visual panel)
Response:
```json
{
  "nodes": [
    { "id": "ent::jet a1", "label": "Jet A1", "group": "entity", "curated": false },
    { "id": "spec::jet a1::freezing point", "label": "freezing point: -47 °C",
      "group": "spec", "curated": false }
  ],
  "edges": [ { "from": "ent::jet a1", "to": "spec::jet a1::freezing point", "label": "freezing point" } ],
  "stats": { "nodes": 1245, "edges": 1070, "specs": 509 }
}
```
- Draw with **`vis-network`** (`npm i vis-network`). In React, render into a
  `useRef` div inside a `useEffect` (see §4). It uses exactly `id`/`label` and
  `from`/`to`, so feed `nodes`/`edges` straight in.
- Colour nodes by `group`: `"entity"` vs `"spec"`. Mark `curated:true` ones
  specially (they're human-edited).
- ⚠️ Use `limit=150` (not the full 1245) or the graph is slow/cluttered.

### 🔹 GET `/related?entity=Jet A1&depth=1` — "related topics" (recommendation)
Response:
```json
{ "entity": "Jet A1", "related": [
  { "id": "spec::jet a1::density", "label": "density: 0.775–0.825 kg/dm³", "kind": "spec", "value": "0.775–0.825" },
  { "id": "ent::jp-8", "label": "JP-8", "kind": "entity" }
]}
```
- Show as a sidebar list of clickable related items.

### 🔹 PATCH `/fact` — edit a structured value (THE differentiator feature)
Request:
```json
{ "id": "spec::jet a1::freezing point", "new_value": "-50" }
```
Response: the updated fact (now `"curated": true`).
- Wire this to an "edit" pencil on each fact chip. After saving, **re-run the
  same `/query`** to show the answer now reflects the new value. That's the
  money demo moment.

### 🔹 PATCH `/chunk/{chunk_id}` — edit a source chunk's text
Request (path = the `chunk_id` from a citation):
```json
{ "new_text": "corrected text here" }
```
or metadata only: `{ "new_metadata": { "topic": "tuning" } }`.
- Lower priority for the UI; the fact-edit above is the headline.

### 🔹 POST `/tip` — add a free-text tip (contribution loop)
Request:
```json
{ "text": "On the F-23, if it bogs at full throttle, lower the needle clip one notch." }
```
Response: `{ "document_id": "...", "source": "user tip", "n_chunks": 1 }`.
- A textarea + "Submit tip" button. After submit, ask a related question to show
  it's instantly searchable.

### 🔹 POST `/ingest` — upload a file (PDF / XLSX / DOCX)
- **multipart/form-data**, field name `file`. Not JSON — use `FormData` (see §4).
- ⚠️ **SLOW**: a big PDF runs an AI pass per chunk and can take minutes. Show a
  spinner and set a long timeout. For the live demo prefer `/tip` (instant).

### 🔹 POST `/ingest-url` — ingest a web page
Request: `{ "url": "https://forum.example/thread/123" }` (also slow-ish).

### 🔹 GET `/metrics` — live stats (for a footer/dashboard)
```json
{ "cache_hit_rate": 0.4, "n_queries": 12, "total_cost_usd_today": 0.0021,
  "p50_latency_ms": 1800, "p95_latency_ms": 3200, ... }
```

### 🔹 GET `/health` → `{ "status": "ok" }` (uptime check)

---

## 4. Minimal React API helper (plain `fetch`, zero deps)

`src/api.js` (or `.ts`):
```js
const API = import.meta.env.VITE_API_URL;

async function post(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.json()).detail ?? res.statusText}`);
  return res.json();
}
async function patch(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}
async function get(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export const api = {
  query: (question, topK = 8, webSearch = false) =>
    post("/query", { question, top_k: topK, web_search: webSearch }),
  graph: (limit = 150) => get(`/graph?limit=${limit}`),
  related: (entity) => get(`/related?entity=${encodeURIComponent(entity)}`),
  editFact: (id, new_value) => patch("/fact", { id, new_value }),
  submitTip: (text) => post("/tip", { text }),
  metrics: () => get("/metrics"),
};
```

Use it in a component:
```jsx
import { useState } from "react";
import { api } from "./api";

export function Search() {
  const [q, setQ] = useState("");
  const [web, setWeb] = useState(false);
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);

  async function ask() {
    setLoading(true);
    try { setRes(await api.query(q, 8, web)); }
    catch (e) { alert(e.message); }       // 503 here = web search needs TAVILY_API_KEY
    finally { setLoading(false); }
  }

  return (
    <div>
      <input value={q} onChange={(e) => setQ(e.target.value)} />
      <label><input type="checkbox" checked={web} onChange={(e) => setWeb(e.target.checked)} /> 🌐 Web search</label>
      <button onClick={ask} disabled={loading}>{loading ? "…" : "Ask"}</button>
      {res && <p>{res.answer}</p>}
    </div>
  );
}
```

Drawing the graph (`vis-network`) in React:
```jsx
import { useEffect, useRef } from "react";
import { Network } from "vis-network";
import { api } from "./api";

export function GraphPanel() {
  const ref = useRef(null);
  useEffect(() => {
    api.graph(150).then(({ nodes, edges }) => {
      new Network(ref.current, { nodes, edges }, {}); // ids/labels/from/to already match vis
    });
  }, []);
  return <div ref={ref} style={{ height: 500 }} />;
}
```

File upload (`/ingest`) uses `FormData`, not JSON:
```js
const fd = new FormData();
fd.append("file", file);                 // `file` from an <input type="file">
await fetch(`${import.meta.env.VITE_API_URL}/ingest`, { method: "POST", body: fd });
```

---

## 5. The screens to build (map each to an endpoint)

1. **Search/chat** (main): input + web toggle → `api.query()`. Render `answer`,
   then `facts` as editable chips, then `citations` as collapsible source cards
   (branch card style on `source_type` — corpus vs 🌐 web).
2. **Knowledge graph panel**: `api.graph()` → vis-network. Click a `spec` node →
   open the edit-fact dialog; click an `entity` node → call `api.related()`.
3. **Related topics** sidebar: `api.related(entity)` list.
4. **Edit a fact** dialog: pencil on a fact chip → `api.editFact(id, newValue)` →
   then re-call `api.query()` with the same question to show it changed.
5. **Add knowledge**: a textarea → `api.submitTip()`; (optional) file upload → `/ingest`.
6. **Footer**: `api.metrics()` (queries, latency, cost).

---

## 6. Common mistakes (don't do these)

- ❌ Sending `document_id` in `/query`. It does NOT exist — the API rejects
  unknown fields. `/query` body is only `{ question, top_k, web_search }`.
- ❌ Hardcoding `localhost:8000`. Use `import.meta.env.VITE_API_URL`.
- ❌ Reading env as `process.env.*`. Vite uses `import.meta.env.VITE_*`.
- ❌ Drawing the full graph (1245 nodes). Use `/graph?limit=150`.
- ❌ Expecting `/ingest` to be instant. It's slow (AI pass). Use `/tip` for live demos.
- ❌ Ignoring the 503 from `/query` when `web_search:true` — that means the
  backend has no `TAVILY_API_KEY`. Show a toast, don't crash.
- ❌ `cost_usd` is tiny (like `0.000013`) — format with enough decimals or show "≈ $0".
- ❌ Forgetting the spinner/timeout on `/query` and `/ingest` — answers take ~2–30s.

---

## 7. The demo flow to support (so the UI tells a story)

1. Ask a real question → cited answer + an exact **fact** chip.
2. Show the **graph** (entities ↔ specs, linked across docs).
3. Click an entity → **related topics**.
4. **Edit the fact** value → re-ask the same question → answer updates live.
5. **Submit a tip** → ask about it → it's already searchable.
6. (Optional) flip the **🌐 web-search toggle** → same question answered from the
   live web, with web-styled citations.

That sequence is the winning demo. Build the UI to make those steps smooth.
