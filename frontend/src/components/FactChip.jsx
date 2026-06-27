import { useState } from 'react'
import { PencilIcon } from './icons.jsx'

// An editable structured fact (the differentiator — PATCH /fact, CLAUDE.md §5).
// `onSave(id, newValue)` should call the backend and return the updated fact.
export default function FactChip({ fact, onSave }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(fact.value)
  const [saving, setSaving] = useState(false)

  const save = async () => {
    if (!val.trim() || val === fact.value) {
      setEditing(false)
      return
    }
    setSaving(true)
    try {
      await onSave(fact.id, val.trim())
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const unit = fact.unit ? ` ${fact.unit}` : ''

  return (
    <span className={`fact-chip${fact.curated ? ' curated' : ''}`}>
      <span className="fact-attr">{fact.subject || fact.attribute || 'fact'} ·</span>
      {editing ? (
        <span className="fact-edit">
          <input
            value={val}
            autoFocus
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') save()
              if (e.key === 'Escape') {
                setVal(fact.value)
                setEditing(false)
              }
            }}
          />
          <button className="mini-btn primary" onClick={save} disabled={saving}>
            {saving ? '…' : 'Save'}
          </button>
        </span>
      ) : (
        <>
          <span className="fact-val">
            {fact.value}
            {unit}
          </span>
          {fact.curated && <span className="curated-tick" title="Human-curated">✓</span>}
          <button
            className="fact-edit-btn"
            title="Edit this fact"
            onClick={() => {
              setVal(fact.value)
              setEditing(true)
            }}
          >
            <PencilIcon />
          </button>
        </>
      )}
    </span>
  )
}
