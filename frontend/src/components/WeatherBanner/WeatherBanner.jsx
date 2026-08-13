/**
 * WeatherBanner.jsx — Live Space Weather Alert Banner
 *
 * Polls /space-weather every 5 minutes.
 * Displays NORMAL (green) / ELEVATED (amber) / HIGH (red pulsing) status.
 */

import { useEffect } from 'react'
import { useAppStore } from '../../store/appStore'

export default function WeatherBanner() {
  const { weatherState, isWeatherLoading, fetchWeather } = useAppStore()

  useEffect(() => {
    fetchWeather()
    const interval = setInterval(fetchWeather, 5 * 60 * 1000) // 5 min
    return () => clearInterval(interval)
  }, [])

  const level = weatherState.level || 'NORMAL'

  return (
    <div className={`weather-banner weather-banner-${level}`}>
      <div className="weather-dot" />

      <span style={{ fontWeight: 600, fontSize: 11, letterSpacing: '0.5px' }}>
        SPACE WEATHER:
      </span>

      <span style={{ fontSize: 12 }}>
        {weatherState.alert_message || 'Loading...'}
      </span>

      {weatherState.active_events?.length > 0 && (
        <span style={{
          marginLeft: 'auto',
          fontSize: 10,
          opacity: 0.7,
          fontFamily: 'var(--font-mono)',
        }}>
          {weatherState.active_events.length} active event{weatherState.active_events.length > 1 ? 's' : ''}
        </span>
      )}

      {weatherState.last_polled && (
        <span style={{
          fontSize: 10,
          opacity: 0.5,
          fontFamily: 'var(--font-mono)',
          marginLeft: weatherState.active_events?.length > 0 ? 'var(--space-3)' : 'auto',
        }}>
          {new Date(weatherState.last_polled).toLocaleTimeString()}
        </span>
      )}

      {isWeatherLoading && (
        <div className="spinner" style={{ marginLeft: 'var(--space-2)', width: 12, height: 12, borderWidth: 1.5 }} />
      )}
    </div>
  )
}
