# FRONTEND.md — Angular integration guide (read this fully)

This backend is a REST API that returns JSON. Your Angular app just calls these
URLs with `HttpClient`. You do **not** need to understand the Python — only the
endpoints below. Everything you need is here.

---

## 0. The 60-second mental model

It's an AI knowledge database for two-stroke engines. The user asks a question;
the backend returns:
- an **answer** (text),
- **citations** (the source chunks it used),
- **facts** (exact structured values from a knowledge graph, which are editable).

There's also a **knowledge graph** you can draw, a **related topics** feature,
and the ability to **edit facts / add tips**. Build screens around those.

---

## 1. Start the backend (do this first, or you have nothing to call)

```powershell
cd C:\Users\avish\Desktop\haka
uv sync                       # one-time: installs deps (downloads ~3.4GB of models on first run)
uv run uvicorn rag_service.main:app --reload
```

- API is now at **`http://localhost:8000`**.
- Open **`http://localhost:8000/docs`** in a browser → this is **Swagger**: a
  clickable page to test every endpoint by hand. Use it to see real responses
  before you write Angular code. (Swagger is just a testing tool — your Angular
  app does NOT use it.)
- The corpus is already loaded (the engine PDFs + spreadsheets). You can query
  immediately.

**CORS is already enabled**, so your Angular dev server (`http://localhost:4200`)
can call `http://localhost:8000` with no extra setup.

---

## 2. Angular setup

`src/environments/environment.ts`:
```ts
export const environment = { apiUrl: 'http://localhost:8000' };
```

Make sure `HttpClientModule` (or `provideHttpClient()`) is imported in your app.

### Shortcut: auto-generate the whole typed API client
With the backend running:
```bash
npx ng-openapi-gen --input http://localhost:8000/openapi.json --output src/app/api
```
This reads the API schema and generates Angular services + TypeScript types for
every endpoint automatically. **Strongly recommended** — then you don't hand-write
any of the request/response types. If you do that, skip to §4.

---

## 3. The endpoints (the whole API)

Base URL = `http://localhost:8000`. All request/response bodies are JSON
(except file upload). Here is every endpoint with an exact example.

### 🔹 POST `/query` — ask a question (THE main one)
Request:
```json
{ "question": "What is the freezing point of Jet A1?", "top_k": 8 }
```
(`top_k` optional, 1–20, default 8.)

Response:
```json
{
  "answer": "The freezing point of Jet A1 is -47 °C.",
  "citations": [
    { "chunk_id": "a1b2c3...", "source": "Fuel_Kraftstoffe_Übersicht_Daten.xlsx",
      "title": "", "score": 0.87, "snippet": "Jet A1 | freezing point | -47 °C ..." }
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
- Draw with **`vis-network`** (easiest) — `npm i vis-network`. Feed `nodes` and
  `edges` straight in (vis uses exactly `id`/`label` and `from`/`to`).
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
- **multipart/form-data**, field name `file`. Not JSON.
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

## 4. Minimal Angular service (if you didn't auto-generate)

```ts
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../environments/environment';

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  query(question: string, topK = 8) {
    return this.http.post(`${API}/query`, { question, top_k: topK });
  }
  graph(limit = 150)   { return this.http.get(`${API}/graph?limit=${limit}`); }
  related(entity: string) {
    return this.http.get(`${API}/related?entity=${encodeURIComponent(entity)}`);
  }
  editFact(id: string, new_value: string) {
    return this.http.patch(`${API}/fact`, { id, new_value });
  }
  submitTip(text: string) { return this.http.post(`${API}/tip`, { text }); }
  metrics()               { return this.http.get(`${API}/metrics`); }
}
```

---

## 5. The screens to build (map each to an endpoint)

1. **Search/chat** (main): input → `query()`. Render `answer`, then `facts` as
   editable chips, then `citations` as collapsible source cards.
2. **Knowledge graph panel**: `graph()` → vis-network. Click a `spec` node →
   open the edit-fact dialog; click an `entity` node → call `related()`.
3. **Related topics** sidebar: `related(entity)` list.
4. **Edit a fact** dialog: pencil on a fact chip → `editFact(id, newValue)` →
   then re-call `query()` with the same question to show it changed.
5. **Add knowledge**: a textarea → `submitTip()`; (optional) file upload → `/ingest`.
6. **Footer**: `metrics()` (queries, latency, cost).

---

## 6. Common mistakes (don't do these)

- ❌ Sending `document_id` in `/query`. It does NOT exist anymore — the API
  rejects unknown fields. `/query` body is only `{ question, top_k }`.
- ❌ Drawing the full graph (1245 nodes). Use `/graph?limit=150`.
- ❌ Expecting `/ingest` to be instant. It's slow (AI pass). Use `/tip` for live demos.
- ❌ Forgetting the spinner/timeout on ingest — the request can take >30s.
- ❌ `cost_usd` is tiny (like `0.000013`) — format with enough decimals or show "≈ $0".
- ❌ Hardcoding `localhost:8000` everywhere — use `environment.apiUrl`.

---

## 7. The demo flow to support (so the UI tells a story)

1. Ask a real question → cited answer + an exact **fact** chip.
2. Show the **graph** (entities ↔ specs, linked across docs).
3. Click an entity → **related topics**.
4. **Edit the fact** value → re-ask the same question → answer updates live.
5. **Submit a tip** → ask about it → it's already searchable.

That sequence is the winning demo. Build the UI to make those 5 steps smooth.
