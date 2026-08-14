/**
 * SiteReportModal.jsx — Exportable Mission Dossier & Full Site Report Modal
 *
 * Provides a comprehensive, exportable dossier for a candidate habitat site:
 *  - Official Mission Metadata
 *  - AI Executive Briefing
 *  - Risk Matrix
 *  - Contribution Scorecard
 *  - Raw Sensor Telemetry
 *  - Export / Print capabilities
 */

import { useState, useEffect } from 'react'
import { FACTOR_META } from '../../store/appStore'

const BASE_URL = 'http://localhost:8000'

export default function SiteReportModal({ isOpen, onClose, siteId }) {
  if (!isOpen || !siteId) return null

  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let isMounted = true
    setLoading(true)
    setError(null)

    fetch(`${BASE_URL}/explain/report/${siteId}`)
      .then(res => {
        if (!res.ok) throw new Error(`Failed to load report: ${res.statusText}`)
        return res.json()
      })
      .then(data => {
        if (isMounted) {
          setReport(data)
          setLoading(false)
        }
      })
      .catch(err => {
        if (isMounted) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => { isMounted = false }
  }, [siteId])

  const handleDownloadJSON = () => {
    if (!report) return
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(report, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute("href", dataStr)
    downloadAnchor.setAttribute("download", `LunaAstra_Site_Report_${siteId}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  const handlePrint = () => {
    window.print()
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(6, 11, 24, 0.88)',
      backdropFilter: 'blur(10px)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'var(--space-6)',
    }}>
      <div style={{
        background: 'var(--color-bg-panel)',
        border: '1px solid var(--color-border-bright)',
        borderRadius: 'var(--radius-xl)',
        width: '100%',
        maxWidth: 880,
        maxHeight: '92vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 70px rgba(0,0,0,0.85), var(--shadow-glow)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: 'var(--space-4) var(--space-6)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(79, 142, 255, 0.05)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: 'var(--color-accent)',
              boxShadow: '0 0 10px var(--color-accent)',
            }} />
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 16, fontWeight: 700, color: 'var(--color-lunar)' }}>
                MISSION DOSSIER: {siteId}
              </div>
              <div style={{ fontSize: 11, color: 'var(--color-lunar-dim)' }}>
                NASA/ISRO Multi-Sensor Geospatial Assessment · Problem SW02
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <button
              onClick={handleDownloadJSON}
              disabled={!report}
              className="btn btn-ghost"
              style={{ fontSize: 12, padding: '6px 12px' }}
            >
              📥 Download JSON
            </button>
            <button
              onClick={handlePrint}
              disabled={!report}
              className="btn btn-primary"
              style={{ fontSize: 12, padding: '6px 12px' }}
            >
              🖨️ Print / PDF
            </button>
            <button
              onClick={onClose}
              className="btn btn-ghost"
              style={{ padding: '6px 12px', fontSize: 16 }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: 'var(--space-6)', overflowY: 'auto', flex: 1 }}>
          {loading && (
            <div className="empty-state" style={{ padding: 'var(--space-12)' }}>
              <div className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
              <div className="empty-state-title" style={{ marginTop: 'var(--space-4)' }}>
                Assembling Dossier for {siteId}...
              </div>
            </div>
          )}

          {error && (
            <div style={{ padding: 'var(--space-4)', background: 'rgba(239,68,68,0.1)', border: '1px solid var(--color-danger)', borderRadius: 'var(--radius-md)', color: 'var(--color-danger)' }}>
              ⚠️ {error}
            </div>
          )}

          {report && !loading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              
              {/* Top Banner: Rank + Coordinates + Percentile */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 'var(--space-3)',
                background: 'var(--color-bg-base)',
                padding: 'var(--space-4)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border)',
              }}>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', textTransform: 'uppercase' }}>Candidate Rank</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-accent)', fontFamily: 'var(--font-display)' }}>
                    #{report.rank}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', textTransform: 'uppercase' }}>Suitability Score</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--risk-low)', fontFamily: 'var(--font-mono)' }}>
                    {(report.total_score * 100).toFixed(1)} <span style={{ fontSize: 12, color: 'var(--color-lunar-dim)' }}>/100</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', textTransform: 'uppercase' }}>Coordinates</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-lunar)', fontFamily: 'var(--font-mono)', marginTop: 4 }}>
                    {report.lat.toFixed(3)}° S, {report.lon.toFixed(3)}° E
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', textTransform: 'uppercase' }}>Global Percentile</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-accent)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                    Top {(100 - report.score_percentile).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* AI Mission Briefing */}
              {report.mission_briefing && (
                <div className="briefing-card" style={{ margin: 0 }}>
                  <div className="briefing-header">
                    🤖 AI Mission Planning Executive Summary
                  </div>
                  <div className="briefing-text" style={{ fontSize: 13, lineHeight: 1.8 }}>
                    {report.mission_briefing}
                  </div>
                </div>
              )}

              {/* Risk Profile Breakdown */}
              {report.risk_profile && (
                <div className="card" style={{ margin: 0 }}>
                  <div className="section-label" style={{ marginBottom: 'var(--space-3)' }}>
                    Environmental Risk Profile & Thresholds
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--space-2)' }}>
                    {Object.entries(report.risk_profile).map(([k, v]) => (
                      <div key={k} style={{
                        background: 'var(--color-bg-base)',
                        padding: 'var(--space-3)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--color-border)',
                        textAlign: 'center',
                      }}>
                        <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', marginBottom: 4 }}>
                          {FACTOR_META[k]?.icon} {v.display_name}
                        </div>
                        <div style={{ marginBottom: 4 }}>
                          <span className={`risk-tag risk-tag-${v.risk_level}`}>
                            {v.emoji} {v.risk_level}
                          </span>
                        </div>
                        <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--color-lunar-dim)' }}>
                          Raw: {v.raw_value.toFixed(2)} {v.unit}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Water Ice Confidence & Detection Details */}
              {report.ice_confidence && (
                <div className="card" style={{ margin: 0 }}>
                  <div className="section-label" style={{ marginBottom: 'var(--space-3)' }}>
                    Water Ice Detection & Resource Confidence
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)' }}>
                    <div style={{
                      fontFamily: 'var(--font-display)',
                      fontSize: 32,
                      fontWeight: 700,
                      color: report.ice_confidence.color,
                      minWidth: 90,
                    }}>
                      {report.ice_confidence.confidence_pct}%
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: report.ice_confidence.color }}>
                        {report.ice_confidence.label}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--color-lunar-dim)', marginTop: 2 }}>
                        {report.ice_confidence.note}
                      </div>
                      <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-2)', fontSize: 10, fontFamily: 'var(--font-mono)', color: 'rgba(200,216,240,0.5)' }}>
                        <span>LEND Neutron Flux Proxy: {report.ice_confidence.signals?.neutron_flux_proxy}%</span>
                        <span>Diviner PSR Shadow Proxy: {report.ice_confidence.signals?.shadow_proxy}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Multi-Criteria Contribution Breakdown */}
              {report.contributions && (
                <div className="card" style={{ margin: 0 }}>
                  <div className="section-label" style={{ marginBottom: 'var(--space-3)' }}>
                    Deterministic Factor Contribution Breakdown
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {report.contributions.map(item => (
                      <div key={item.factor} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: 'var(--color-bg-base)',
                        padding: '8px 12px',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: 12,
                      }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          {FACTOR_META[item.factor]?.icon} {item.display_name}
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', fontFamily: 'var(--font-mono)' }}>
                          <span style={{ color: 'var(--color-lunar-dim)', fontSize: 11 }}>
                            Weight: {(item.weight * 100).toFixed(0)}% × Score: {(item.normalized_score * 100).toFixed(0)}%
                          </span>
                          <span style={{ color: 'var(--color-accent)', fontWeight: 700 }}>
                            +{item.contribution.toFixed(4)} ({item.percentage.toFixed(1)}%)
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Space Weather Alert context */}
              <div style={{
                fontSize: 11,
                color: 'rgba(200,216,240,0.4)',
                fontFamily: 'var(--font-mono)',
                display: 'flex',
                justifyContent: 'space-between',
                padding: '0 var(--space-2)',
              }}>
                <span>Live Space Weather State: {report.space_weather_at_time}</span>
                <span>Report Generated: {new Date(report.generated_at).toLocaleString()}</span>
              </div>

            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: 'var(--space-3) var(--space-6)',
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'flex-between',
          alignItems: 'center',
          background: 'rgba(13, 21, 38, 0.95)',
        }}>
          <span style={{ fontSize: 11, color: 'var(--color-lunar-dim)' }}>
            LunaAstra Decision Support System · SW02
          </span>
          <button onClick={onClose} className="btn btn-ghost">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
