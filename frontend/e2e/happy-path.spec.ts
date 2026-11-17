import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test, type Page } from '@playwright/test'

const SAMPLE_PDF = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../backend/tests/fixtures/sample_report.pdf',
)
const PASSWORD = 'correct horse battery'

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.org`
}

async function signUp(page: Page, email: string) {
  await page.goto('/signup')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
  await page.getByLabel('Confirm password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign up' }).click()
  await expect(page).toHaveURL(/\/workspaces$/)
  await expect(page.getByTestId('current-user')).toHaveText(email)
}

test('sign up, upload a PDF, ask a question, and open the cited passage', async ({ page }) => {
  const email = uniqueEmail()
  await signUp(page, email)

  // Create a workspace and open it.
  await page.getByLabel('New workspace name').fill('Northwind research')
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name: 'Northwind research' }).click()
  await expect(page.getByTestId('workspace-name')).toHaveText('Northwind research')

  // Upload the fixture PDF and wait for ingestion to finish.
  await page.getByTestId('upload-input').setInputFiles(SAMPLE_PDF)
  const row = page.getByTestId('document-row').filter({ hasText: 'sample_report' })
  await expect(row).toBeVisible()
  await expect(row).toHaveAttribute('data-status', 'ready', { timeout: 180_000 })
  await expect(row).toContainText('3 pages')

  // Refreshing keeps the session.
  await page.reload()
  await expect(page.getByTestId('current-user')).toHaveText(email)
  await expect(row).toHaveAttribute('data-status', 'ready')

  // Ask a question; the answer streams in, then carries a citation.
  await page.getByRole('link', { name: 'Ask questions' }).click()
  await page.getByLabel('Question').fill("Where is the company's largest supplier located?")
  await page.getByLabel('Question').press('Enter')

  // Partial text is visible while the answer is still streaming (the first question also
  // loads the embedding and reranker models, hence the longer timeout).
  await expect(
    page.locator('[data-testid="chat-turn"][data-state="streaming"] [data-testid="answer-text"]'),
  ).toHaveText(/\S/, { timeout: 60_000 })
  const turn = page.getByTestId('chat-turn').last()
  await expect(turn).toHaveAttribute('data-state', 'done', { timeout: 30_000 })
  await expect(turn.getByTestId('answer-text')).toContainText('Portugal')

  const chip = turn.getByTestId('citation-chip').first()
  await expect(chip).toContainText('sample_report')
  await chip.click()

  const panel = page.getByTestId('citation-panel')
  await expect(panel.getByTestId('citation-document')).toHaveText('sample_report')
  await expect(panel.getByTestId('citation-location')).toContainText('p. 3')
  await expect(panel.getByTestId('passage-text')).toContainText(
    "The company's largest supplier is located in Portugal.",
  )

  // A question the documents can't answer is refused.
  await page.getByLabel('Question').fill('Who won the 2022 FIFA World Cup?')
  await page.getByRole('button', { name: 'Ask' }).click()
  const refused = page.getByTestId('chat-turn').last()
  await expect(refused).toHaveAttribute('data-state', 'refused', { timeout: 30_000 })
  await expect(refused).toContainText('Not in your documents')
  await expect(refused.getByTestId('citation-chip')).toHaveCount(0)
})

test('protected pages require login, and bad credentials show an error', async ({ page }) => {
  await page.goto('/workspaces')
  await expect(page).toHaveURL(/\/login$/)

  const email = uniqueEmail()
  await signUp(page, email)
  await page.getByRole('button', { name: 'Log out' }).click()
  await expect(page).toHaveURL(/\/login$/)

  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill('not the password')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page.getByRole('alert')).toHaveText('Invalid email or password')

  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/workspaces$/)
})

test('a cut-off stream keeps its partial answer, and the rate limit says when to retry', async ({
  page,
}) => {
  await signUp(page, uniqueEmail())
  await page.getByLabel('New workspace name').fill('Limits')
  await page.getByRole('button', { name: 'Create' }).click()
  await page.getByRole('link', { name: 'Chat' }).click()
  const question = page.getByLabel('Question')

  // The connection drops after two tokens: the text so far stays, with a notice.
  await page.route('**/ask', async (route) => {
    if (route.request().method() !== 'POST') return route.continue()
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Access-Control-Allow-Origin': new URL(page.url()).origin,
        'Access-Control-Allow-Credentials': 'true',
      },
      body: 'event: token\ndata: {"text":"Partial "}\n\nevent: token\ndata: {"text":"answer"}\n\n',
    })
  })
  await question.fill('What happens if the network drops?')
  await question.press('Enter')
  const cut = page.getByTestId('chat-turn').last()
  await expect(cut).toHaveAttribute('data-state', 'error')
  await expect(cut.getByTestId('answer-text')).toHaveText('Partial answer')
  await expect(cut.getByTestId('answer-error')).toContainText('closed before the answer finished')
  await page.unroute('**/ask')

  // Five questions a minute are allowed (no documents, so each is refused quickly).
  for (let i = 1; i <= 5; i++) {
    await question.fill(`Question number ${i}?`)
    await question.press('Enter')
    await expect(page.getByTestId('chat-turn').last()).toHaveAttribute('data-state', 'refused')
  }
  await question.fill('One too many?')
  await question.press('Enter')
  const limited = page.getByTestId('chat-turn').last()
  await expect(limited).toHaveAttribute('data-state', 'error')
  await expect(limited.getByTestId('rate-limit-notice')).toContainText(
    /Too many questions.*You can ask again in \d+ (s|min)\./,
  )
})
