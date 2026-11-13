import { test, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import path from 'node:path'
const root = path.resolve(import.meta.dirname, '../../..')
const enabled = process.env.S01_ONLINE_BROWSER === 'true'
const session = enabled ? JSON.parse(readFileSync(path.join(root, 'data/private/s01-online/session.json'), 'utf8')) : {}
const out = path.join(root, 'docs/evidence/S01-ONLINE')
test('ONLINE REAL: current ERP to bounded DeepSeek, replay, refresh, reanalysis and cancel', async ({ page }) => {
  test.skip(!enabled, 'Explicit live ERP/model browser authorization required')
  test.setTimeout(480000)
  mkdirSync(path.join(out, 'screenshots'), { recursive: true })
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
  await page.goto('/')
  await page.getByRole('button', { name: '连接身份', exact: true }).first().click()
  await page.getByLabel('短期身份令牌').fill(session.token)
  await page.getByRole('button', { name: '连接会话', exact: true }).click()
  await expect(page.getByText('可信会话 · 已连接')).toBeVisible()
  await page.screenshot({ path: path.join(out, 'screenshots/online-authorized-options.png'), fullPage: true })
  const resume = process.env.S01_ONLINE_BROWSER_RESUME === 'true'
  const checkpoint = resume ? JSON.parse(readFileSync(path.join(out, 'browser-checkpoint.json'), 'utf8')) : null
  const reports: any[] = checkpoint?.reports || []
  let original: any = checkpoint?.original
  for (let index = 0; index < (resume ? 0 : 2); index++) {
    if (!index) {
      await page.getByRole('button', { name: '＋ 新建补货分析', exact: true }).click()
      await page.getByRole('combobox', { name: '授权 SKU / 来源', exact: true }).selectOption({ index: 1 })
    } else {
      await page.getByRole('button', { name: '基于此报告重新分析', exact: true }).click()
    }
    const accepted = page.waitForResponse(r => r.url().endsWith('/api/v1/analysis-tasks') && r.request().method() === 'POST')
    const published = page.waitForResponse(r => /\/analysis-tasks\/[^/]+\/report$/.test(r.url()) && r.status() === 200, { timeout: 220000 })
    await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
    const response = await accepted; expect(response.status()).toBe(202)
    const request = response.request(); const body = request.postDataJSON(); const task = await response.json()
    expect(body.parameters).toEqual({ inputMode: 'ONLINE_TEACHING_ERP' }); expect(body.scope.tenantId).toBeUndefined()
    const report = await (await published).json()
    expect(report.taskRef).toEqual(task.taskRef); expect(report.completeness).toBe('BLOCKED')
    expect(report.dataReport.supplyDemand.baseline).toBeNull(); expect(report.dataReport.supplyDemand.candidates).toEqual([])
    expect(report.analysisReport.ai.status).toBe('AVAILABLE')
    expect(report.analysisReport.ai.actualModelRevision).toBe('deepseek-flash')
    expect(report.analysisReport.ai.binding.snapshotId).toBe(report.snapshotRef)
    expect(report.analysisReport.ai.usage.totalTokens).toBeGreaterThan(0)
    expect(report.analysisReport.ai.usage.totalTokens).toBe(report.analysisReport.ai.usage.inputTokens + report.analysisReport.ai.usage.outputTokens)
    if (!index) {
      original = { body, key: request.headers()['idempotency-key'], taskId: task.taskRef.taskId }
    } else {
      expect(report.dataReport.scenarioSupplement.previousReportRef).toEqual(reports[0].reportRef)
      expect(report.snapshotRef).not.toBe(reports[0].snapshotRef)
      expect(report.dataReport.acquisition.acquisitionId).not.toBe(reports[0].dataReport.acquisition.acquisitionId)
    }
    reports.push(report)
    writeFileSync(path.join(out, 'browser-checkpoint.json'), JSON.stringify({ reports, original }, null, 2))
    await expect(page.getByRole('heading', { name: '本次 ERP 在线采集', exact: true })).toBeVisible()
    await page.getByRole('heading', { name: 'AI 解释', exact: true }).scrollIntoViewIfNeeded()
    await expect(page.getByText('解释可用', { exact: true })).toBeVisible()
    await page.screenshot({ path: path.join(out, `screenshots/online-ai-${index + 1}.png`) })
    await page.screenshot({ path: path.join(out, `screenshots/online-report-${index + 1}.png`), fullPage: true })
    await page.reload(); await expect(page.getByText(report.snapshotRef, { exact: true })).toBeVisible()
  }
  if (resume) {
    const report = reports[1]
    await page.evaluate(({ taskId, scope, choiceRef }) => { sessionStorage.setItem('xuheng.s01.v1', JSON.stringify({ taskId, packageRef: choiceRef })); },
      { taskId: report.taskRef.taskId, scope: report.scope, choiceRef: 'online-' + '' })
    // The saved task is read through the ordinary authenticated report endpoint.
    await page.reload(); await expect(page.getByText(report.snapshotRef, { exact: true })).toBeVisible()
    for (const report of reports) {
      expect(report.analysisReport.ai.status).toBe('AVAILABLE')
      expect(report.analysisReport.ai.binding.snapshotId).toBe(report.snapshotRef)
    }
  }
  const replay = await page.evaluate(async (original) => {
    const csrf = decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('commerce_csrf='))!.slice(14))
    const response = await fetch('/api/v1/analysis-tasks', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': original.key, 'X-CSRF-Token': csrf }, body: JSON.stringify(original.body) })
    return { status: response.status, value: await response.json() }
  }, original)
  expect(replay.status).toBe(202); expect(replay.value.taskRef.taskId).toBe(original.taskId)
  await page.getByRole('button', { name: '查看证据', exact: true }).last().click()
  await expect(page.locator('.evidence-json')).toContainText(reports[1].dataReport.acquisition.acquisitionId)
  await page.getByRole('button', { name: '关闭弹窗', exact: true }).click()
  // A new command cancelled during source acquisition must never reach a model.
  await page.getByRole('button', { name: '基于此报告重新分析', exact: true }).click()
  const cancelling = page.waitForResponse(r => r.url().endsWith('/api/v1/analysis-tasks') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
  const cancelledTask = await (await cancelling).json()
  // Read the current revision after the Worker starts; a 409 is definitive and
  // requires a new explicit confirmation, never an uncertain-send blind retry.
  await page.getByRole('button', { name: '重新查询状态', exact: true }).click()
  const cancelResponse = page.waitForResponse(r => r.url().endsWith('/cancel') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '取消分析任务', exact: true }).click()
  const cancelled = await cancelResponse
  if (cancelled.status() === 409) {
    expect((await cancelled.json()).code).toBe('REVISION_CONFLICT')
    await page.getByRole('button', { name: '重新查询状态', exact: true }).click()
    await page.getByRole('button', { name: '取消分析任务', exact: true }).click()
  }
  await expect(page.getByText('已取消', { exact: true }).first()).toBeVisible()
  await expect(page.getByRole('heading', { name: '供需与补货分析', exact: true })).toHaveCount(0)
  expect(errors).toEqual([])
  writeFileSync(path.join(out, 'phase3-browser.json'), JSON.stringify({ result: 'PASS', kind: 'REAL_EDGE_REAL_ERP_REAL_DEEPSEEK_MYSQL_INDEPENDENT_WORKER',
    taskReports: reports, cancelledTaskRef: cancelledTask.taskRef, replay: 'PASS', refresh: 'PASS', previousReportRef: 'PASS', currentEvidence: 'PASS', errors }, null, 2))
})
