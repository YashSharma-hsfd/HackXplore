import { useState } from 'react'

// Review & Update overlay (design handoff §6).
//
// The design's "Update vector space" maps to the real backend's contribution
// loop: POST /tip re-embeds the correction so it's immediately searchable.
// `onSubmit(text)` should call api.submitTip and resolve when done.
export default function ReviewOverlay({ result, query, onSubmit, onClose }) {
  const [text, setText] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    if (!text.trim()) return
    setBusy(true)
    try {
      // Prefix with the question for context so the correction is self-contained.
      await onSubmit(`Re: ${query}\n\n${text.trim()}`)
      setDone(true)
      setTimeout(onClose, 1900) // auto-close (design handoff §6 success state)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-title">Review &amp; update answer</div>
            <div className="modal-sub">Propose a correction — it’s re-embedded into the vector space.</div>
          </div>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {done ? (
          <div className="review-success">
            <div className="success-circle">✓</div>
            <div className="success-title">Vector space updated</div>
            <div className="success-sub">
              Your correction is indexed and immediately searchable.
              <br />
              Re-ask the question to see it reflected.
            </div>
          </div>
        ) : (
          <div className="modal-cols">
            <div className="modal-pane left">
              <div className="ro-read-label">CURRENT ANSWER</div>
              <div className="ro-read-headline">{query}</div>
              <div className="ro-read-body">{result.answer}</div>
            </div>

            <div className="modal-pane">
              <div className="update-label">YOUR UPDATE</div>
              <p className="update-copy">
                Add a correction, a missing detail, or expert experience. This becomes a new,
                searchable entry in the knowledge base.
              </p>
              <textarea
                className="update-textarea"
                placeholder="e.g. On the F-23, if it bogs at full throttle, lower the needle clip one notch…"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
              <div className="modal-actions">
                <button className="btn-primary" onClick={submit} disabled={busy || !text.trim()}>
                  {busy ? 'Updating…' : 'Update vector space'}
                </button>
                <button className="btn-secondary" onClick={onClose}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
