import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// CORS is already enabled on the FastAPI backend, so we call it directly via
// VITE_API_URL (see src/lib/api.js). No dev proxy required.
export default defineConfig({
  plugins: [react()],
  server: { port: 4200 },
})
