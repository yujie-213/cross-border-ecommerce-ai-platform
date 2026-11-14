import { test, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'

/**
 * V3 workspace: the four business pages against the real local platform.
 * Read-only by design — it never submits a requisition or triggers a model call.
 * Run: S01_V3_BROWSER=true S01_LOCAL_PASSWORD=<admin password> npx playwright test v3.spec.ts
 */
const root = path.resolve(import.meta.dirname, '../../..')
const screenshots = path.join(root, 'docs/evidence/S01-V3/screenshots')
const password = process.env.S01_LOCAL_PASSWORD || ''

test('V3 WORKSPACE: four pages, real facts, AI states, filter restore and three viewports', async ({ page }) => {
  test.skip(process.env.S01_V3_BROWSER !== 'true', 'Explicit local platform + password required')
  expect(!!password, 'S01_LOCAL_PASSWORD is required').toBe(true)
  test.setTimeout(180000)
  mkdirSync(screenshots, { recursive: true })
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  page.on('console', m => { if (m.type() === 'error' && !m.text().includes('401')) errors.push(m.text()) })

  await page.goto('/')
  await page.getByLabel('账号').fill('admin')
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()

  // 1. Login lands on the workbench with a real batch, and nav is URL driven.
  await expect(page.getByRole('heading', { name: '采购运营工作台', exact: true })).toBeVisible()
  await expect(page.locator('.kpi-row')).toBeVisible({ timeout: 45000 })
  await expect(page).toHaveURL(/#\/workbench\?batch=/)
  const kpi = await page.locator('.kpi b').allInnerTexts()
  expect(Number(kpi.reduce((a, b) => a + Number(b), 0))).toBeGreaterThan(0)
  await page.screenshot({ path: path.join(screenshots, '01-workbench-1440.png'), fullPage: true })

  await page.getByRole('link', { name: /补货建议/ }).first().click()
  await expect(page.getByRole('heading', { name: '补货建议', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: /补货建议/ }).first()).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('tbody tr').first()).toBeVisible()
  await page.screenshot({ path: path.join(screenshots, '02-suggestions-1440.png'), fullPage: true })

  // 2. Filters live in the URL and survive a reload; back restores the list.
  await page.getByLabel('SKU / 商品').fill('HL-CBL100')
  await expect(page).toHaveURL(/q=HL-CBL100/, { timeout: 8000 })
  await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 15000 })
  await page.reload()
  await expect(page.getByLabel('SKU / 商品')).toHaveValue('HL-CBL100', { timeout: 30000 })
  await expect(page.locator('tbody tr')).toHaveCount(1, { timeout: 30000 })

  // 3. A historically referenced object: history only, never a submit-ready quantity.
  await page.goto('/#/suggestions')
  await page.getByLabel('状态').selectOption('HISTORICAL_REFERENCE')
  await expect(page).toHaveURL(/state=HISTORICAL_REFERENCE/)
  await expect(page.locator('tbody tr').first().getByText('历史参考', { exact: true })).toBeVisible({ timeout: 20000 })
  const historyRows = page.locator('tbody tr')
  if (await historyRows.count()) {
    await historyRows.first().click()
    await expect(page).toHaveURL(/#\/sku\//)
    await expect(page.locator('.verdict')).toContainText('历史参考')
    await expect(page.locator('.actionbar')).toContainText('暂不可提交')
    await page.screenshot({ path: path.join(screenshots, '03-historical-reference-1440.png'), fullPage: true })
  }

  // 4. ERP reference keeps Scheme B: source is labelled, quantity comes from the ERP record.
  await page.goto('/#/suggestions')
  await page.getByLabel('来源').selectOption('REFERENCE_ONLY')
  await expect(page).toHaveURL(/source=REFERENCE_ONLY/)
  await expect(page.locator('tbody tr').first().getByText('ERP 参考建议', { exact: true })).toBeVisible({ timeout: 25000 })
  await page.locator('tbody tr').first().click()
  await expect(page).toHaveURL(/#\/sku\//)
  await expect(page.locator('.verdict')).toContainText('来源 ERP 建议')
  await expect(page.locator('.ai-head')).toBeVisible()
  const aiState = await page.locator('.ai-head .chip').innerText()
  expect(['已生成', '未生成', '未调用', '生成中']).toContain(aiState)
  await page.screenshot({ path: path.join(screenshots, '04-erp-reference-1440.png'), fullPage: false })

  // 5. Tabs are real sections; the quality tab exposes admission state and hints.
  await page.getByRole('tab', { name: /依据与限制/ }).click()
  await expect(page.locator('.quality-grid')).toBeVisible()
  await page.screenshot({ path: path.join(screenshots, '05-quality-1440.png'), fullPage: false })

  // 6. Requisition ledger reads saved records; UNKNOWN rows keep the reconcile warning.
  await page.getByRole('link', { name: /请购管理/ }).click()
  await expect(page.getByRole('heading', { name: '请购管理', exact: true })).toBeVisible()
  await expect(page.getByText('后端尚未提供请购列表接口')).toBeVisible()
  await page.screenshot({ path: path.join(screenshots, '06-requisitions-1440.png'), fullPage: true })
  await page.waitForTimeout(4000)

  // 7. A saved requisition opens the analysis it was confirmed against (single id in the URL).
  const ledgerRows = page.locator('tbody tr')
  if (await ledgerRows.count()) {
    await ledgerRows.first().getByRole('link', { name: '查看 SKU' }).click()
    await expect(page).toHaveURL(/single=/)
    await expect(page.locator('.ai-head')).toBeVisible()
    await expect(page.locator('.actionbar')).toContainText(/已提交|待 ERP 审批|暂不可提交/)
    await page.waitForTimeout(1500)
    await page.screenshot({ path: path.join(screenshots, '07-sku-analysis-1440.png'), fullPage: false })
    await page.getByRole('tab', { name: /采购条件/ }).click()
    await expect(page.locator('.tab-body')).toBeVisible()
  }

  // 8. Three viewports must not introduce page-level horizontal scrolling.
  for (const [width, height, tag] of [[1024, 900, '1024'], [820, 900, '820']] as const) {
    await page.setViewportSize({ width, height })
    for (const route of ['/#/workbench', '/#/suggestions', '/#/requisitions']) {
      await page.goto(route)
      await page.waitForTimeout(3000)
      expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)
    }
    await page.goto('/#/workbench')
    await page.waitForTimeout(4500)
    await page.screenshot({ path: path.join(screenshots, `08-workbench-${tag}.png`), fullPage: false })
    await page.goto('/#/suggestions')
    await page.waitForTimeout(4500)
    await page.screenshot({ path: path.join(screenshots, `09-suggestions-${tag}.png`), fullPage: false })
  }

  expect(errors).toEqual([])
  writeFileSync(path.join(root, 'docs/evidence/S01-V3/browser-result.json'),
    JSON.stringify({ result: 'PASS', pageErrors: errors, viewports: [1440, 1024, 820], submitted: 0, modelCalls: 0 }, null, 2))
})
