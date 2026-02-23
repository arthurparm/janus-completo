import angular from '@analogjs/vite-plugin-angular'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [angular()],
  ssr: {
    noExternal: ['rxfire']
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['src/test-setup.ts'],
    include: ['src/**/*.spec.ts'],
    clearMocks: true,
    restoreMocks: true,
    server: {
      deps: {
        inline: ['rxfire']
      }
    }
  }
})
