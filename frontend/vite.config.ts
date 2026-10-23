import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  // No API proxy, host/origin rewriting or TLS bypass.
  server: { host: '127.0.0.1' },
  test: {
    environment: 'jsdom',
    environmentOptions: { jsdom: { url: 'https://lab.test/' } },
    setupFiles: ['./src/test/setup.ts'],
    clearMocks: true,
    restoreMocks: true,
  },
});
