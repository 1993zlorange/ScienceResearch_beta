/// <reference types="vite/client" />
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// Vite owns only the browser process in development. Flask owns the API and
// compatibility adapter on port 8765, so neither process needs special CORS.
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/_legacy': 'http://127.0.0.1:8765',
      '/api': 'http://127.0.0.1:8765',
      '/healthz': 'http://127.0.0.1:8765',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.spec.ts'],
    exclude: ['tests/e2e/**', 'node_modules/**'],
    setupFiles: ['tests/setup.ts'],
    restoreMocks: true,
  },
})

