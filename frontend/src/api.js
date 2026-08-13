/**
 * api.js — LunaAstra API Client
 *
 * Centralized fetch wrapper for all backend endpoints.
 * Handles base URL resolution (dev proxy vs Electron production).
 */

const BASE_URL = 'http://localhost:8000'

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body) opts.body = JSON.stringify(body)

  const res = await fetch(`${BASE_URL}${path}`, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// POST /score
export async function postScore({ weights, maxSlopeDeg = 15, topN = 5, includeXai = true }) {
  return request('POST', '/score', {
    weights,
    max_slope_deg: maxSlopeDeg,
    top_n: topN,
    include_xai: includeXai,
  })
}

// GET /space-weather
export async function getSpaceWeather() {
  return request('GET', '/space-weather')
}

// POST /assistant
export async function postAssistant(text) {
  return request('POST', '/assistant', { text })
}

// POST /explain/site
export async function postExplainSite(siteId, includeBriefing = true) {
  return request('POST', '/explain/site', {
    site_id: siteId,
    include_briefing: includeBriefing,
    include_anomalies: true,
  })
}

// POST /explain/compare
export async function postExplainCompare(scenarioA, scenarioB) {
  return request('POST', '/explain/compare', {
    scenario_a: scenarioA,
    scenario_b: scenarioB,
    top_n: 5,
  })
}

// GET /health
export async function getHealth() {
  return request('GET', '/health')
}
