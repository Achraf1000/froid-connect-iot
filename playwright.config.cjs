const { defineConfig } = require('@playwright/test')
module.exports = defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: '.runtime/browser-results.json' }]],
  use: { baseURL: process.env.BASE_URL || 'http://127.0.0.1:8000', viewport: { width: 1440, height: 1080 }, screenshot: 'only-on-failure' },
})
