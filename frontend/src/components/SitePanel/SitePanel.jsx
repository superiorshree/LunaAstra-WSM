/**
 * SitePanel.jsx — Right panel: ranked site list + selected site detail
 *
 * Shows top 5 candidate sites. Clicking a site expands:
 *  - Score + coordinates
 *  - Contribution chart (Recharts)
 *  - Risk profile (LOW/MEDIUM/HIGH badges)
 *  - Ice detection confidence ring
 *  - Mission briefing button (calls /explain/site for Claude narration)
 */

import { useState } from 'react'
import { useAppStore } from '../../store/appStore'
import ContributionChart from './ContributionChart'
import RiskProfile from './RiskProfile'
import { postExplainSite } from '../../api'

function ScoreBar({ value }) {
  const color = value >= 0.7 ? 'var(--risk-low)' : value >= 0.4 ? 'var(--risk-medium)' : 'var(--risk-high)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        flex: 1, height: 4, background: 'var(--color-border)',
        borderRadius: 'var(--radius-full)', overflow: 'hidden',
      }}>
        <div style={{
          width: `${value * 100}%`, height: '100%',
          background: color, borderRadius: 'var(--radius-full)',
          transition: 'width 600ms ease',
        }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color, fontWeight: 700, minWidth: 42 }}>
        {(value * 100).toFixed(1)}
      </span>
    </div>
  )
}

function SiteCard({ site, isSelected, onSelect }) {
  const [briefing, setBriefing]   = useState(null)
  const [briefingLoading, setBriefingLoading] = useState(false)

  const handleBriefing = async (e) => {
    e.stopPropagation()
    if (briefing) { setBriefing(null); return }
    setBriefingLoading(true)
    try {
      const data = await postExplainSite(site.site_id, true)
      setBriefing(data.mission_briefing)
    } catch {
      setBriefing('Mission briefing unavailable (Claude API offline).')
    } finally {
      setBriefingLoading(false)
    }
  }

  return (
    <div
      className={`site-card ${isSelected ? 'active' : ''}`}
      onClick={() => onSelect(site)}
      id={`site-card-${site.site_id}`}
    >
      <div className="site-rank">#{site.rank}</div>

      <div className="site-id">⬡ {site.site_id}</div>
      <div className="site-coords">
        {site.lat.toFixed(3)}°, {site.lon.toFixed(3)}°
      </div>

      <div style={{ marginBottom: 'var(--space-3)' }}>
        <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', marginBottom: 4 }}>Suitability Score</div>
        <ScoreBar value={site.total_score} />
      </div>

      {/* Expanded detail when selected */}
      {isSelected && (
        <div style={{ marginTop: 'var(--space-4)', borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-4)' }}>

          {/* Risk Profile */}
          {site.risk_profile && (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <RiskProfile
                riskProfile={site.risk_profile}
                iceConfidence={site.ice_confidence}
              />
            </div>
          )}

          {/* Contribution Chart */}
          {site.contributions && (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <ContributionChart contributions={site.contributions} />
            </div>
          )}

          {/* Raw values detail */}
          {site.raw_values && (
            <div>
              <div className="section-label">Raw Sensor Values</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)' }}>
                {Object.entries(site.raw_values).map(([k, v]) => (
                  <div key={k} style={{
                    background: 'var(--color-bg-base)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '6px 10px',
                    border: '1px solid var(--color-border)',
                  }}>
                    <div style={{ fontSize: 9, color: 'rgba(200,216,240,0.4)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>{k}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--color-lunar)', marginTop: 2 }}>
                      {v.toFixed(3)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Mission Briefing & Dossier Actions */}
          <div style={{ marginTop: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <button
              className="btn btn-ghost btn-full"
              onClick={handleBriefing}
              disabled={briefingLoading}
              id={`briefing-btn-${site.site_id}`}
              style={{ fontSize: 12 }}
            >
              {briefingLoading
                ? <><div className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} /> Generating briefing...</>
                : briefing ? '▲ Hide Mission Briefing' : '🤖 Generate Mission Briefing'
              }
            </button>

            <button
              className="btn btn-primary btn-full"
              onClick={(e) => {
                e.stopPropagation()
                onOpenReport(site.site_id)
              }}
              style={{ fontSize: 12, background: 'rgba(79,142,255,0.15)', borderColor: 'var(--color-accent)', color: 'var(--color-accent)' }}
            >
              📄 Full Mission Dossier & Export
            </button>

            {briefing && (
              <div className="briefing-card" style={{ marginTop: 'var(--space-2)' }}>
                <div className="briefing-header">
                  🤖 AI Mission Briefing
                </div>
                <div className="briefing-text">{briefing}</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function SitePanel({ onOpenReport }) {
  const { scoreResult, selectedSite, setSelectedSite, isScoring } = useAppStore()

  const sites = scoreResult?.top_sites ?? []

  return (
    <div className="panel panel-sites">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-title-icon">🏆</span>
          Top Candidate Sites
        </div>
        {sites.length > 0 && (
          <span style={{ fontSize: 10, color: 'var(--color-lunar-dim)', fontFamily: 'var(--font-mono)' }}>
            {sites.length} sites
          </span>
        )}
      </div>

      <div className="panel-body">
        {isScoring && (
          <div className="empty-state">
            <div className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
            <div className="empty-state-title">Ranking sites...</div>
          </div>
        )}

        {!isScoring && sites.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">🏔️</div>
            <div className="empty-state-title">No Sites Ranked Yet</div>
            <div className="empty-state-desc">Run the analysis to see candidate habitat locations</div>
          </div>
        )}

        {!isScoring && sites.map(site => (
          <SiteCard
            key={site.site_id}
            site={site}
            isSelected={selectedSite?.site_id === site.site_id}
            onSelect={setSelectedSite}
            onOpenReport={onOpenReport}
          />
        ))}

        {/* Score metadata */}
        {scoreResult && !isScoring && (
          <div style={{
            marginTop: 'var(--space-4)',
            padding: 'var(--space-3)',
            background: 'var(--color-bg-base)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border)',
            fontSize: 10,
            color: 'var(--color-lunar-dim)',
            fontFamily: 'var(--font-mono)',
          }}>
            <div>Mode: {scoreResult.space_weather_alert}</div>
            {scoreResult.radiation_penalty_applied > 0 && (
              <div style={{ color: 'var(--color-warning)', marginTop: 2 }}>
                Radiation penalty: -{(scoreResult.radiation_penalty_applied * 100).toFixed(0)}%
              </div>
            )}
            <div style={{ marginTop: 2 }}>Slope constraint: &lt;{scoreResult.max_slope_constraint}°</div>
          </div>
        )}
      </div>
    </div>
  )
}
