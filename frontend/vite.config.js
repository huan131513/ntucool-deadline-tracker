import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies /api to the Flask backend so the app can always call
// relative '/api/...' paths — same code works in dev (:5173) and once
// built and served by Flask itself (:5050), no separate API base URL.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5050',
    },
  },
  build: {
    outDir: 'dist',
  },
})
