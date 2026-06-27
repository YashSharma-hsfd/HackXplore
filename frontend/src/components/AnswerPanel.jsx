import FactChip from './FactChip.jsx'
import { domainColor, domainLabel } from '../lib/domains.js'

// Derives a short headline from the answer text: first sentence, capped.
function headlineOf(answer) {
  if (!answer) return ''
  const first = answer.split(/(?<=[.?!])\s/)[0] || answer
  return first.length > 120 ? first.slice(0, 117).trimEnd() + '…' : first
}

function fmtCost(usd) {
  if (usd == null) return '≈ $0'
  if (usd < 0.0001) return '≈ $0'
  return `$${usd.toFixed(usd < 0.01 ? 5 : 4)}`
}

export default function AnswerPanel({ result, query, domain, webMode, onReview, onEditFact }) {
  const { answer, citations = [], facts = [], latency_ms, cost_usd } = result
  const headline = headlineOf(answer)
  const body = answer.length > headline.length ? answer.slice(headline.length).trim() : ''
  const color = domainColor(domain)

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
        <div className="answer-meta">
          <span className="domain-tag" style={{ color }}>
            <span className="dot" style={{ background: color }} />
            {domainLabel(domain)}
          </span>
          <span className="updated-date">updated {new Date().toLocaleDateString()}</span>
        </div>

        <h2 className="answer-headline">{headline}</h2>

        <div className={`source-banner ${webMode ? 'web' : 'kb'}`}>
          {webMode
            ? 'Synthesised from live web signals — verify before relying on it.'
            : `Grounded in ${citations.length} internal source${citations.length === 1 ? '' : 's'} from the knowledge base.`}
        </div>

        {body && <div className="answer-prose">{body}</div>}

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

        <div className="section-label">SOURCES</div>
        {citations.length === 0 && <div className="src-meta">No sources cited.</div>}
        {citations.map((c) => (
          <div className="source-row" key={c.chunk_id}>
            <span className="src-badge">{(c.source || '').split('.').pop()?.toUpperCase()?.slice(0, 4) || 'DOC'}</span>
            <div className="src-main">
              <div className="src-name">{c.title || c.source || 'source'}</div>
              {c.snippet && <div className="src-snippet">{c.snippet}</div>}
              <div className="src-meta">{c.source}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
