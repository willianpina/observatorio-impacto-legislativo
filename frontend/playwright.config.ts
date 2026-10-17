import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests', fullyParallel: false, workers: 1, timeout: 45000,
  reporter: [['list'], ['json', { outputFile: 'test-results/resultados.json' }]],
  use: { baseURL: 'http://127.0.0.1:3101', trace: 'retain-on-failure',channel:process.env.OIL_BROWSER_CHANNEL || undefined },
  webServer: [
    { command: 'node tests/server.mjs test', url: 'http://127.0.0.1:3101', reuseExistingServer: false, timeout: 180000 },
    { command: 'node tests/server.mjs normal', url: 'http://127.0.0.1:3102', reuseExistingServer: false, timeout: 180000 }
  ]
});
