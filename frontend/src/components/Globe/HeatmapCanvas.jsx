/**
 * HeatmapCanvas.jsx — 2D Canvas Heatmap
 *
 * Renders the /score grid as a color-coded canvas overlay.
 * Green = high suitability, Red = low, transparent = masked (NaN)
 *
 * Phase 3: 2D canvas heatmap (placeholder until CesiumJS 3D in Phase 6)
 *
 * Click on any pixel to select that location and show its details.
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useAppStore } from '../../store/appStore'

// Score → RGBA color (green=high, yellow=mid, red=low, transparent=NaN)
function scoreToRGBA(score) {
  if (score === null || score === undefined) return [0, 0, 0, 0]

  // Clamp 0-1
  const t = Math.max(0, Math.min(1, score))

  let r, g, b
  if (t < 0.5) {
    // red → yellow
    const f = t / 0.5
    r = 239
    g = Math.round(68 + (f * (245 - 68)))
    b = Math.round(68 + (f * (11 - 68)))
  } else {
    // yellow → green
    const f = (t - 0.5) / 0.5
    r = Math.round(245 + (f * (34 - 245)))
    g = Math.round(158 + (f * (197 - 158)))
    b = Math.round(11 + (f * (94 - 11)))
  }

  const alpha = Math.round(180 + t * 70)  // more opaque for high scores
  return [r, g, b, alpha]
}

export default function HeatmapCanvas() {
  const canvasRef    = useRef(null)
  const { scoreResult, isScoring, selectedSite, setSelectedSite } = useAppStore()
  const [tooltip, setTooltip] = useState(null)
  const [canvasSize, setCanvasSize] = useState({ w: 500, h: 500 })

  // Draw heatmap on score result change
  useEffect(() => {
    if (!scoreResult || !canvasRef.current) return
    const { score_grid, grid_rows, grid_cols } = scoreResult

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')

    // Size canvas to fill container while keeping pixels
    const maxDim = Math.min(canvasSize.w, canvasSize.h)
    const pixelW = Math.floor(maxDim / grid_cols)
    const pixelH = Math.floor(maxDim / grid_rows)
    const pixelSize = Math.max(1, Math.min(pixelW, pixelH))
    const drawW = pixelSize * grid_cols
    const drawH = pixelSize * grid_rows

    canvas.width  = drawW
    canvas.height = drawH

    const imageData = ctx.createImageData(drawW, drawH)
    const data = imageData.data

    for (let row = 0; row < grid_rows; row++) {
      for (let col = 0; col < grid_cols; col++) {
        const score = score_grid[row]?.[col]
        const [r, g, b, a] = scoreToRGBA(score)

        for (let py = 0; py < pixelSize; py++) {
          for (let px = 0; px < pixelSize; px++) {
            const idx = ((row * pixelSize + py) * drawW + (col * pixelSize + px)) * 4
            data[idx]     = r
            data[idx + 1] = g
            data[idx + 2] = b
            data[idx + 3] = a
          }
        }
      }
    }

    ctx.putImageData(imageData, 0, 0)

    // Draw top site markers
    if (scoreResult.top_sites) {
      scoreResult.top_sites.forEach((site, i) => {
        const cx = site.col * pixelSize + pixelSize / 2
        const cy = site.row * pixelSize + pixelSize / 2

        // Glow ring
        const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, 14)
        gradient.addColorStop(0, 'rgba(79,142,255,0.6)')
        gradient.addColorStop(1, 'rgba(79,142,255,0)')
        ctx.beginPath()
        ctx.arc(cx, cy, 14, 0, Math.PI * 2)
        ctx.fillStyle = gradient
        ctx.fill()

        // Dot
        ctx.beginPath()
        ctx.arc(cx, cy, 5, 0, Math.PI * 2)
        ctx.fillStyle = i === 0 ? '#ffffff' : '#4f8eff'
        ctx.strokeStyle = '#0a0e1a'
        ctx.lineWidth = 2
        ctx.fill()
        ctx.stroke()

        // Rank label
        ctx.fillStyle = '#fff'
        ctx.font = `bold 9px monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(`#${i + 1}`, cx, cy)
      })
    }

  }, [scoreResult, canvasSize])

  // Handle canvas click → select site or log coords
  const handleClick = useCallback((e) => {
    if (!scoreResult) return
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const pixX = x * scaleX
    const pixY = y * scaleY

    const { grid_rows, grid_cols } = scoreResult
    const pixelSize = canvas.width / grid_cols
    const col = Math.floor(pixX / pixelSize)
    const row = Math.floor(pixY / pixelSize)

    // Find if a top site is near this click
    const nearSite = scoreResult.top_sites?.find(s =>
      Math.abs(s.row - row) <= 2 && Math.abs(s.col - col) <= 2
    )
    if (nearSite) setSelectedSite(nearSite)
  }, [scoreResult])

  // Handle hover → show tooltip
  const handleMouseMove = useCallback((e) => {
    if (!scoreResult) return
    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    const pixX = x * scaleX
    const pixY = y * scaleY

    const { score_grid, grid_rows, grid_cols, lat_min, lat_max, lon_min, lon_max } = scoreResult
    const pixelSize = canvas.width / grid_cols
    const col = Math.floor(pixX / pixelSize)
    const row = Math.floor(pixY / pixelSize)

    if (row >= 0 && row < grid_rows && col >= 0 && col < grid_cols) {
      const score = score_grid[row]?.[col]
      const lat = lat_min + (row / grid_rows) * (lat_max - lat_min)
      const lon = lon_min + (col / grid_cols) * (lon_max - lon_min)
      setTooltip({ x: e.clientX - rect.left + 12, y: e.clientY - rect.top + 12, score, lat, lon, row, col })
    }
  }, [scoreResult])

  const handleMouseLeave = () => setTooltip(null)

  // Resize observer
  useEffect(() => {
    const container = canvasRef.current?.parentElement
    if (!container) return
    const obs = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      setCanvasSize({ w: width, h: height - 60 })
    })
    obs.observe(container)
    return () => obs.disconnect()
  }, [])

  if (!scoreResult && !isScoring) {
    return (
      <div className="heatmap-container">
        <div className="empty-state">
          <div className="empty-state-icon">🌙</div>
          <div className="empty-state-title">No Analysis Yet</div>
          <div className="empty-state-desc">
            Set your priorities and click "Find Optimal Sites" to generate the lunar suitability map
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="heatmap-container" style={{ padding: 'var(--space-6)', paddingBottom: 'var(--space-4)', position: 'relative' }}>

      {/* Title */}
      <div style={{ position: 'absolute', top: 'var(--space-4)', left: 'var(--space-6)', zIndex: 5 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-lunar-dim)', letterSpacing: '1px', textTransform: 'uppercase' }}>
          Lunar Surface Suitability Map
        </div>
        {scoreResult && (
          <div style={{ fontSize: 10, color: 'rgba(200,216,240,0.4)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            {scoreResult.valid_pixel_count.toLocaleString()} valid pixels ·{' '}
            {scoreResult.masked_pixel_count.toLocaleString()} masked ·{' '}
            {scoreResult.grid_rows}×{scoreResult.grid_cols} grid
          </div>
        )}
      </div>

      {/* Heatmap */}
      <canvas
        ref={canvasRef}
        className="heatmap-canvas"
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ maxWidth: '100%', maxHeight: `${canvasSize.h}px` }}
      />

      {/* Legend */}
      <div className="heatmap-legend">
        <span>Low</span>
        <div className="heatmap-legend-bar" />
        <span>High Suitability</span>
        {scoreResult && (
          <span style={{ marginLeft: 'var(--space-3)', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(200,216,240,0.4)' }}>
            🔵 = Top {scoreResult.top_sites?.length} sites
          </span>
        )}
      </div>

      {/* Hover tooltip */}
      {tooltip && (
        <div className="heatmap-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          <div style={{ fontSize: 10, color: 'var(--color-accent)', fontWeight: 600, marginBottom: 4 }}>
            {tooltip.score !== null ? `Score: ${tooltip.score?.toFixed(4)}` : 'Masked (excluded)'}
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--color-lunar-dim)' }}>
            {tooltip.lat?.toFixed(2)}°, {tooltip.lon?.toFixed(2)}°
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'rgba(200,216,240,0.4)', marginTop: 2 }}>
            row={tooltip.row} col={tooltip.col}
          </div>
        </div>
      )}

      {/* Loading overlay */}
      {isScoring && (
        <div className="loading-overlay" style={{ borderRadius: 'var(--radius-lg)' }}>
          <div style={{ fontSize: 32 }}>🌙</div>
          <div className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
          <div className="loading-text">Analysing {(100 * 100).toLocaleString()} lunar pixels...</div>
        </div>
      )}
    </div>
  )
}
