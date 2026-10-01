import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Bind to all interfaces + proxy /api to the FastAPI backend so the dev
    // site (and sandbox previews) work with zero CORS setup: api.js calls
    // same-origin /api/... and Vite forwards it to localhost:8000.
    host: true,
    // Dev server only — allow proxied preview hosts (e.g. e2b.app).
    allowedHosts: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
