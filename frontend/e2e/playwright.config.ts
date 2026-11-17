// End-to-end tests against the real API, worker, Postgres, and Redis, with the fake LLM.
// The API and worker get their own database (docqa_e2e) and Redis DB, reset on every run.
import { existsSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseEnv } from 'node:util'

import { defineConfig, devices } from '@playwright/test'

const here = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(here, '../..')
const API_PORT = 8001
const WEB_PORT = 4173

// Connection settings come from the environment (CI) or the repo's .env (local).
const envFile = join(repoRoot, '.env')
const dotenv = existsSync(envFile) ? parseEnv(readFileSync(envFile, 'utf8')) : {}
const setting = (name: string, fallback: string) => process.env[name] ?? dotenv[name] ?? fallback

function withPath(url: string, path: string): string {
  const parsed = new URL(url)
  parsed.pathname = path
  return parsed.toString()
}

const databaseUrl =
  process.env.E2E_DATABASE_URL ??
  withPath(
    setting('TEST_DATABASE_URL', 'postgresql+asyncpg://docqa:change-me@localhost:5434/docqa_test'),
    '/docqa_e2e',
  )
const redisUrl =
  process.env.E2E_REDIS_URL ?? withPath(setting('TEST_REDIS_URL', 'redis://localhost:6380/1'), '/2')

const webOrigin = `http://localhost:${WEB_PORT}`
const apiOrigin = `http://localhost:${API_PORT}`

export default defineConfig({
  testDir: '.',
  outputDir: '../test-results',
  timeout: 240_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['list'], ['html', { outputFolder: '../playwright-report', open: 'never' }]]
    : [['list']],
  use: {
    baseURL: webOrigin,
    trace: 'retain-on-failure',
    video: process.env.E2E_VIDEO ? 'on' : 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: './e2e/start-backend.sh',
      cwd: resolve(here, '..'),
      url: `${apiOrigin}/health`,
      // First run downloads the embedding and reranker models.
      timeout: 300_000,
      reuseExistingServer: false,
      stdout: 'pipe',
      env: {
        APP_ENV: 'test',
        LOG_LEVEL: 'WARNING',
        DATABASE_URL: databaseUrl,
        REDIS_URL: redisUrl,
        FRONTEND_ORIGIN: webOrigin,
        SESSION_COOKIE_SECURE: 'false',
        LLM_PROVIDER: 'fake',
        FAKE_LLM_TOKEN_DELAY_MS: '60',
        GROQ_API_KEY: '',
        UPLOAD_DIR: join(tmpdir(), 'docqa-e2e-uploads'),
        WORKER_MAX_JOBS: '1',
        INGEST_RETRY_BASE_DELAY_SECONDS: '1',
        E2E_API_PORT: String(API_PORT),
      },
    },
    {
      command: `npm run build && npx vite preview --port ${WEB_PORT} --strictPort`,
      cwd: resolve(here, '..'),
      url: webOrigin,
      timeout: 120_000,
      reuseExistingServer: false,
      env: { VITE_API_BASE_URL: apiOrigin },
    },
  ],
})
