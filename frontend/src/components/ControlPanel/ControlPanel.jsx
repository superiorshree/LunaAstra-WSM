/**
 * ControlPanel.jsx — Left sidebar with sliders, constraint, NL assistant, score button
 */

import { useAppStore } from '../../store/appStore'
import WeightSliders from './WeightSliders'
import NLAssistant from './NLAssistant'

export default function ControlPanel() {
  const { runScore, isScoring, resetWeights, lastScoredAt, scoringError, backendReady } = useAppStore()

  return (
    <div className="panel panel-control">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon">🎛️</span>
          Mission Parameters
        </div>
        <button
          className="btn btn-ghost"
          onClick={resetWeights}
          disabled={isScoring}
          style={{ fontSize: 11, padding: '4px 10px' }}
          title="Reset to equal weights"
        >
          Reset
        </button>
      </div>

      <div className="panel-body" style={{ gap: 0, padding: 'var(--space-5)' }}>

        {/* NL Assistant */}
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <NLAssistant />
        </div>

        <div className="divider" />

        {/* Weight Sliders */}
        <WeightSliders />

        {/* Score Button */}
        <button
          id="run-score-btn"
          className="btn btn-primary btn-full"
          onClick={runScore}
          disabled={isScoring || !backendReady}
          style={{
            padding: 'var(--space-3)',
            fontSize: 14,
            marginTop: 'var(--space-2)',
            background: isScoring
              ? 'rgba(79,142,255,0.3)'
              : 'linear-gradient(135deg, #4f8eff, #6366f1)',
            boxShadow: isScoring ? 'none' : '0 4px 20px rgba(79,142,255,0.35)',
          }}
        >
          {isScoring ? (
            <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2, borderColor: 'rgba(255,255,255,0.3)', borderTopColor: '#fff' }} />
            Analysing Lunar Surface...</>
          ) : (
            <>🚀 Find Optimal Sites</>
          )}
        </button>

        {/* Error */}
        {scoringError && (
          <div style={{
            marginTop: 'var(--space-3)',
            padding: 'var(--space-3)',
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid rgba(239,68,68,0.25)',
            borderRadius: 'var(--radius-md)',
            fontSize: 12,
            color: 'var(--color-danger)',
          }}>
            ⚠️ {scoringError}
          </div>
        )}

        {/* Last scored timestamp */}
        {lastScoredAt && !isScoring && (
          <div style={{ marginTop: 'var(--space-3)', textAlign: 'center', fontSize: 10, color: 'var(--color-lunar-dim)', fontFamily: 'var(--font-mono)' }}>
            Last scored: {lastScoredAt.toLocaleTimeString()}
          </div>
        )}

        {/* Backend status */}
        {!backendReady && (
          <div style={{
            marginTop: 'var(--space-4)',
            padding: 'var(--space-3)',
            background: 'rgba(245,158,11,0.08)',
            border: '1px solid rgba(245,158,11,0.25)',
            borderRadius: 'var(--radius-md)',
            fontSize: 11,
            color: 'var(--color-warning)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
          }}>
            <div className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5, borderColor: 'rgba(245,158,11,0.3)', borderTopColor: 'var(--color-warning)' }} />
            Connecting to backend...
          </div>
        )}
      </div>
    </div>
  )
}
