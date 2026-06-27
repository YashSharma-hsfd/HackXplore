import { HirthBadge } from './icons.jsx'

// Top bar (design handoff §2). `view` is 'ask' | 'upload'.
export default function TopBar({ view, onView, stats, online }) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="logo">
          <div className="logo-badge">
            <HirthBadge />
          </div>
          <div>
            <div className="logo-wordmark">HIRTH</div>
            <div className="logo-sub">ENGINES</div>
          </div>
        </div>
        <div className="topbar-divider" />
        <div className="topbar-label">KNOWLEDGE ENGINE</div>
      </div>

      <div className="topbar-right">
        <div className="segmented">
          <button className={view === 'ask' ? 'active' : ''} onClick={() => onView('ask')}>
            Ask
          </button>
          <button className={view === 'upload' ? 'active' : ''} onClick={() => onView('upload')}>
            Upload
          </button>
        </div>

        <div className={`vector-status${online ? '' : ' down'}`}>
          <span className="status-dot" />
          {stats ? `${stats.specs} specs · ${stats.nodes} vectors` : online ? 'connected' : 'offline'}
        </div>

        <div className="avatar">HE</div>
      </div>
    </header>
  )
}
