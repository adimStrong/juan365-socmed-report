import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: ['juan365-socmed-report-production.up.railway.app', 'localhost'],
  },
})
