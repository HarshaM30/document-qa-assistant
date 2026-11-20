// Scripted session recorded as the README demo (`make demo-gif`). Paced for viewing, not
// speed: typing is slowed and each step pauses so the result can be read in the GIF.
import { expect, test, type Page } from '@playwright/test'

const PASSWORD = 'correct horse battery'
const TYPE_DELAY_MS = 35

async function type(page: Page, label: string, text: string) {
  const field = page.getByLabel(label, { exact: true })
  await field.click()
  await field.pressSequentially(text, { delay: TYPE_DELAY_MS })
}

async function ask(page: Page, question: string) {
  await type(page, 'Question', question)
  await page.getByLabel('Question').press('Enter')
  const turn = page.getByTestId('chat-turn').last()
  await expect(turn).toHaveAttribute('data-state', /done|refused|error/)
  return turn
}

test('demo: attach the 10-K library, ask, open a citation, and see a refusal', async ({ page }) => {
  await page.goto('/signup')
  await page.waitForTimeout(600)
  await type(page, 'Email', 'analyst@example.org')
  await type(page, 'Password', PASSWORD)
  await type(page, 'Confirm password', PASSWORD)
  await page.getByRole('button', { name: 'Sign up' }).click()
  await expect(page).toHaveURL(/\/workspaces$/)

  await type(page, 'New workspace name', '10-K research')
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name: '10-K research' }).click()
  await page.waitForTimeout(800)

  // Attach the shared SEC filings library (15 10-Ks, already indexed).
  await page.getByRole('button', { name: 'Attach all' }).click()
  await expect(page.getByRole('button', { name: 'Detach' })).toHaveCount(15)
  await page.waitForTimeout(1500)

  await page.getByRole('link', { name: 'Ask questions' }).click()
  await page.waitForTimeout(600)

  // A table lookup: the answer streams in with citations.
  const first = await ask(page, "What were Apple's iPhone net sales in fiscal 2026?")
  await page.waitForTimeout(1500)
  await first.getByTestId('citation-chip').first().click()
  await expect(page.getByTestId('passage-text')).toBeVisible()
  await page.waitForTimeout(3500)
  await page.getByRole('button', { name: 'Close source panel' }).click()

  // Year over year, across two filings.
  const second = await ask(page, "How did Apple's total net sales change from fiscal 2025 to fiscal 2026?")
  await page.waitForTimeout(1000)
  await second.getByTestId('citation-chip').first().click()
  await page.waitForTimeout(3000)
  await page.getByRole('button', { name: 'Close source panel' }).click()

  // Not in the documents: refused rather than guessed.
  await ask(page, "What was Tesla's total revenue in fiscal 2025?")
  await page.waitForTimeout(3000)
})
