// "Around the Web" card — renders live web citations returned by the backend
// when web mode is on (POST /query with web_search: true).
// Citations with source_type="web" carry a `url` and `title` field.
export default function AroundTheWeb({ signals, webMode }) {
  const hasSignals = signals && signals.length > 0

  return (
    <div className="card web-card">
      <div className="card-head">
        <span className="card-title">Around the web</span>
        <span className={`head-chip ${webMode && hasSignals ? 'amber' : 'blue'}`}>
          {webMode && hasSignals ? 'LIVE RESULTS' : 'PRIMARY SOURCE'}
        </span>
      </div>
      <div className="web-list">
        {!webMode && (
          <div className="empty-state">
            <span className="tag">WEB SEARCH</span>
            <div>Toggle Web in the query bar to search live web sources.</div>
          </div>
        )}
        {webMode && !hasSignals && (
          <div className="empty-state">
            <span className="tag">WEB SEARCH</span>
            <div>No web results returned. Check that TAVILY_API_KEY is set on the backend.</div>
          </div>
        )}
        {hasSignals &&
          signals.map((s, i) => (
            <div className="web-item" key={s.url || i}>
              <div className="web-item-top">
                <span className="web-tag" style={{ color: '#3358e0' }}>WEB</span>
                <span className="web-src">{s.source}</span>
              </div>
              <div className="web-title">{s.title || s.source}</div>
              {s.snippet && <div className="src-snippet" style={{ marginTop: 5 }}>{s.snippet}</div>}
              <div className="web-bottom">
                <span className="web-rel">{s.score ? `${(s.score * 100).toFixed(0)}% relevance` : ''}</span>
                {s.url && (
                  <a className="open-link" href={s.url} target="_blank" rel="noreferrer">
                    open ↗
                  </a>
                )}
              </div>
            </div>
          ))}
      </div>
    </div>
  )
}
