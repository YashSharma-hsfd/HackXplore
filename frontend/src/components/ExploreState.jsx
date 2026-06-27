import { TOPIC_CHIPS, domainColor } from '../lib/domains.js'

// Ask view landing / empty state (design handoff §3).
export default function ExploreState({ onPick }) {
  return (
    <div className="explore">
      <div className="eyebrow">HIRTH KNOWLEDGE ENGINE</div>
      <h1 className="hero-headline">
        Ask anything about Hirth <span className="em">two-stroke</span> engines.
      </h1>
      <p className="hero-sub">
        Grounded answers from the internal manuals, spec sheets and forum knowledge — with
        citations, exact specs, and corrections you can push back into the vector space.
      </p>

      <div className="chips">
        {TOPIC_CHIPS.map((c) => (
          <button key={c.label} className="chip" onClick={() => onPick(c.label)}>
            <span className="dot" style={{ background: domainColor(c.domain) }} />
            {c.label}
          </button>
        ))}
      </div>
    </div>
  )
}
