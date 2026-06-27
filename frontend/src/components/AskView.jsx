import AnswerPanel from './AnswerPanel.jsx'
import RelatedDomains from './RelatedDomains.jsx'
import AroundTheWeb from './AroundTheWeb.jsx'
import ExploreState from './ExploreState.jsx'

// Ask view body: explore (empty) state OR the two-column answer state
// (design handoff §3 & §4). The query bar itself is rendered by App so it can
// pin to the bottom across both states.
export default function AskView({
  phase,
  query,
  result,
  domain,
  webMode,
  loading,
  relatedEntity,
  related,
  webSignals,
  onPickChip,
  onReview,
  onEditFact,
  onPickRelated,
}) {
  if (phase === 'explore') {
    return <ExploreState onPick={onPickChip} />
  }

  return (
    <div className="answer-layout">
      <div className="answer-col">
        {loading || !result ? (
          <div className="card answer-card">
            <div className="loading-card">
              <div className="skeleton" style={{ height: 14, width: '40%' }} />
              <div className="skeleton" style={{ height: 30, width: '85%' }} />
              <div className="skeleton" style={{ height: 14, width: '100%' }} />
              <div className="skeleton" style={{ height: 14, width: '95%' }} />
              <div className="skeleton" style={{ height: 14, width: '70%' }} />
            </div>
          </div>
        ) : (
          <AnswerPanel
            result={result}
            query={query}
            domain={domain}
            webMode={webMode}
            onReview={onReview}
            onEditFact={onEditFact}
          />
        )}
      </div>

      <div className="side-col">
        <RelatedDomains entity={relatedEntity} items={related} onPick={onPickRelated} />
        <AroundTheWeb signals={webSignals} webMode={webMode} />
      </div>
    </div>
  )
}
