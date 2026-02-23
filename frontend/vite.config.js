import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Dev only: proxy /api calls to FastAPI on :8000
      // Your api.js uses full URL so this isn't strictly needed,
      // but handy if you ever switch to relative paths.
      '/digest': 'http://localhost:8000',
      '/config': 'http://localhost:8000',
      '/digests': 'http://localhost:8000',
    },
  },
})