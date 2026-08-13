/**
 * ContributionChart.jsx — Recharts bar chart showing factor contributions
 *
 * Renders a horizontal bar chart of weight × normalized_score per factor.
 * This is the core explainability visualization.
 */

import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  Cell, ResponsiveContainer, LabelList,
} from 'recharts'

const FACTOR_COLORS = {
  ice:          'var(--factor-ice)',
  illumination: 'var(--factor-illumination)',
  radiation:    'var(--factor-radiation)',
  slope:        'var(--factor-slope)',
  comm:         'var(--factor-comm)',
}

const FACTOR_ICONS = {
  ice: '💧', illumination: '☀️', radiation: '🛡️', slope: '⛰️', comm: '📡',
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{
      background: 'var(--color-bg-card)',
      border: '1px solid var(--color-border-bright)',
      borderRadius: 'var(--radius-md)',
      padding: '8px 12px',
      fontSize: 11,
      boxShadow: 'var(--shadow-card)',
    }}>
      <div style={{ fontWeight: 600, color: 'var(--color-lunar)', marginBottom: 4 }}>
        {FACTOR_ICONS[d.factor]} {d.display_name}
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-accent)' }}>
        Contribution: {d.contribution.toFixed(4)} ({d.percentage.toFixed(1)}%)
      </div>
      <div style={{ color: 'var(--color-lunar-dim)', marginTop: 2 }}>
        Weight: {(d.weight * 100).toFixed(0)}% × Score: {(d.normalized_score * 100).toFixed(0)}%
      </div>
      {d.raw_value !== undefined && d.raw_value !== null && (
        <div style={{ color: 'rgba(200,216,240,0.5)', marginTop: 2 }}>
          Raw: {d.raw_value.toFixed(3)} {d.unit}
        </div>
      )}
    </div>
  )
}

export default function ContributionChart({ contributions }) {
  if (!contributions?.length) return null

  // Sort by contribution descending for chart
  const sorted = [...contributions].sort((a, b) => b.contribution - a.contribution)

  return (
    <div>
      <div className="section-label" style={{ marginBottom: 'var(--space-3)' }}>
        Score Contribution Breakdown
      </div>

      {/* Mini bar rows (always visible) */}
      <div style={{ marginBottom: 'var(--space-4)' }}>
        {sorted.map(item => (
          <div key={item.factor} className="contrib-bar-row">
            <span className="contrib-bar-label" title={item.display_name}>
              {FACTOR_ICONS[item.factor]} {item.display_name}
            </span>
            <div className="contrib-bar-track">
              <div
                className="contrib-bar-fill"
                style={{
                  width: `${item.percentage}%`,
                  background: FACTOR_COLORS[item.factor] || '#4f8eff',
                }}
              />
            </div>
            <span className="contrib-bar-pct">{item.percentage.toFixed(0)}%</span>
          </div>
        ))}
      </div>

      {/* Recharts bar chart */}
      <ResponsiveContainer width="100%" height={140}>
        <BarChart
          data={sorted}
          layout="vertical"
          margin={{ top: 0, right: 10, left: -10, bottom: 0 }}
        >
          <XAxis
            type="number"
            domain={[0, 'auto']}
            tick={{ fill: 'rgba(200,216,240,0.4)', fontSize: 10, fontFamily: 'monospace' }}
            tickFormatter={v => v.toFixed(2)}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="factor"
            tick={false}
            axisLine={false}
            tickLine={false}
            width={0}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(79,142,255,0.05)' }} />
          <Bar dataKey="contribution" radius={[0, 4, 4, 0]} barSize={12}>
            {sorted.map(item => (
              <Cell
                key={item.factor}
                fill={FACTOR_COLORS[item.factor] || '#4f8eff'}
                fillOpacity={0.85}
              />
            ))}
            <LabelList
              dataKey="percentage"
              position="right"
              formatter={v => `${v.toFixed(0)}%`}
              style={{ fill: 'rgba(200,216,240,0.5)', fontSize: 10, fontFamily: 'monospace' }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
