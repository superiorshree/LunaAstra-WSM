/**
 * MoonGlobe.jsx — 3D Interactive CesiumJS Moon Globe
 *
 * Renders an accurate 3D lunar sphere (Moon Ellipsoid radius = 1,737.4 km).
 * Features:
 *  - Real Moon terrain & lunar surface basemap
 *  - Dynamic color-coded suitability heatmap draped over South Pole coordinates
 *  - 3D interactive candidate site pin markers with rank badges
 *  - Click-to-select with smooth flyTo camera animations
 *  - View controls (Reset to South Pole, Toggle Heatmap, View Mode toggle)
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { useAppStore } from '../../store/appStore'

// Lunar Ellipsoid: Radius = 1,737,400 meters
const MOON_ELLIPSOID = new Cesium.Ellipsoid(1737400.0, 1737400.0, 1737400.0)

// Helper: Score [0, 1] to RGBA color for heatmap texture
function scoreToRGBA(score) {
  if (score === null || score === undefined || isNaN(score)) return [0, 0, 0, 0]
  const t = Math.max(0, Math.min(1, score))
  let r, g, b
  if (t < 0.5) {
    const f = t / 0.5
    r = 239
    g = Math.round(68 + f * (245 - 68))
    b = Math.round(68 + f * (11 - 68))
  } else {
    const f = (t - 0.5) / 0.5
    r = Math.round(245 + f * (34 - 245))
    g = Math.round(158 + f * (197 - 158))
    b = Math.round(11 + f * (94 - 11))
  }
  const a = Math.round(160 + t * 90) // opacity
  return [r, g, b, a]
}

// Generate canvas image from score grid for Cesium imagery provider
function generateHeatmapCanvas(scoreResult) {
  if (!scoreResult) return null
  const { score_grid, grid_rows, grid_cols } = scoreResult
  const canvas = document.createElement('canvas')
  canvas.width = grid_cols
  canvas.height = grid_rows
  const ctx = canvas.getContext('2d')
  const imgData = ctx.createImageData(grid_cols, grid_rows)
  const data = imgData.data

  for (let r = 0; r < grid_rows; r++) {
    for (let c = 0; c < grid_cols; c++) {
      const score = score_grid[r]?.[c]
      const [red, green, blue, alpha] = scoreToRGBA(score)
      const idx = (r * grid_cols + c) * 4
      data[idx] = red
      data[idx + 1] = green
      data[idx + 2] = blue
      data[idx + 3] = alpha
    }
  }

  ctx.putImageData(imgData, 0, 0)
  return canvas
}

export default function MoonGlobe({ onSwitchTo2D }) {
  const containerRef = useRef(null)
  const viewerRef = useRef(null)
  const heatmapLayerRef = useRef(null)
  const entitiesRef = useRef([])

  const { scoreResult, selectedSite, setSelectedSite, isScoring } = useAppStore()

  const [showHeatmap, setShowHeatmap] = useState(true)
  const [showPins, setShowPins] = useState(true)
  const [isGlobeReady, setIsGlobeReady] = useState(false)

  // Initialize Cesium Viewer
  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return

    try {
      // Set Moon Ellipsoid globally
      Cesium.Ellipsoid.WGS84 = MOON_ELLIPSOID

      const viewer = new Cesium.Viewer(containerRef.current, {
        globe: new Cesium.Globe(MOON_ELLIPSOID),
        skyAtmosphere: false,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        infoBox: false,
        selectionIndicator: false,
        timeline: false,
        animation: false,
        navigationHelpButton: false,
        sceneModePicker: false,
        fullscreenButton: false,
        creditContainer: document.createElement('div'), // hide default credits
      })

      // Lunar Space Scene styling
      const scene = viewer.scene
      scene.backgroundColor = Cesium.Color.fromCssColorString('#060b18')
      scene.globe.enableLighting = true
      scene.globe.baseColor = Cesium.Color.fromCssColorString('#2d3748')

      // Add NASA / USGS Lunar WMS imagery or Moon texture provider
      try {
        const moonProvider = new Cesium.WebMapServiceImageryProvider({
          url: 'https://planetarymaps.usgs.gov/cgi-bin/mapserv?map=/maps/earth/moon_simp_cyl.map',
          layers: 'LOLA_CLR_SHADE',
          parameters: {
            transparent: true,
            format: 'image/png',
          },
        })
        viewer.imageryLayers.addImageryProvider(moonProvider)
      } catch (err) {
        console.warn('Lunar WMS provider fallback:', err)
      }

      // Initial Camera: Point directly at South Pole (-90° Lat)
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(0, -85, 3000000, MOON_ELLIPSOID),
        orientation: {
          heading: Cesium.Math.toRadians(0),
          pitch: Cesium.Math.toRadians(-89.9),
          roll: 0.0,
        },
        duration: 0,
      })

      // Handle Click on Globe / Site Pins
      const handler = new Cesium.ScreenSpaceEventHandler(scene.canvas)
      handler.setInputAction((click) => {
        const pickedObject = scene.pick(click.position)
        if (Cesium.defined(pickedObject) && pickedObject.id && pickedObject.id.siteData) {
          setSelectedSite(pickedObject.id.siteData)
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

      viewerRef.current = viewer
      setIsGlobeReady(true)
    } catch (err) {
      console.error('Cesium Viewer initialization error:', err)
    }

    return () => {
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy()
        viewerRef.current = null
      }
    }
  }, [])

  // Update Heatmap Overlay when scoreResult changes
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !isGlobeReady) return

    // Remove previous heatmap layer
    if (heatmapLayerRef.current) {
      viewer.imageryLayers.remove(heatmapLayerRef.current, true)
      heatmapLayerRef.current = null
    }

    if (!scoreResult || !showHeatmap) return

    const heatmapCanvas = generateHeatmapCanvas(scoreResult)
    if (!heatmapCanvas) return

    const { lat_min, lat_max, lon_min, lon_max } = scoreResult

    const imageryProvider = new Cesium.SingleTileImageryProvider({
      url: heatmapCanvas.toDataURL(),
      rectangle: Cesium.Rectangle.fromDegrees(lon_min, lat_min, lon_max, lat_max),
      ellipsoid: MOON_ELLIPSOID,
    })

    const layer = viewer.imageryLayers.addImageryProvider(imageryProvider)
    layer.alpha = 0.82
    heatmapLayerRef.current = layer
  }, [scoreResult, showHeatmap, isGlobeReady])

  // Update Top Candidate Site 3D Pins
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !isGlobeReady) return

    // Clear existing pins
    entitiesRef.current.forEach((e) => viewer.entities.remove(e))
    entitiesRef.current = []

    if (!scoreResult?.top_sites || !showPins) return

    scoreResult.top_sites.forEach((site) => {
      const isSelected = selectedSite?.site_id === site.site_id
      const pinColor = isSelected
        ? Cesium.Color.fromCssColorString('#ffffff')
        : Cesium.Color.fromCssColorString('#4f8eff')

      const entity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(site.lon, site.lat, 15000, MOON_ELLIPSOID),
        point: {
          pixelSize: isSelected ? 16 : 12,
          color: pinColor,
          outlineColor: Cesium.Color.fromCssColorString('#060b18'),
          outlineWidth: 3,
          heightReference: Cesium.HeightReference.NONE,
        },
        label: {
          text: `#${site.rank} ${site.site_id}\n(${(site.total_score * 100).toFixed(0)}%)`,
          font: 'bold 11px Inter, sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -14),
          showBackground: true,
          backgroundColor: Cesium.Color.fromCssColorString('rgba(13, 21, 38, 0.85)'),
          backgroundPadding: new Cesium.Cartesian2(6, 4),
        },
      })

      entity.siteData = site
      entitiesRef.current.push(entity)
    })
  }, [scoreResult, selectedSite, showPins, isGlobeReady])

  // Camera FlyTo when selected site changes
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !selectedSite || !isGlobeReady) return

    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        selectedSite.lon,
        selectedSite.lat,
        750000,
        MOON_ELLIPSOID
      ),
      duration: 1.5,
    })
  }, [selectedSite, isGlobeReady])

  // Fly to South Pole action
  const handleResetToSouthPole = () => {
    const viewer = viewerRef.current
    if (!viewer) return
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(0, -85, 3000000, MOON_ELLIPSOID),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-89.9),
        roll: 0.0,
      },
      duration: 1.2,
    })
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      {/* Cesium Viewer Container */}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Floating Control Overlay */}
      <div style={{
        position: 'absolute',
        top: 'var(--space-4)',
        left: 'var(--space-4)',
        zIndex: 10,
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-2)',
      }}>
        {/* Title */}
        <div style={{
          background: 'rgba(13, 21, 38, 0.85)',
          backdropFilter: 'blur(8px)',
          padding: '8px 14px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border)',
        }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-accent)', letterSpacing: '0.8px' }}>
            🌕 3D MOON TERRAIN & SUITABILITY DRAPE
          </div>
          <div style={{ fontSize: 10, color: 'var(--color-lunar-dim)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            Moon Ellipsoid (R = 1,737.4 km) · South Polar Region
          </div>
        </div>

        {/* View buttons */}
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button
            onClick={handleResetToSouthPole}
            className="btn btn-ghost"
            style={{ fontSize: 11, padding: '5px 10px', background: 'rgba(13, 21, 38, 0.85)' }}
            title="Center view on Lunar South Pole"
          >
            🧭 South Pole
          </button>
          <button
            onClick={() => setShowHeatmap(!showHeatmap)}
            className="btn btn-ghost"
            style={{
              fontSize: 11,
              padding: '5px 10px',
              background: showHeatmap ? 'var(--color-accent-dim)' : 'rgba(13, 21, 38, 0.85)',
              borderColor: showHeatmap ? 'var(--color-accent)' : 'var(--color-border)',
            }}
          >
            🔥 Heatmap {showHeatmap ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={() => setShowPins(!showPins)}
            className="btn btn-ghost"
            style={{
              fontSize: 11,
              padding: '5px 10px',
              background: showPins ? 'var(--color-accent-dim)' : 'rgba(13, 21, 38, 0.85)',
              borderColor: showPins ? 'var(--color-accent)' : 'var(--color-border)',
            }}
          >
            📍 Sites {showPins ? 'ON' : 'OFF'}
          </button>
          <button
            onClick={onSwitchTo2D}
            className="btn btn-ghost"
            style={{ fontSize: 11, padding: '5px 10px', background: 'rgba(13, 21, 38, 0.85)' }}
            title="Switch to 2D Raster Grid view"
          >
            🗺️ 2D Grid
          </button>
        </div>
      </div>

      {/* Legend Overlay at bottom */}
      <div style={{
        position: 'absolute',
        bottom: 'var(--space-4)',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 10,
        background: 'rgba(13, 21, 38, 0.85)',
        backdropFilter: 'blur(8px)',
        padding: '6px 16px',
        borderRadius: 'var(--radius-full)',
        border: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-3)',
        fontSize: 11,
      }}>
        <span style={{ color: 'var(--risk-high)', fontSize: 10 }}>Low</span>
        <div className="heatmap-legend-bar" style={{ width: 140, height: 6 }} />
        <span style={{ color: 'var(--risk-low)', fontSize: 10 }}>High Suitability</span>
      </div>

      {/* Loading Overlay */}
      {isScoring && (
        <div className="loading-overlay" style={{ borderRadius: 0 }}>
          <div style={{ fontSize: 32 }}>🌕</div>
          <div className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
          <div className="loading-text">Draping suitability tensor on Lunar 3D Terrain...</div>
        </div>
      )}
    </div>
  )
}
