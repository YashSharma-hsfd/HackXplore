import { useCallback, useEffect, useState } from 'react'
import { api } from './lib/api.js'
import { classifyDomain } from './lib/domains.js'
import TopBar from './components/TopBar.jsx'
import AskView from './components/AskView.jsx'
import UploadView from './components/UploadView.jsx'
import QueryBar from './components/QueryBar.jsx'
import ReviewOverlay from './components/ReviewOverlay.jsx'
import Toast from './components/Toast.jsx'

// Pick the best "entity" to ask /related about: a curated spec subject, else the
// first citation's source, else the raw query.
function primaryEntity(result, query) {
  if (result?.facts?.length) return result.facts[0].subject || query
  if (result?.citations?.length) return result.citations[0].title || result.citations[0].source || query
  return query
}

export default function App() {
  // ── top-level UI state (mirrors design handoff §State Management) ───────────
  const [view, setView] = useState('ask') // 'ask' | 'upload'
  const [phase, setPhase] = useState('explore') // 'explore' | 'answer'
  const [query, setQuery] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [result, setResult] = useState(null)
  const [domain, setDomain] = useState('combustion')
  const [webMode, setWebMode] = useState(false)
  const [loading, setLoading] = useState(false)

  const [related, setRelated] = useState([])
  const [relatedEntity, setRelatedEntity] = useState('')
  const [webSignals, setWebSignals] = useState([])

  const [reviewOpen, setReviewOpen] = useState(false)
  const [toast, setToast] = useState(null)

  // ── connection / corpus stats for the header & upload view ──────────────────
  const [online, setOnline] = useState(false)
  const [graphStats, setGraphStats] = useState(null)
  const [corpusStats, setCorpusStats] = useState(null)
  const [metrics, setMetrics] = useState(null)

  const refreshStats = useCallback(async () => {
    try {
      const g = await api.graph(150)
      setGraphStats(g.stats)
    } catch {
      /* graph optional */
    }
    try {
      setCorpusStats(await api.corpusStats())
    } catch {
      /* corpus stats optional */
    }
    try {
      setMetrics(await api.metrics())
    } catch {
      /* metrics optional */
    }
  }, [])

  useEffect(() => {
    api
      .health()
      .then(() => setOnline(true))
      .catch(() => setOnline(false))
    refreshStats()
  }, [refreshStats])

  // ── core query flow ─────────────────────────────────────────────────────────
  const runQuery = useCallback(
    async (question) => {
      const q = question.trim()
      if (!q) return
      setSubmittedQuery(q)
      setPhase('answer')
      setLoading(true)
      setResult(null)
      setRelated([])
      setWebSignals([])
      setDomain(classifyDomain(q))

      try {
        const res = await api.query(q, 8, webMode)
        setResult(res)
        setDomain(classifyDomain(`${q} ${res.answer}`))

        // In web mode, web citations come back in res.citations with source_type="web"
        // and a url field — AroundTheWeb reads them directly from result.citations.
        const webCitations = webMode
          ? (res.citations || []).filter((c) => c.source_type === 'web')
          : []
        setWebSignals(webCitations)

        // recommendation feature → GET /related on the primary entity (corpus mode only)
        if (!webMode) {
          const entity = primaryEntity(res, q)
          setRelatedEntity(entity)
          api
            .related(entity)
            .then((r) => setRelated(r.related || []))
            .catch(() => setRelated([]))
        } else {
          setRelated([])
          setRelatedEntity('')
        }

        refreshStats()
      } catch (e) {
        setToast(`Query failed: ${e.message}`)
        setResult({ answer: `Couldn't reach the knowledge base.\n\n${e.message}`, citations: [], facts: [] })
      } finally {
        setLoading(false)
      }
    },
    [webMode, refreshStats],
  )

  const onSubmit = () => runQuery(query)

  const onPickChip = (label) => {
    setQuery(label)
    runQuery(label)
  }

  const onPickRelated = (item) => {
    const text = item.value ? `${item.label}` : item.label
    setQuery(text)
    runQuery(text)
  }

  const onClear = () => {
    setPhase('explore')
    setQuery('')
    setSubmittedQuery('')
    setResult(null)
    setRelated([])
  }

  // ── edit a structured fact → PATCH /fact, then patch local state ────────────
  const onEditFact = async (id, newValue) => {
    try {
      const updated = await api.editFact(id, newValue)
      setResult((r) =>
        r ? { ...r, facts: r.facts.map((f) => (f.id === id ? { ...f, ...updated } : f)) } : r,
      )
      setToast('Fact updated — re-ask to see it reflected in the answer.')
    } catch (e) {
      setToast(`Edit failed: ${e.message}`)
      throw e
    }
  }

  // ── review overlay → POST /tip (contribution / re-embed loop) ───────────────
  const onSubmitTip = async (text) => {
    await api.submitTip(text)
    refreshStats()
  }

  return (
    <div className="app-shell">
      <TopBar view={view} onView={setView} stats={graphStats} online={online} />

      <div className="app-body">
        {view === 'ask' ? (
          <>
            <AskView
              phase={phase}
              query={submittedQuery}
              result={result}
              domain={domain}
              webMode={webMode}
              loading={loading}
              relatedEntity={relatedEntity}
              related={related}
              webSignals={webSignals}
              onPickChip={onPickChip}
              onReview={() => setReviewOpen(true)}
              onEditFact={onEditFact}
              onPickRelated={onPickRelated}
            />
            <QueryBar
              value={query}
              onChange={setQuery}
              onSubmit={onSubmit}
              onClear={onClear}
              webMode={webMode}
              onToggleWeb={() => setWebMode((w) => !w)}
              loading={loading}
              showClear={phase === 'answer'}
            />
          </>
        ) : (
          <UploadView
            metrics={metrics}
            graphStats={graphStats}
            corpusStats={corpusStats}
            onToast={setToast}
            onIngested={refreshStats}
          />
        )}
      </div>

      {reviewOpen && result && (
        <ReviewOverlay
          result={result}
          query={submittedQuery}
          onSubmit={onSubmitTip}
          onClose={() => setReviewOpen(false)}
        />
      )}

      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  )
}
