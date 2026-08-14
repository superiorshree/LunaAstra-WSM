/**
 * ScenarioModal.jsx — What-If Scenario Comparison Modal
 *
 * Compares two different weight configurations side-by-side.
 * Calls POST /explain/compare and displays:
 *  - Claude-generated operational narration
 *  - Top site shift & score delta
 *  - Weight diff breakdown
 *  - Factor tradeoff insights
 */

import { useState } from 'react'
import { postExplainCompare } from '../../api'
import { FACTOR_META } from '../../store/appStore'

const PRESET_SCENARIOS = {
  water_focus: {
    label: 'Water Extraction (ISRU)',
    weights: { ice: 0.50, illumination: 0.15, radiation: 0.15, slope: 0.10, comm: 0.10 },
    max_slope_deg: 15,
  },
  solar_focus: {
    label: 'Continuous Solar Power',
    weights: { ice: 0.10, illumination: 0.55, radiation: 0.15, slope: 0.10, comm: 0.10 },
    max_slope_deg: 15,
  },
  safety_first: {
    label: 'Maximum Radiation Safety',
    weights: { ice: 0.15, illumination: 0.15, radiation: 0.50, slope: 0.10, comm: 0.10 },
    max_slope_deg: 12,
  },
  construction: {
    label: 'Flat Terrain Construction',
    weights: { ice: 0.15, illumination: 0.15, radiation: 0.15, slope: 0.45, comm: 0.10 },
    max_slope_deg: 8,
  },
  balanced: {
    label: 'Balanced Exploration',
    weights: { ice: 0.20, illumination: 0.20, radiation: 0.20, slope: 0.20, comm: 0.20 },
    max_slope_deg: 15,
  }
}

