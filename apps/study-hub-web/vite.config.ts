import { defineConfig } from 'vitest/config';

export default defineConfig({
  server: { host: '127.0.0.1', port: 3400, strictPort: true, proxy: { '/api/dashboard': { target: 'http://127.0.0.1:3401', changeOrigin: true } } },
  preview: { host: '127.0.0.1', port: 3400, strictPort: true },
  test: { environment: 'jsdom', restoreMocks: true },
});
