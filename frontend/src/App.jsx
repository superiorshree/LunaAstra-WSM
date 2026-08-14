/**
 * App.jsx — Root application component
 *
 * Assembles the full 3-panel layout:
 *  Header (logo + weather banner + What-If Scenario button + View Switcher)
 *  Left: ControlPanel (sliders + NL assistant)
 *  Center: MoonGlobe (3D CesiumJS Moon Globe) OR HeatmapCanvas (2D Grid)
 *  Right: SitePanel (ranked sites + XAI + Dossier triggers)
 *  Modals: ScenarioModal (What-If Analysis) + SiteReportModal (Mission Dossier)
 */

import { useState, useEffect } from 'react'
import ControlPanel from './components/ControlPanel/ControlPanel'
import HeatmapCanvas from './components/Globe/HeatmapCanvas'
import MoonGlobe from './components/Globe/MoonGlobe'
import SitePanel from './components/SitePanel/SitePanel'
import WeatherBanner from './components/WeatherBanner/WeatherBanner'
import ScenarioModal from './components/ScenarioPanel/ScenarioModal'
import SiteReportModal from './components/SitePanel/SiteReportModal'
import { useAppStore } from './store/appStore'
import { getHealth } from './api'

export default function App() {
  const { setBackendReady, runScore, weights, maxSlopeDeg } = useAppStore()

  const [viewMode, setViewMode] = useState('3d') // '3d' | '2d'
  const [isScenarioOpen, setIsScenarioOpen] = useState(false)
  const [reportSiteId, setReportSiteId] = useState(null)

  // Poll backend health until ready, then auto-run initial score
  useEffect(() => {
    let attempts = 0
    const maxAttempts = 30

    const check = async () => {
      try {
        const health = await getHealth()
        if (health.status === 'healthy' || health.data_loaded) {
          setBackendReady(true)
          runScore() // Run initial scoring on load
          return
        }
      } catch {
        /* backend not ready yet */
      }

      attempts++
      if (attempts < maxAttempts) {
        setTimeout(check, 1000)
      }
    }

    check()
  }, [])

  return (
    <div className="app-shell">
      {/* ─── Header ─────────────────────────────────────────────────── */}
      <header className="app-header">
        <div className="app-logo">
          <div className="app-logo-icon" />
          <div>
            <div className="app-logo-text">
              Luna<span>Astra</span>
            </div>
            <div className="app-tagline">Lunar Habitat AI Decision Support · SW02</div>
          </div>
        </div>

        {/* Live weather banner — center */}
        <WeatherBanner />

        {/* Right actions: What-If Scenario Modal & View Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
          <button
            onClick={() => setIsScenarioOpen(true)}
            className="btn btn-ghost"
            style={{
              fontSize: 12,
              padding: '6px 12px',
              borderColor: 'var(--color-accent)',
              color: 'var(--color-accent)',
              background: 'var(--color-accent-dim)',
            }}
          >
            ⚖️ What-If Scenarios
          </button>

          <div style={{
            display: 'flex',
            background: 'var(--color-bg-base)',
            padding: 2,
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border)',
          }}>
            <button
              onClick={() => setViewMode('3d')}
              style={{
                background: viewMode === '3d' ? 'var(--color-accent)' : 'transparent',
                color: viewMode === '3d' ? '#fff' : 'var(--color-lunar-dim)',
                border: 'none',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 150ms ease',
              }}
            >
              🌕 3D Globe
            </button>
            <button
              onClick={() => setViewMode('2d')}
              style={{
                background: viewMode === '2d' ? 'var(--color-accent)' : 'transparent',
                color: viewMode === '2d' ? '#fff' : 'var(--color-lunar-dim)',
                border: 'none',
                padding: '4px 10px',
                borderRadius: 'var(--radius-sm)',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 150ms ease',
              }}
            >
              🗺️ 2D Grid
            </button>
          </div>
        </div>
      </header>

      {/* ─── Left Panel: Controls ────────────────────────────────────── */}
      <ControlPanel />

      {/* ─── Center: 3D Moon Globe / 2D Heatmap Grid ─────────────────── */}
      <main className="panel-globe">
        {viewMode === '3d' ? (
          <MoonGlobe onSwitchTo2D={() => setViewMode('2d')} />
        ) : (
          <HeatmapCanvas />
        )}
      </main>

      {/* ─── Right Panel: Sites & XAI ────────────────────────────────── */}
      <SitePanel onOpenReport={(siteId) => setReportSiteId(siteId)} />

      {/* ─── Modals ──────────────────────────────────────────────────── */}
      <ScenarioModal
        isOpen={isScenarioOpen}
        onClose={() => setIsScenarioOpen(false)}
        currentWeights={weights}
        currentMaxSlope={maxSlopeDeg}
      />

      <SiteReportModal
        isOpen={!!reportSiteId}
        onClose={() => setReportSiteId(null)}
        siteId={reportSiteId}
      />
    </div>
  )
}
