import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import cesium from 'vite-plugin-cesium'

export default defineConfig({
  plugins: [react(), cesium()],
  base: './',   // required for Electron to load assets via file:// protocol
  server: {
    port: 5173,
    proxy: {
      // Proxy API calls to FastAPI backend during dev
      '/score':         'http://localhost:8000',
      '/explain':       'http://localhost:8000',
      '/space-weather': 'http://localhost:8000',
      '/assistant':     'http://localhost:8000',
      '/health':        'http://localhost:8000',
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
})
