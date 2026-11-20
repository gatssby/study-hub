import { defineConfig } from 'vitest/config';

const observer = { target: 'http://127.0.0.1:3401', headers: { Host: 'localhost' } };

export default defineConfig({
  server: { host: '127.0.0.1', port: 3400, strictPort: true, proxy: { '/api/dashboard': observer, '/api/library': observer, '/api/lessons/': observer } },
  preview: { host: '127.0.0.1', port: 3400, strictPort: true },
  test: { environment: 'jsdom', restoreMocks: true },
});
