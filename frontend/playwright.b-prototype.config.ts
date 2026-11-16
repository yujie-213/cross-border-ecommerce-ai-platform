import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '../tests/browser/s01', testMatch: 'b-after-sales-prototype.spec.ts',
  workers: 1, fullyParallel: false, timeout: 30000,
  outputDir: '../.tmp/b-prototype',
  reporter: [['list'], ['junit', { outputFile: '../.tmp/b-prototype.xml' }],
    ['json', { outputFile: '../.tmp/b-prototype.json' }]],
  use: { browserName: 'chromium', channel: 'msedge', viewport: { width: 1440, height: 1000 },
    trace: 'off', screenshot: 'off', video: 'off' }
})
