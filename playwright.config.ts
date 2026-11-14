import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests', timeout: 60_000, workers: 1, retries: 0,
  use: { baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1100 },
    launchOptions: { args: ['--enable-unsafe-swiftshader'] }, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  reporter: [['list'], ['json', { outputFile: 'reports/browser-test-results.json' }]],
  webServer: { command: 'npm.cmd run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: true },
});