export default function ScenarioModal({ isOpen, onClose, currentWeights, currentMaxSlope }) {
  if (!isOpen) return null

  const [presetA, setPresetA] = useState('water_focus')
  const [presetB, setPresetB] = useState('solar_focus')
  const [customA, setCustomA] = useState(false)
  const [customB, setCustomB] = useState(false)

  const [scenarioA, setScenarioA] = useState({
    label: 'Scenario A (Current Setup)',
    weights: { ...currentWeights },
    max_slope_deg: currentMaxSlope,
  })

  const [scenarioB, setScenarioB] = useState(PRESET_SCENARIOS.solar_focus)

  const [loading, setLoading] = useState(false)
  const [compareResult, setCompareResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSelectPresetA = (key) => {
    setPresetA(key)
    if (key === 'current') {
      setScenarioA({
        label: 'Current Setup',
        weights: { ...currentWeights },
        max_slope_deg: currentMaxSlope,
      })
    } else {
      setScenarioA(PRESET_SCENARIOS[key])
    }
  }

  const handleSelectPresetB = (key) => {
    setPresetB(key)
    setScenarioB(PRESET_SCENARIOS[key])
  }

  const handleRunCompare = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await postExplainCompare(scenarioA, scenarioB)
      setCompareResult(data)
    } catch (err) {
      setError(err.message || 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(6, 11, 24, 0.85)',
      backdropFilter: 'blur(8px)',
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
        maxWidth: 960,
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0,0,0,0.8), var(--shadow-glow)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: 'var(--space-5) var(--space-6)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(79, 142, 255, 0.04)',
        }}>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700, color: 'var(--color-lunar)' }}>
              ⚖️ What-If Scenario Comparison
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-lunar-dim)', marginTop: 2 }}>
              Compare two mission priority profiles and analyze trade-offs with AI narration
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost"
            style={{ padding: '6px 12px', fontSize: 16 }}
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: 'var(--space-6)', overflowY: 'auto', flex: 1 }}>
          
          {/* Preset Selectors */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)', marginBottom: 'var(--space-6)' }}>
            
            {/* Scenario A */}
            <div className="card" style={{ margin: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-accent)', marginBottom: 'var(--space-3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>🔵 SCENARIO A</span>
                <select
                  value={presetA}
                  onChange={(e) => handleSelectPresetA(e.target.value)}
                  style={{
                    background: 'var(--color-bg-base)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-lunar)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '3px 8px',
                    fontSize: 11,
                  }}
                >
                  <option value="current">Current Parameters</option>
                  <option value="water_focus">Water Extraction (ISRU)</option>
                  <option value="solar_focus">Continuous Solar Power</option>
                  <option value="safety_first">Maximum Radiation Safety</option>
                  <option value="construction">Flat Terrain Construction</option>
                  <option value="balanced">Balanced Exploration</option>
                </select>
              </div>

              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-lunar)', marginBottom: 'var(--space-3)' }}>
                {scenarioA.label}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                {Object.entries(scenarioA.weights).map(([k, v]) => (
                  <div key={k} style={{ fontSize: 11, display: 'flex', justifyContent: 'space-between', padding: '4px 8px', background: 'var(--color-bg-base)', borderRadius: 4 }}>
                    <span style={{ color: 'var(--color-lunar-dim)' }}>{FACTOR_META[k]?.icon} {FACTOR_META[k]?.label}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{(v * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Scenario B */}
            <div className="card" style={{ margin: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--factor-illumination)', marginBottom: 'var(--space-3)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>🟡 SCENARIO B</span>
                <select
                  value={presetB}
                  onChange={(e) => handleSelectPresetB(e.target.value)}
                  style={{
                    background: 'var(--color-bg-base)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-lunar)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '3px 8px',
                    fontSize: 11,
                  }}
                >
                  <option value="solar_focus">Continuous Solar Power</option>
                  <option value="water_focus">Water Extraction (ISRU)</option>
                  <option value="safety_first">Maximum Radiation Safety</option>
                  <option value="construction">Flat Terrain Construction</option>
                  <option value="balanced">Balanced Exploration</option>
                </select>
              </div>

              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-lunar)', marginBottom: 'var(--space-3)' }}>
                {scenarioB.label}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                {Object.entries(scenarioB.weights).map(([k, v]) => (
                  <div key={k} style={{ fontSize: 11, display: 'flex', justifyContent: 'space-between', padding: '4px 8px', background: 'var(--color-bg-base)', borderRadius: 4 }}>
                    <span style={{ color: 'var(--color-lunar-dim)' }}>{FACTOR_META[k]?.icon} {FACTOR_META[k]?.label}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{(v * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Action button */}
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 'var(--space-6)' }}>
            <button
              onClick={handleRunCompare}
              disabled={loading}
              className="btn btn-primary"
              style={{ padding: '10px 24px', fontSize: 14 }}
            >
              {loading ? (
                <><div className="spinner" style={{ width: 14, height: 14 }} /> Computing Multi-Criteria Trade-offs...</>
              ) : (
                <>⚖️ Compare Scenarios & Generate AI Narration</>
              )}
            </button>
          </div>

          {/* Error banner */}
          {error && (
            <div style={{ padding: 'var(--space-3)', background: 'rgba(239,68,68,0.1)', border: '1px solid var(--color-danger)', borderRadius: 'var(--radius-md)', color: 'var(--color-danger)', fontSize: 12, marginBottom: 'var(--space-4)' }}>
              ⚠️ {error}
            </div>
          )}

          {/* Results section */}
          {compareResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
              
              {/* AI Narration Card */}
              {compareResult.narration && (
                <div className="briefing-card" style={{ margin: 0, border: '1px solid rgba(79, 142, 255, 0.4)' }}>
                  <div className="briefing-header">
                    🤖 AI Trade-Off Analysis & Operational Narrative
                  </div>
                  <div className="briefing-text" style={{ fontSize: 13, lineHeight: 1.7 }}>
                    {compareResult.narration}
                  </div>
                </div>
              )}

              {/* Side-by-side Top Site Comparison */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-6)' }}>
                
                {/* Site A */}
                {compareResult.top_site_a && (
                  <div className="card" style={{ margin: 0 }}>
                    <div style={{ fontSize: 11, color: 'var(--color-accent)', fontWeight: 700 }}>
                      TOP SITE IN SCENARIO A
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-lunar)', margin: '4px 0' }}>
                      {compareResult.top_site_a.site_id}
                    </div>
                    <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-lunar-dim)', marginBottom: 8 }}>
                      Lat: {compareResult.top_site_a.lat?.toFixed(2)}° · Lon: {compareResult.top_site_a.lon?.toFixed(2)}°
                    </div>
                    <div style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--color-accent)', fontWeight: 700 }}>
                      Score: {(compareResult.top_site_a.total_score * 100).toFixed(1)} / 100
                    </div>
                  </div>
                )}

                {/* Site B */}
                {compareResult.top_site_b && (
                  <div className="card" style={{ margin: 0 }}>
                    <div style={{ fontSize: 11, color: 'var(--factor-illumination)', fontWeight: 700 }}>
                      TOP SITE IN SCENARIO B
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-lunar)', margin: '4px 0' }}>
                      {compareResult.top_site_b.site_id}
                    </div>
                    <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--color-lunar-dim)', marginBottom: 8 }}>
                      Lat: {compareResult.top_site_b.lat?.toFixed(2)}° · Lon: {compareResult.top_site_b.lon?.toFixed(2)}°
                    </div>
                    <div style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--factor-illumination)', fontWeight: 700 }}>
                      Score: {(compareResult.top_site_b.total_score * 100).toFixed(1)} / 100
                    </div>
                  </div>
                )}

              </div>

              {/* Weight Deltas Table */}
              <div className="card" style={{ margin: 0 }}>
                <div className="section-label" style={{ marginBottom: 'var(--space-3)' }}>
                  Factor Priority Deltas
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--space-2)' }}>
                  {Object.entries(compareResult.weight_changes || {}).map(([factor, item]) => {
                    const delta = item.delta
                    const isPositive = delta > 0
                    const isZero = Math.abs(delta) < 0.001
                    return (
                      <div key={factor} style={{
                        background: 'var(--color-bg-base)',
                        padding: 'var(--space-3)',
                        borderRadius: 'var(--radius-md)',
                        textAlign: 'center',
                      }}>
                        <div style={{ fontSize: 11, color: 'var(--color-lunar-dim)', marginBottom: 4 }}>
                          {FACTOR_META[factor]?.icon} {FACTOR_META[factor]?.label}
                        </div>
                        <div style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: 13,
                          fontWeight: 700,
                          color: isZero ? 'var(--color-lunar-dim)' : isPositive ? 'var(--risk-low)' : 'var(--risk-high)',
                        }}>
                          {isZero ? '±0%' : `${isPositive ? '+' : ''}${(delta * 100).toFixed(0)}%`}
                        </div>
                        <div style={{ fontSize: 10, color: 'rgba(200,216,240,0.4)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
                          {(item.weight_a * 100).toFixed(0)}% → {(item.weight_b * 100).toFixed(0)}%
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

            </div>
          )}

        </div>

        {/* Footer */}
        <div style={{
          padding: 'var(--space-4) var(--space-6)',
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'flex-end',
          background: 'rgba(13, 21, 38, 0.95)',
        }}>
          <button onClick={onClose} className="btn btn-ghost">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
