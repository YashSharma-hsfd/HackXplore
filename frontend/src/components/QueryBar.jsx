import { GlobeIcon } from './icons.jsx'

// Pinned bottom query bar (design handoff §5).
export default function QueryBar({
  value,
  onChange,
  onSubmit,
  onClear,
  webMode,
  onToggleWeb,
  onUpload,
  loading,
  showClear,
}) {
  const submit = (e) => {
    e.preventDefault()
    if (value.trim() && !loading) onSubmit()
  }

  return (
    <div className="query-bar-wrap">
      <form className={`query-bar${webMode ? ' web-on' : ''}`} onSubmit={submit}>
        <button type="button" className="qb-btn" title="Upload documents" onClick={onUpload}>
          +
        </button>

        <button
          type="button"
          className={`qb-web${webMode ? ' on' : ''}`}
          onClick={onToggleWeb}
          title="Toggle live web search (coming soon)"
        >
          <GlobeIcon color={webMode ? '#fff' : '#5a626e'} />
          {webMode ? 'Web · on' : 'Web'}
        </button>

        <input
          className="qb-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={
            webMode
              ? 'Search the live web for two-stroke knowledge…'
              : 'Ask about tuning, jetting, port timing, detonation…'
          }
          autoFocus
        />

        {showClear && (
          <button type="button" className="qb-clear" onClick={onClear}>
            Clear
          </button>
        )}

        <button type="submit" className="qb-submit" disabled={loading || !value.trim()}>
          {loading ? <span className="spinner" /> : '→'}
        </button>
      </form>
    </div>
  )
}
