/**
 * App.jsx — Root application component
 *
 * Assembles the full 3-panel layout:
 *  Header (logo + weather banner)
 *  Left: ControlPanel (sliders + NL assistant)
 *  Center: HeatmapCanvas (2D grid → Phase 6: CesiumJS 3D globe)
 *  Right: SitePanel (ranked sites + XAI)
 */

import { useEffect } from 'react'
import ControlPanel from './components/ControlPanel/ControlPanel'
import HeatmapCanvas from './components/Globe/HeatmapCanvas'
import SitePanel from './components/SitePanel/SitePanel'
import WeatherBanner from './components/WeatherBanner/WeatherBanner'
import { useAppStore } from './store/appStore'
import { getHealth } from './api'

export default function App() {
  const { setBackendReady, runScore } = useAppStore()

  // Poll backend health until ready, then auto-run initial score
  useEffect(() => {
    let attempts = 0
    const maxAttempts = 30

    const check = async () => {
      try {
        const health = await getHealth()
        if (health.status === 'healthy' || health.data_loaded) {
          setBackendReady(true)
          runScore()   // Run initial scoring on load
          return
        }
      } catch { /* backend not ready yet */ }

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

        {/* Right badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexShrink: 0 }}>
          <span className="header-badge">Phase 3</span>
          <span style={{ fontSize: 10, color: 'var(--color-lunar-dim)', fontFamily: 'var(--font-mono)' }}>
            Mock Data Mode
          </span>
        </div>
      </header>

      {/* ─── Left Panel: Controls ────────────────────────────────────── */}
      <ControlPanel />

      {/* ─── Center: Heatmap / Globe ─────────────────────────────────── */}
      <main className="panel-globe">
        <HeatmapCanvas />
      </main>

      {/* ─── Right Panel: Sites ──────────────────────────────────────── */}
      <SitePanel />

    </div>
  )
}
