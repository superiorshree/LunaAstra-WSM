/**
 * appStore.js — Zustand Global State
 *
 * Single source of truth for:
 *  - weights (5 factor sliders)
 *  - constraints (max slope)
 *  - score result (heatmap grid + top sites)
 *  - selected site
 *  - space weather
 *  - UI loading/error states
 */

import { create } from 'zustand'
import { postScore, getSpaceWeather } from '../api'

const DEFAULT_WEIGHTS = {
  ice:          0.2,
  illumination: 0.2,
  radiation:    0.2,
  slope:        0.2,
  comm:         0.2,
}

const FACTOR_META = {
  ice:          { label: 'Water Ice',       icon: '💧', color: 'var(--factor-ice)' },
  illumination: { label: 'Solar Power',     icon: '☀️', color: 'var(--factor-illumination)' },
  radiation:    { label: 'Radiation Safety',icon: '🛡️', color: 'var(--factor-radiation)' },
  slope:        { label: 'Terrain',         icon: '⛰️', color: 'var(--factor-slope)' },
  comm:         { label: 'Earth Comms',     icon: '📡', color: 'var(--factor-comm)' },
}

export const useAppStore = create((set, get) => ({
  // ── Weights & Constraints ────────────────────────────────────────────────
  weights:     { ...DEFAULT_WEIGHTS },
  maxSlopeDeg: 15,

  setWeight: (factor, value) => set(state => ({
    weights: { ...state.weights, [factor]: parseFloat(value) }
  })),

  setMaxSlope: (value) => set({ maxSlopeDeg: parseFloat(value) }),

  setWeightsFromAssistant: (weights) => set({ weights }),

  resetWeights: () => set({ weights: { ...DEFAULT_WEIGHTS }, maxSlopeDeg: 15 }),

  // ── Scoring ──────────────────────────────────────────────────────────────
  scoreResult:    null,
  isScoring:      false,
  scoringError:   null,
  lastScoredAt:   null,

  runScore: async () => {
    const { weights, maxSlopeDeg } = get()
    set({ isScoring: true, scoringError: null })
    try {
      const result = await postScore({ weights, maxSlopeDeg, topN: 5, includeXai: true })
      set({
        scoreResult: result,
        isScoring: false,
        lastScoredAt: new Date(),
        selectedSite: result.top_sites?.[0] ?? null,
      })
    } catch (err) {
      set({ isScoring: false, scoringError: err.message })
    }
  },

  // ── Selected Site ────────────────────────────────────────────────────────
  selectedSite: null,
  setSelectedSite: (site) => set({ selectedSite: site }),

  // ── Space Weather ────────────────────────────────────────────────────────
  weatherState: {
    level:        'NORMAL',
    alert_message:'Loading space weather data...',
    alert_color:  '#22c55e',
    active_events:[],
    last_polled:  null,
  },
  isWeatherLoading: false,

  fetchWeather: async () => {
    set({ isWeatherLoading: true })
    try {
      const data = await getSpaceWeather()
      set({ weatherState: data, isWeatherLoading: false })
    } catch {
      set({ isWeatherLoading: false })
    }
  },

  // ── Assistant ────────────────────────────────────────────────────────────
  assistantText:    '',
  assistantLoading: false,
  assistantError:   null,
  assistantResult:  null,

  setAssistantText: (text) => set({ assistantText: text }),

  setAssistantResult: (result) => set({ assistantResult: result }),

  clearAssistantError: () => set({ assistantError: null }),

  // ── Backend Health ────────────────────────────────────────────────────────
  backendReady: false,
  setBackendReady: (v) => set({ backendReady: v }),
}))

export { FACTOR_META, DEFAULT_WEIGHTS }
