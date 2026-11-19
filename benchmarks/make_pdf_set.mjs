// Build the PDF set for the ingestion benchmark: the latest locked 10-K of four companies,
// printed to PDF by Playwright's Chromium (real layout, real tables, selectable text).
// Run with `make bench-pdfs` after `make download`. Output: data/bench/pdfs/ (gitignored).
import { existsSync, mkdirSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..')
// Playwright is a frontend dev dependency; resolve it from there.
const require = createRequire(join(repo, 'frontend', 'package.json'))
const { chromium } = require('@playwright/test')

const TICKERS = ['AAPL', 'AMZN', 'JNJ', 'MSFT']
const lock = JSON.parse(readFileSync(join(repo, 'data', 'filings.lock.json'), 'utf8'))
const outDir = join(repo, 'data', 'bench', 'pdfs')
mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch()
try {
  for (const ticker of TICKERS) {
    const latest = lock.filings
      .filter((f) => f.ticker === ticker)
      .sort((a, b) => b.fiscal_year - a.fiscal_year)[0]
    const source = join(repo, 'data', 'raw', latest.local_path)
    if (!existsSync(source)) throw new Error(`${source} is missing; run \`make download\` first`)
    const out = join(outDir, `${ticker}-10K-FY${latest.fiscal_year}.pdf`)
    const page = await browser.newPage()
    // Offline: the filing's few external images aren't needed for text extraction.
    await page.route(/^https?:/, (route) => route.abort())
    await page.goto(pathToFileURL(source).href, { waitUntil: 'load', timeout: 120_000 })
    await page.pdf({ path: out, format: 'Letter', margin: { top: '0.5in', bottom: '0.5in' } })
    await page.close()
    console.log(`wrote ${out}`)
  }
} finally {
  await browser.close()
}
