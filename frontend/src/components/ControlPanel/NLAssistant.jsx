/**
 * NLAssistant.jsx — Natural Language Priority Input
 *
 * User types a sentence like "prioritize water safety over sunlight"
 * → calls POST /assistant → receives weight JSON → auto-updates sliders → re-runs /score
 */

import { useState } from 'react'
import { useAppStore } from '../../store/appStore'
import { postAssistant } from '../../api'
import { FACTOR_META } from '../../store/appStore'

const EXAMPLE_PROMPTS = [
  "Prioritize water ice and radiation safety equally",
  "Solar power is most important, ignore Earth comms",
  "I need flat terrain above all else for construction",
  "Balanced approach, slight preference for water resources",
]

export default function NLAssistant() {
  const {
    assistantText,
    setAssistantText,
    setWeightsFromAssistant,
    runScore,
  } = useAppStore()

  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [result, setResult]       = useState(null)
  const [exampleIdx, setExampleIdx] = useState(0)

  const handleSubmit = async () => {
    if (!assistantText.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await postAssistant(assistantText)
      setWeightsFromAssistant(data.weights)
      setResult(data.weights)
      // Auto-trigger scoring with new weights
      setTimeout(() => runScore(), 200)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleExample = () => {
    const text = EXAMPLE_PROMPTS[exampleIdx % EXAMPLE_PROMPTS.length]
    setAssistantText(text)
    setExampleIdx(i => i + 1)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: 'var(--color-accent)',
          boxShadow: '0 0 8px var(--color-accent)',
          animation: 'dotPulse 2s ease-in-out infinite',
        }} />
        <span style={{ fontSize: 10, color: 'var(--color-accent)', fontWeight: 600, letterSpacing: '0.8px' }}>
          AI ASSISTANT
        </span>
      </div>

      <textarea
        id="nl-assistant-input"
        className="input-field"
        placeholder='e.g. "Prioritize water ice and radiation safety, terrain is secondary"'
        value={assistantText}
        onChange={e => setAssistantText(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={3}
        disabled={loading}
      />

      <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
        <button
          id="nl-assistant-submit"
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={loading || !assistantText.trim()}
          style={{ flex: 1 }}
        >
          {loading ? (
            <><div className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} /> Parsing...</>
          ) : (
            <>✨ Apply</>
          )}
        </button>

        <button
          className="btn btn-ghost"
          onClick={handleExample}
          disabled={loading}
          title="Try an example prompt"
        >
          💡
        </button>
      </div>

      {/* Result: show which weights were set */}
      {result && !error && (
        <div className="assistant-result" style={{ marginTop: 'var(--space-3)' }}>
          <div style={{ fontSize: 10, color: 'var(--color-accent)', fontWeight: 600, marginBottom: 6, letterSpacing: '0.8px' }}>
            ✓ WEIGHTS UPDATED — SLIDERS SYNCED
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {Object.entries(result).map(([factor, val]) => {
              const meta = FACTOR_META[factor]
              const total = Object.values(result).reduce((s, v) => s + v, 0)
              const pct = total > 0 ? Math.round((val / total) * 100) : 0
              return (
                <span key={factor} style={{
                  fontSize: 10,
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--color-bg-base)',
                  border: `1px solid ${meta.color}33`,
                  color: meta.color,
                  fontFamily: 'var(--font-mono)',
                }}>
                  {meta.icon} {meta.label}: {pct}%
                </span>
              )
            })}
          </div>
        </div>
      )}

      {error && (
        <div className="assistant-result error" style={{ marginTop: 'var(--space-3)' }}>
          ⚠️ {error}
        </div>
      )}
    </div>
  )
}
