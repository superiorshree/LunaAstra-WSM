/**
 * RiskProfile.jsx — Factor risk badges per site
 *
 * Displays LOW/MEDIUM/HIGH risk tags for each factor with color coding.
 * Includes ice detection confidence ring.
 */

function IceConfidenceRing({ pct, color }) {
  const r = 24
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ

  return (
    <div className="ice-conf-ring">
      <svg width="60" height="60" viewBox="0 0 60 60">
        {/* Track */}
        <circle cx="30" cy="30" r={r} fill="none" stroke="var(--color-border)" strokeWidth="4" />
        {/* Fill */}
        <circle
          cx="30" cy="30" r={r}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 800ms ease' }}
        />
      </svg>
      <div className="ice-conf-label">{Math.round(pct)}%</div>
    </div>
  )
}

export default function RiskProfile({ riskProfile, iceConfidence }) {
  if (!riskProfile) return null

  const FACTOR_ICONS = {
    ice: '💧', illumination: '☀️', radiation: '🛡️', slope: '⛰️', comm: '📡',
  }

  return (
    <div>
      <div className="section-label">Risk Assessment</div>

      {/* Risk tags grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 'var(--space-2)',
        marginBottom: 'var(--space-4)',
      }}>
        {Object.entries(riskProfile).map(([factor, info]) => (
          <div key={factor} style={{
            background: 'var(--color-bg-base)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-2) var(--space-3)',
          }}>
            <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', marginBottom: 4 }}>
              {FACTOR_ICONS[factor]} {info.display_name}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'space-between' }}>
              <span className={`risk-tag risk-tag-${info.risk_level}`}>
                {info.emoji} {info.risk_level}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--color-lunar-dim)' }}>
                {(info.normalized_score * 100).toFixed(0)}
              </span>
            </div>
            {info.note && (
              <div style={{ fontSize: 9, color: 'var(--color-warning)', marginTop: 4, lineHeight: 1.4 }}>
                ⚠️ {info.note}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Ice confidence */}
      {iceConfidence && (
        <div style={{
          background: 'var(--color-bg-base)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-3)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
        }}>
          <IceConfidenceRing
            pct={iceConfidence.confidence_pct}
            color={iceConfidence.color}
          />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-lunar)', marginBottom: 2 }}>
              💧 Ice Detection
            </div>
            <div style={{ fontSize: 12, color: iceConfidence.color, fontWeight: 600 }}>
              {iceConfidence.label}
            </div>
            <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', marginTop: 2, lineHeight: 1.5 }}>
              Neutron proxy: {iceConfidence.signals?.neutron_flux_proxy?.toFixed(0)}% ·{' '}
              Shadow: {iceConfidence.signals?.shadow_proxy?.toFixed(0)}%
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
