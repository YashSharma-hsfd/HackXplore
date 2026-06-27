import { classifyDomain, domainColor } from '../lib/domains.js'

// "Related domains" card (design handoff §4b) — wired to GET /related.
// `items` is the backend's related[] array; clicking a row re-queries.
export default function RelatedDomains({ entity, items, onPick }) {
  return (
    <div className="card related-card">
      <div className="card-head">
        <span className="card-title">Related domains</span>
      </div>
      <div className="related-list">
        {(!items || items.length === 0) && (
          <div className="empty-state">
            {entity ? `No linked topics for “${entity}” yet.` : 'Ask a question to see related topics.'}
          </div>
        )}
        {items?.map((it) => {
          const color = domainColor(classifyDomain(it.label))
          return (
            <button key={it.id} className="related-row" onClick={() => onPick(it)}>
              <span className="dot" style={{ background: color }} />
              <span className="related-label">{it.label}</span>
              <span className="related-conf">{it.kind || 'topic'}</span>
              <span className="related-arrow">→</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
