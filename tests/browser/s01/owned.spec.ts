import { test, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import path from 'node:path'
const root = path.resolve(import.meta.dirname, '../../..')
const enabled = process.env.S01_OWNED_BROWSER === 'true'
const out = path.join(root, 'data/private/s01-carton-fix-20261113/browser')

test('OWNED REAL: two ERP SMA reports, AI, evidence, scope and cancellation', async ({ page }) => {
  test.skip(!enabled, 'Explicit owned live integration required')
  test.setTimeout(360000)
  mkdirSync(out, { recursive: true })
  const session = JSON.parse(readFileSync(path.join(root, 'data/private/s01-online/session.json'), 'utf8'))
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
  const resume = process.env.S01_OWNED_BROWSER_RESUME === 'true'
  const reports: any[] = resume ? JSON.parse(readFileSync(path.join(out, 'reports.json'), 'utf8')) : []
  const accepted: any[] = resume ? JSON.parse(readFileSync(path.join(out, 'accepted.json'), 'utf8')) : []
  const control = async (action: string) => {
    const file = path.join(root, 'data/private/s01-online/owned-test-control.json')
    writeFileSync(file, JSON.stringify({ action, status: 'REQUESTED' }))
    await expect.poll(() => JSON.parse(readFileSync(file, 'utf8')).status, { timeout: 15000 }).toBe('DONE')
  }
  await page.goto('/')
  await page.getByRole('button', { name: '连接身份', exact: true }).first().click()
  await page.getByLabel('短期身份令牌').fill(session.token)
  await page.getByRole('button', { name: '连接会话', exact: true }).click()
  await expect(page.getByText('可信会话 · 已连接')).toBeVisible()
  await expect(page.getByText('当前有权分析 2 个 SKU；范围外商品不会自动进入分析或统计。')).toBeVisible()
  for (const sku of resume ? [] : ['HL-CBL100-2M', 'HL-MUG350-WH']) {
    await page.goto('/#workbench')
    await page.getByRole('button', { name: '＋ 新建补货分析', exact: true }).click()
    const select = page.getByRole('combobox', { name: '授权 SKU / 来源', exact: true })
    const labels = await select.locator('option').allTextContents()
    await select.selectOption({ label: labels.find(x => x.startsWith(sku + ' ·'))! })
    const received = page.waitForResponse(r => r.url().endsWith('/api/v1/analysis-tasks') && r.request().method() === 'POST')
    const published = page.waitForResponse(r => /\/analysis-tasks\/[^/]+\/report$/.test(r.url()) && r.status() === 200, { timeout: 220000 })
    await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
    const response = await received; expect(response.status()).toBe(202)
    accepted.push({ key: response.request().headers()['idempotency-key'], body: response.request().postDataJSON(), task: await response.json() })
    writeFileSync(path.join(out, 'accepted.json'), JSON.stringify(accepted, null, 2))
    const report = await (await published).json(); reports.push(report)
    writeFileSync(path.join(out, 'reports.json'), JSON.stringify(reports, null, 2))
    expect(report.dataReport.scenarioSupplement.monitoring.scopeVersion).toBe(1)
    expect(report.dataReport.forecast.observationDays).toBe(7)
    expect(report.completeness).toBe('RULES_ONLY')
    if (sku.includes('CBL')) {
      expect(report.dataReport.supplyDemand.candidates.map((c: any) => c.quantity)).toEqual(['48'])
      if (report.dataReport.existingPurchases?.policyVersion === 's01-approved-purchases-v1') {
        expect(report.dataReport.forecast.excludedSupply).toEqual([])
      } else {
        expect(report.dataReport.forecast.excludedSupply[0].pendingQuantity).toBe('36')
      }
      expect(report.dataReport.forecast.constraints.orderMultiple).toBe('8')
      await expect(page.locator('.candidate .big')).toContainText('48 件（6 箱）')
    } else {
      expect(report.dataReport.supplyDemand.candidates).toEqual([])
      expect(report.dataReport.supplyDemand.limitations).toEqual(['NO_REPLENISHMENT_NEEDED'])
      expect(report.dataReport.forecast.constraints.orderMultiple).toBe('12')
    }
    expect(report.dataReport.forecast.constraints.wholeCartonRequired).toBe(true)
    expect(report.dataReport.forecast.constraints.ruleVersion).toBe('s01-whole-carton-v1')
    expect(report.dataReport.forecast.constraints.otherConditions).toBe('UNCONFIRMED')
    await expect(page.getByText(/ERP 箱规 \/ 采购订购倍数/)).toBeVisible()
    await expect(page.getByText(/需求从采集业务日次日计算/)).toBeVisible()
    expect(report.analysisReport.ai.status, report.analysisReport.ai.reason).toBe('AVAILABLE')
    expect(report.analysisReport.ai.usage.totalTokens).toBeGreaterThan(0)
    await expect(page.getByRole('heading', { name: '需求预测与 ERP 采购约束', exact: true })).toBeVisible()
    await expect(page.getByText('解释可用', { exact: true })).toBeVisible()
    await page.screenshot({ path: path.join(out, sku + '.png'), fullPage: true })
    await page.reload(); await expect(page.getByText(report.snapshotRef, { exact: true })).toBeVisible()
    const forecastEvidence = page.locator('.source-item').filter({ hasText: /^forecast/ }).getByRole('button', { name: '查看证据', exact: true })
    await forecastEvidence.click(); await expect(page.locator('.evidence-json')).toContainText('SIMPLE_MOVING_AVERAGE')
    await expect(page.locator('.evidence-json')).toContainText('products.default_carton_qty')
    await expect(page.locator('.evidence-json')).toContainText('s01-whole-carton-v1')
    await page.getByRole('button', { name: '关闭弹窗', exact: true }).click()
  }
  if (resume) {
    for (const report of reports) {
      await page.evaluate(taskId => {
        const saved = JSON.parse(sessionStorage.getItem('xuheng.s01.v1') || '{}')
        sessionStorage.setItem('xuheng.s01.v1', JSON.stringify({ ...saved, taskId }))
      }, report.taskRef.taskId)
      await page.goto('/#detail'); await page.reload()
      await expect(page.getByText(report.snapshotRef, { exact: true })).toBeVisible()
      await expect(page.getByText('解释可用', { exact: true })).toBeVisible()
      await page.screenshot({ path: path.join(out, report.scope.canonicalSkuIds[0] + '-resume.png'), fullPage: true })
    }
  }
  // Old immutable results remain readable, but never appear as current candidates.
  const oldFile = path.join(root, 'data/private/s01-mvp-20261113/browser/reports.json')
  if (existsSync(oldFile)) {
    const old = JSON.parse(readFileSync(oldFile, 'utf8'))[0]
    await page.evaluate(taskId => {
      const saved = JSON.parse(sessionStorage.getItem('xuheng.s01.v1') || '{}')
      sessionStorage.setItem('xuheng.s01.v1', JSON.stringify({ ...saved, taskId }))
    }, old.taskRef.taskId)
    await page.goto('/#detail'); await page.reload()
    await expect(page.getByText('历史规则报告 · 采购候选已失效', { exact: true })).toBeVisible()
    await expect(page.locator('.candidate .big')).toHaveCount(0)
    await page.screenshot({ path: path.join(out, 'legacy-rule-obsolete.png'), fullPage: true })
    await page.evaluate(taskId => {
      const saved = JSON.parse(sessionStorage.getItem('xuheng.s01.v1') || '{}')
      sessionStorage.setItem('xuheng.s01.v1', JSON.stringify({ ...saved, taskId }))
    }, reports[reports.length - 1].taskRef.taskId)
    await page.reload()
    await expect(page.getByText(reports[reports.length - 1].snapshotRef, { exact: true })).toBeVisible()
  }
  const checks = await page.evaluate(async (original) => {
    const csrf = decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('commerce_csrf='))!.slice(14))
    const headers = { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }
    const replay = await fetch('/api/v1/analysis-tasks', { method: 'POST', headers: { ...headers, 'Idempotency-Key': original.key }, body: JSON.stringify(original.body) })
    const foreign = structuredClone(original.body); foreign.scope.canonicalSkuIds = ['not-registered']
    const denied = await fetch('/api/v1/analysis-tasks', { method: 'POST', headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify(foreign) })
    return { replayStatus: replay.status, replay: await replay.json(), deniedStatus: denied.status }
  }, accepted[0])
  expect(checks.replayStatus).toBe(202); expect(checks.replay.taskRef).toEqual(accepted[0].task.taskRef)
  expect([400, 403, 422]).toContain(checks.deniedStatus)
  await control('pauseWorker')
  try {
    await page.getByRole('button', { name: '基于此报告重新分析', exact: true }).click()
    const create = page.waitForResponse(r => r.url().endsWith('/api/v1/analysis-tasks') && r.request().method() === 'POST')
    await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
    const created = await (await create).json()
    const cancelled = page.waitForResponse(r => r.url().endsWith('/cancel') && r.request().method() === 'POST')
    await page.getByRole('button', { name: '取消分析任务', exact: true }).click()
    expect((await cancelled).status()).toBe(200)
    await expect(page.getByText('已取消', { exact: true }).first()).toBeVisible()
    await expect(page.getByRole('heading', { name: '供需与补货分析', exact: true })).toHaveCount(0)
    await page.reload(); await expect(page.getByText('已取消', { exact: true }).first()).toBeVisible()
    writeFileSync(path.join(out, 'cancellation.json'), JSON.stringify({ taskRef: created.taskRef, result: 'PASS' }))
  } finally { await control('resumeWorker') }
  // Also cancel while the independent Worker is reading ERP. No provider send
  // may survive cancellation; the private receipt is checked against MySQL.
  await page.goto('/#workbench')
  await page.getByRole('button', { name: '＋ 新建补货分析', exact: true }).click()
  const runningCreate = page.waitForResponse(r => r.url().endsWith('/api/v1/analysis-tasks') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
  const runningTask = await (await runningCreate).json()
  await expect(page.getByText('分析中', { exact: true }).first()).toBeVisible()
  let runningCancel = page.waitForResponse(r => r.url().endsWith('/cancel') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '取消分析任务', exact: true }).click()
  let cancelResponse = await runningCancel
  if (cancelResponse.status() === 409) {
    expect((await cancelResponse.json()).code).toBe('REVISION_CONFLICT')
    await page.getByRole('button', { name: '重新查询状态', exact: true }).click()
    runningCancel = page.waitForResponse(r => r.url().endsWith('/cancel') && r.request().method() === 'POST')
    await page.getByRole('button', { name: '取消分析任务', exact: true }).click()
    cancelResponse = await runningCancel
  }
  expect(cancelResponse.status()).toBe(200)
  await expect(page.getByText('已取消', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('heading', { name: '供需与补货分析', exact: true })).toHaveCount(0)
  writeFileSync(path.join(out, 'running-cancellation.json'), JSON.stringify({ taskRef: runningTask.taskRef, result: 'PASS' }))
  expect(errors).toEqual([])
  writeFileSync(path.join(out, 'result.json'), JSON.stringify({ result: 'PASS', reports: reports.map(r => ({ taskRef: r.taskRef, snapshotRef: r.snapshotRef })),
    replay: 'PASS', unregisteredScope: 'PASS', refresh: 'PASS', evidence: 'PASS', cancellation: 'PASS', errors }, null, 2))
})
