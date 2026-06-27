import { useRef, useState } from 'react'
import { api } from '../lib/api.js'
import { UploadCloud } from './icons.jsx'

const fmtSize = (n) => (n > 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)
const ext = (name) => (name.split('.').pop() || '').toUpperCase().slice(0, 4)

// Upload view (design handoff §7).
//
// Real backend has POST /ingest (multipart) + GET /metrics + GET /graph(stats),
// but NO /documents list endpoint, so the document list is session-local: it
// tracks files uploaded in this session and their status.
export default function UploadView({ metrics, graphStats, corpusStats, onToast, onIngested }) {
  const [docs, setDocs] = useState([])
  const [drag, setDrag] = useState(false)
  const inputRef = useRef(null)

  const upload = async (fileList) => {
    const files = Array.from(fileList)
    for (const file of files) {
      const id = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
      setDocs((d) => [{ id, name: file.name, size: file.size, status: 'embedding' }, ...d])
      try {
        // /ingest is SLOW (AI pass per chunk) — no timeout, just await.
        const res = await api.ingest(file)
        setDocs((d) =>
          d.map((x) => (x.id === id ? { ...x, status: 'indexed', chunks: res.n_chunks } : x)),
        )
        onToast?.(`Indexed “${file.name}” (${res.n_chunks} chunks)`)
        onIngested?.()
      } catch (e) {
        setDocs((d) => d.map((x) => (x.id === id ? { ...x, status: 'error', error: e.message } : x)))
        onToast?.(`Failed: ${e.message}`)
      }
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDrag(false)
    if (e.dataTransfer.files?.length) upload(e.dataTransfer.files)
  }

  const indexedCount = docs.filter((d) => d.status === 'indexed').length

  return (
    <div className="upload-view">
      <div className="upload-inner">
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-label">Documents</div>
            <div className="stat-value">{corpusStats ? corpusStats.document_count : '—'}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Chunks indexed</div>
            <div className="stat-value blue">{corpusStats ? corpusStats.chunk_count : '—'}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Uploaded this session</div>
            <div className="stat-value teal">{indexedCount}</div>
          </div>
        </div>

        <div
          className={`dropzone${drag ? ' drag' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setDrag(true)
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
        >
          <div className="drop-icon">
            <UploadCloud />
          </div>
          <div className="drop-title">Drop files here or click to browse</div>
          <div className="drop-accept">PDF · DOCX · XLSX · TXT</div>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.xlsx,.txt,.html"
            style={{ display: 'none' }}
            onChange={(e) => e.target.files?.length && upload(e.target.files)}
          />
        </div>

        {metrics && (
          <div className="src-meta" style={{ marginTop: 14 }}>
            {metrics.n_queries} queries · cache hit rate {(metrics.cache_hit_rate * 100).toFixed(0)}% ·
            p50 {Math.round(metrics.p50_latency_ms)}ms · today ${metrics.total_cost_usd_today.toFixed(4)}
          </div>
        )}

        <div className="doc-list">
          {docs.length === 0 && (
            <div className="empty-state">
              Uploads from this session appear here. Big PDFs run an AI pass per chunk and can take
              minutes — for a quick live demo, use “Submit a tip” via Review &amp; update instead.
            </div>
          )}
          {docs.map((d) => (
            <div className="doc-row" key={d.id}>
              <div className="doc-badge">{ext(d.name)}</div>
              <div className="doc-main">
                <div className="doc-name">{d.name}</div>
                <div className="doc-meta">
                  {fmtSize(d.size)}
                  {d.chunks != null ? ` · ${d.chunks} chunks` : ''}
                  {d.error ? ` · ${d.error}` : ''}
                </div>
                <div className="doc-progress">
                  <div
                    className={`doc-progress-fill ${d.status === 'indexed' ? 'indexed' : 'embedding'}`}
                    style={{ width: d.status === 'indexed' ? '100%' : d.status === 'error' ? '100%' : '60%' }}
                  />
                </div>
              </div>
              <span className={`doc-status ${d.status}`}>
                {d.status === 'indexed' ? 'INDEXED' : d.status === 'error' ? 'ERROR' : 'EMBEDDING'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
