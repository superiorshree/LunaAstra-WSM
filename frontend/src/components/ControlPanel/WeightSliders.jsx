/**
 * WeightSliders.jsx — 5-Factor Priority Sliders + Max Slope Constraint
 *
 * Displays sliders for each factor. Values are auto-normalized to sum 1.0
 * on the backend, so users see relative priorities intuitively (0–100).
 */

import { useAppStore, FACTOR_META } from '../../store/appStore'

const FACTOR_KEYS = ['ice', 'illumination', 'radiation', 'slope', 'comm']

export default function WeightSliders() {
  const { weights, maxSlopeDeg, setWeight, setMaxSlope, isScoring } = useAppStore()

  const total = Object.values(weights).reduce((s, v) => s + v, 0)

  return (
    <div>
      {/* Weights */}
      <div className="section-label" style={{ marginBottom: 'var(--space-4)' }}>
        Factor Priorities
      </div>

      {FACTOR_KEYS.map(factor => {
        const meta = FACTOR_META[factor]
        const pct = total > 0 ? Math.round((weights[factor] / total) * 100) : 0

        return (
          <div key={factor} className="slider-group">
            <div className="slider-header">
              <span className="slider-label">
                <span>{meta.icon}</span>
                <span>{meta.label}</span>
              </span>
              <span className="slider-value">{pct}%</span>
            </div>

            {/* Custom colored slider track */}
            <div style={{ position: 'relative' }}>
              <input
                id={`slider-${factor}`}
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={weights[factor]}
                disabled={isScoring}
                onChange={e => setWeight(factor, e.target.value)}
                style={{
                  background: `linear-gradient(to right, ${meta.color} 0%, ${meta.color} ${weights[factor] * 100}%, var(--color-border) ${weights[factor] * 100}%, var(--color-border) 100%)`,
                  accentColor: meta.color,
                }}
              />
            </div>

            {/* Contribution display */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 2 }}>
              <span style={{ fontSize: 10, color: 'var(--color-lunar-dim)', fontFamily: 'var(--font-mono)' }}>
                weight: {weights[factor].toFixed(2)}
              </span>
            </div>
          </div>
        )
      })}

      {/* Normalized sum indicator */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--space-2) var(--space-3)',
        background: 'var(--color-bg-base)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border)',
        marginBottom: 'var(--space-4)',
      }}>
        <span style={{ fontSize: 10, color: 'var(--color-lunar-dim)' }}>
          Auto-normalized to 100%
        </span>
        <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-accent)' }}>
          {Math.round(total * 100)}% raw → normalized
        </span>
      </div>

      {/* Hard Constraint */}
      <div className="section-label">Hard Constraint</div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
        <span style={{ fontSize: 12, color: 'var(--color-lunar-dim)', flex: 1 }}>
          ⛰️ Max slope (exclude steeper terrain)
        </span>
        <input
          id="max-slope-input"
          type="number"
          className="input-number"
          min="0"
          max="90"
          step="0.5"
          value={maxSlopeDeg}
          disabled={isScoring}
          onChange={e => setMaxSlope(e.target.value)}
        />
        <span style={{ fontSize: 11, color: 'var(--color-lunar-dim)', fontFamily: 'var(--font-mono)' }}>°</span>
      </div>

      <div style={{ fontSize: 10, color: 'rgba(200,216,240,0.3)', marginBottom: 'var(--space-4)' }}>
        Pixels with slope &gt; {maxSlopeDeg}° are excluded regardless of score
      </div>
    </div>
  )
}
