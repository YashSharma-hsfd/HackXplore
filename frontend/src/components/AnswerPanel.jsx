import FactChip from './FactChip.jsx'

function fmtCost(usd) {
  if (usd == null) return '≈ $0'
  if (usd < 0.0001) return '≈ $0'
  return `$${usd.toFixed(usd < 0.01 ? 5 : 4)}`
}

// Returns true when the LLM admitted it couldn't answer.
const NO_INFO_PHRASES = [
  "i don't have enough information",
  "ich habe nicht genügend informationen",
  "not enough information",
  "keine ausreichenden informationen",
]
function isNoInfo(answer) {
  const lower = (answer || '').toLowerCase()
  return NO_INFO_PHRASES.some((p) => lower.includes(p))
}

// Deduplicate citations by source filename — keep the highest-score chunk per source.
function dedupeCitations(citations) {
  const seen = new Map()
  for (const c of citations) {
    const key = c.source || c.chunk_id
    const prev = seen.get(key)
    if (!prev || (c.score || 0) > (prev.score || 0)) {
      seen.set(key, c)
    }
  }
  return Array.from(seen.values())
}

export default function AnswerPanel({ result, query, webMode, onReview, onEditFact }) {
  const { answer, citations = [], facts = [], latency_ms, cost_usd } = result
  const noInfo = isNoInfo(answer)
  const dedupedCitations = dedupeCitations(citations)

  return (
    <div className="card answer-card">
      <div className="answer-header">
        <div className="answer-header-main">
          <div className="asked-label">YOU ASKED</div>
          <div className="query-echo">{query}</div>
          <div className="pill-row">
            <span className="pill">
              <span className="ico-bolt">↯</span>
              {latency_ms != null ? `${(latency_ms / 1000).toFixed(1)}s` : '—'} latency
            </span>
            <span className="pill">
              <span className="ico-cost">$</span>
              {fmtCost(cost_usd)} cost
            </span>
            <span className={`pill mode-badge ${webMode ? 'web' : 'kb'}`}>
              {webMode ? 'Web' : 'Knowledge base'}
            </span>
          </div>
        </div>
        <button className="review-btn" onClick={onReview}>
          ⟳ Review &amp; update
        </button>
      </div>

      <div className="answer-body">
        {webMode && (
          <div className="source-banner web">
            Synthesised from live web signals — verify before relying on it.
          </div>
        )}

        {answer && <div className="answer-prose">{answer}</div>}

        {facts.length > 0 && (
          <>
            <div className="section-label">EXACT SPECS · EDITABLE</div>
            <div className="facts">
              {facts.map((f) => (
                <FactChip key={f.id} fact={f} onSave={onEditFact} />
              ))}
            </div>
          </>
        )}

        {!noInfo && dedupedCitations.length > 0 && (
          <>
            <div className="section-label">SOURCES</div>
            {dedupedCitations.map((c) => (
              <div className="source-row" key={c.chunk_id}>
                <span className="src-badge">
                  {(c.source || '').split('.').pop()?.toUpperCase()?.slice(0, 4) || 'DOC'}
                </span>
                <div className="src-main">
                  <div className="src-name">{c.title || c.source || 'source'}</div>
                  {c.snippet && <div className="src-snippet">{c.snippet}</div>}
                  <div className="src-meta">{c.source}</div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
