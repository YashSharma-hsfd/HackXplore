// Thin typed-ish client for the real FastAPI backend (see FRONTEND.md §3).
// Every endpoint here exists on the backend. The design-handoff's /api/* names
// are *not* real — they are mapped onto these by the components.

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function req(path, { method = 'GET', body, isForm = false } = {}) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    if (isForm) {
      opts.body = body // FormData — let the browser set the multipart boundary
    } else {
      opts.headers['Content-Type'] = 'application/json'
      opts.body = JSON.stringify(body)
    }
  }
  const res = await fetch(`${API}${path}`, opts)
  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      detail = res.statusText
    }
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  // POST /query — the main one.
  // webSearch=true switches to live Tavily web search (requires TAVILY_API_KEY on the backend).
  // Returns { answer, citations[], facts[], latency_ms, cost_usd }.
  query: (question, topK = 8, webSearch = false) =>
    req('/query', { method: 'POST', body: { question, top_k: topK, web_search: webSearch } }),

  // GET /graph — knowledge graph nodes/edges + stats (used for header counts).
  graph: (limit = 150) => req(`/graph?limit=${limit}`),

  // GET /related — recommendation feature ("Related domains").
  related: (entity, depth = 1) =>
    req(`/related?entity=${encodeURIComponent(entity)}&depth=${depth}`),

  // PATCH /fact — edit a structured value (the differentiator). Returns updated fact.
  editFact: (id, newValue) => req('/fact', { method: 'PATCH', body: { id, new_value: newValue } }),

  // PATCH /chunk/{id} — edit a source chunk's text/metadata.
  editChunk: (chunkId, { newText, newMetadata } = {}) =>
    req(`/chunk/${encodeURIComponent(chunkId)}`, {
      method: 'PATCH',
      body: { new_text: newText, new_metadata: newMetadata },
    }),

  // POST /tip — contribution loop / "Update vector space" correction. Instantly searchable.
  submitTip: (text) => req('/tip', { method: 'POST', body: { text } }),

  // POST /ingest — multipart file upload (SLOW: AI pass per chunk).
  ingest: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return req('/ingest', { method: 'POST', body: fd, isForm: true })
  },

  // POST /ingest-url — ingest a web page by URL (slow-ish).
  ingestUrl: (url) => req('/ingest-url', { method: 'POST', body: { url } }),

  // GET /metrics — live stats (footer / upload dashboard).
  metrics: () => req('/metrics'),

  // GET /corpus/stats — unique document count + total chunks from Chroma.
  corpusStats: () => req('/corpus/stats'),

  // GET /health — uptime check (drives the green "vector status" dot).
  health: () => req('/health'),
}

export { API }
