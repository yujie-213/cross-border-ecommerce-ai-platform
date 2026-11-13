import { test, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import path from 'node:path'
const root = path.resolve(import.meta.dirname, '../../..')
const enabled = process.env.S01_P3_BROWSER === 'true'
const session = enabled ? JSON.parse(readFileSync(path.join(root, 'data/private/s01-online/session.json'), 'utf8')) : {}
const out = path.join(root, 'data/private/s01-p3-min')

test('P3 REAL: owned analysis, human confirmation, ERP submit, lost browser response and same-operation replay', async ({ page }) => {
  test.skip(!enabled, 'Explicit authorized owned teaching create/submit only')
  test.setTimeout(240000)
  mkdirSync(out, { recursive: true })
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto('/')
  await page.getByRole('button', { name: '连接身份', exact: true }).first().click()
  await page.getByLabel('短期身份令牌').fill(session.token)
  await page.getByRole('button', { name: '连接会话', exact: true }).click()
  await expect(page.getByText('可信会话 · 已连接')).toBeVisible()
  await page.getByRole('button', { name: '＋ 新建补货分析', exact: true }).click()
  await page.getByRole('combobox', { name: '授权 SKU / 来源', exact: true }).selectOption({ label: (await page.getByRole('combobox', { name: '授权 SKU / 来源', exact: true }).locator('option').allTextContents()).find(x => x.includes('HL-CBL100-2M'))! })
  const reportResponse = page.waitForResponse(r => r.url().endsWith('/report') && r.status() === 200)
  await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
  const report = await (await reportResponse).json()
  writeFileSync(path.join(out, 'browser-report.json'), JSON.stringify(report, null, 2))
  expect(report.dataReport.supplyDemand.candidates.map((c: any) => c.quantity)).toEqual(['48'])
  expect(report.dataReport.existingPurchases.policyVersion).toBe('s01-approved-purchases-v1')
  expect(report.dataReport.forecast.excludedSupply).toEqual([])
  expect(report.analysisReport.ai.status).toBe('NOT_ATTEMPTED')
  await expect(page.getByRole('heading', { name: 'ERP 已审批正式采购', exact: true })).toBeVisible()
  const quantity = page.getByLabel('确认采购数量 / 件', { exact: true })
  await expect(quantity).toHaveValue('48')
  await quantity.fill('36')
  await expect(page.getByRole('button', { name: '确认并提交 ERP 请购', exact: true })).toBeDisabled()
  await quantity.fill('56')
  await expect(page.getByText('调整数量时请填写原因。', { exact: true })).toBeVisible()
  await quantity.fill('48')
  await page.getByRole('checkbox').check()
  await page.screenshot({ path: path.join(out, 'before-confirm.png'), fullPage: true })
  const endpoint = '/api/v1/analysis-tasks/' + report.taskRef.taskId + '/requisition'
  let original: { key: string; body: any } | undefined
  await page.route('**' + endpoint, async route => {
    if (route.request().method() !== 'POST' || original) { await route.continue(); return }
    original = { key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() }
    const response = await route.fetch({ timeout: 120000 })
    // Simulate loss to this browser after the real backend accepted the operation.
    expect(response.status()).toBe(200)
    await route.abort('connectionreset')
  })
  await page.getByRole('button', { name: '确认并提交 ERP 请购', exact: true }).click()
  let saved: any
  await expect.poll(async () => {
    const response = await page.request.get(endpoint)
    expect(response.status()).toBe(200)
    saved = await response.json()
    if (saved?.state === 'BLOCKED') throw new Error('ERP operation blocked: ' + saved.errorCode)
    return saved?.state
  }, { timeout: 120000, intervals: [1500] }).toBe('SUBMITTED')
  await expect(page.getByText('原提交待确认', { exact: true })).toBeVisible({ timeout: 20000 })
  await page.getByRole('button', { name: '查询已保存的请购结果', exact: true }).click()
  await expect(page.getByText('已提交 ERP，待领导审批', { exact: true })).toBeVisible()
  const cookies = await page.context().cookies()
  const csrf = cookies.find(c => c.name === 'commerce_csrf')!.value
  const repeated = await page.request.post(endpoint, { data: original!.body, headers: { 'Idempotency-Key': original!.key, 'X-CSRF-Token': decodeURIComponent(csrf), Origin: 'http://localhost:5173' } })
  expect(repeated.status()).toBe(200)
  expect(await repeated.json()).toEqual(saved)
  writeFileSync(path.join(out, 'browser-operation.json'), JSON.stringify({ reportId: report.reportRef.reportId, original, result: saved, replay: await repeated.json(), pageErrors: errors }, null, 2))
  await page.reload()
  await expect(page.getByText('已提交 ERP，待领导审批', { exact: true })).toBeVisible()
  await expect(page.getByLabel('确认采购数量 / 件', { exact: true })).toHaveCount(0)
  await page.screenshot({ path: path.join(out, 'submitted-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: path.join(out, 'submitted-mobile.png'), fullPage: true })
  expect(errors).toEqual([])
})
