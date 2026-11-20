// Playwright config for recording the README demo (`make demo-gif`, see docs/record_demo.py).
// The recorder starts the API and the built frontend itself and passes DEMO_BASE_URL.
// Not part of `make e2e`: the demo script is named *.record.ts, so the test config skips it.
import { defineConfig, devices } from '@playwright/test'

const size = { width: 1280, height: 760 }

export default defineConfig({
  testDir: '.',
  testMatch: 'demo.record.ts',
  outputDir: process.env.DEMO_OUTPUT_DIR ?? '../test-results/demo',
  timeout: 300_000,
  expect: { timeout: 120_000 },
  workers: 1,
  reporter: [['list']],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: process.env.DEMO_BASE_URL ?? 'http://localhost:4174',
    viewport: size,
    deviceScaleFactor: 1,
    video: { mode: 'on', size },
  },
})
