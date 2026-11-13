import { test, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import type { Page } from '../../../frontend/node_modules/@playwright/test/index.js'
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import path from 'node:path'
const root = path.resolve(import.meta.dirname, '../../..')
const privateDir = path.join(root, 'data/private/s01-frontend')
const session = JSON.parse(readFileSync(path.join(privateDir, 'session.json'), 'utf8'))
const evidenceDir = path.resolve(root, process.env.S01_UI_EVIDENCE_DIR || 'docs/evidence/D-S01-UI-01')
mkdirSync(path.join(evidenceDir, 'screenshots'), { recursive: true })
const observed: unknown[] = []
async function control(action: string) {
  const file = path.join(privateDir, 'control.json'); const id = crypto.randomUUID()
  writeFileSync(file, JSON.stringify({ id, action, status: 'REQUESTED' }))
  await expect.poll(() => { try { const c = JSON.parse(readFileSync(file, 'utf8')); return c.id === id && c.status === 'DONE' } catch { return false } }, { timeout: 15000 }).toBe(true)
}
async function login(page: Page) {
  await page.goto('/'); await page.getByRole('button', { name: '连接身份', exact: true }).first().click()
  await page.getByLabel('短期身份令牌').fill(session.token)
  const response = page.waitForResponse(r => r.url().endsWith('/api/v1/session') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '连接会话', exact: true }).click()
  const established = await response; expect(established.status()).toBe(200)
  const cookie = (await page.context().cookies()).find(c => c.name === 'commerce_session')
  expect(cookie?.secure).toBe(true); expect(cookie?.httpOnly).toBe(true); expect(cookie?.sameSite).toBe('Strict')
  await expect(page.getByText('可信会话 · 已连接')).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
}
async function create(page: Page, caseId = 'A') {
  const pack = session.casePackages.find((x: { caseId: string }) => x.caseId === caseId)
  await page.getByRole('button', { name: '＋ 新建补货分析', exact: true }).click()
  await page.getByRole('combobox', { name: '授权 SKU / 来源', exact: true }).selectOption(pack.packageRef)
  const created = page.waitForResponse(r => r.url().endsWith('/api/v1/analysis-tasks') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
  const response = await created; expect(response.status()).toBe(202)
  const request = response.request(); const body = request.postDataJSON()
  expect(body.scope.tenantId).toBeUndefined(); expect(body.parameters.packageRef).toBe(pack.packageRef)
  expect(request.headers()['idempotency-key']).toBeTruthy(); expect(request.headers()['x-csrf-token']).toBeTruthy()
  const task = await response.json()
  return { task, body, key: request.headers()['idempotency-key'] }
}
async function complete(page: Page) {
  const response = await page.waitForResponse(r => /\/analysis-tasks\/[^/]+\/report$/.test(r.url()) && r.status() === 200)
  const report = await response.json()
  await expect(page.getByRole('heading', { name: '供需与补货分析', exact: true })).toBeVisible()
  return report
}

test('REAL: A—E teaching packages, Worker reports, chart/table, refresh, previousReportRef, evidence, responsive', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message))
  await login(page)
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots/workbench-1440.png'), fullPage: true })
  for (const caseId of ['A', 'B', 'C', 'D', 'E']) {
    await page.getByRole('navigation', { name: '主要导航' }).getByRole('link', { name: /补货建议/ }).click()
    const resultPromise = complete(page)
    const { task, body, key } = await create(page, caseId)
    const report = await resultPromise
    expect(report.taskRef).toEqual(task.taskRef); expect(report.sourceNature).toBe('SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP')
    expect(report.dataReport.scenarioSupplement.procurementEligible).toBe(false)
    expect(report.analysisReport.ai.status).toBe('NOT_ATTEMPTED')
    await expect(page.getByText('教学 ERP 仿真业务数据', { exact: true })).toBeVisible()
    const supply = report.dataReport.supplyDemand
    if (caseId === 'A') {
      expect(supply.baseline.gapQuantity).toBe('17'); expect(supply.candidates[0].quantity).toBe('18'); expect(supply.candidates[0].evaluation.stockoutRisk).toBe(true)
      await expect(page.getByText('到货前风险仍存在', { exact: true })).toBeVisible()
      await page.getByRole('button', { name: '查看等价数据表', exact: true }).click()
      const rows = page.getByRole('table').locator('tbody tr')
      await expect(rows).toHaveCount(14)
      const expected = [...supply.baseline.series, ...supply.candidates[0].evaluation.series]
      for (let i = 0; i < expected.length; i++) { const cells = rows.nth(i).locator('td'); await expect(cells.nth(1)).toHaveText(expected[i].day); await expect(cells.nth(2)).toHaveText(expected[i].demand); await expect(cells.nth(3)).toHaveText(expected[i].arrivals); await expect(cells.nth(4)).toHaveText(expected[i].closingBalance) }
      for (const width of [1440, 1024, 390]) {
        await page.setViewportSize({ width, height: 1000 })
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
        await page.screenshot({ path: path.join(evidenceDir, `screenshots/detail-A-${width}.png`), fullPage: true })
      }
      await page.setViewportSize({ width: 1440, height: 1000 })
      await page.getByRole('button', { name: '查看证据', exact: true }).first().click(); await expect(page.locator('.evidence-json')).toContainText('gapQuantity'); await page.getByRole('button', { name: '关闭弹窗', exact: true }).click()
      const old = report.reportRef
      await page.reload(); await expect(page.getByText(old.reportId, { exact: true }).first()).toBeVisible()
      // Replaying the exact captured browser command hits the actual API, no second task.
      const replay = await page.evaluate(async ({ body, key }) => { const csrf = decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('commerce_csrf='))!.slice(14)); const r = await fetch('/api/v1/analysis-tasks', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key, 'X-CSRF-Token': csrf }, body: JSON.stringify(body) }); return { status: r.status, body: await r.json() } }, { body, key })
      expect(replay.status).toBe(202); expect(replay.body.taskRef).toEqual(task.taskRef)
      const conflict = await page.evaluate(async ({ body, key, pack }) => { const csrf = decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('commerce_csrf='))!.slice(14)); const r = await fetch('/api/v1/analysis-tasks', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key, 'X-CSRF-Token': csrf }, body: JSON.stringify({ ...body, parameters: { packageRef: pack } }) }); return { status: r.status, code: (await r.json()).code } }, { body, key, pack: session.casePackages[1].packageRef })
      expect(conflict).toEqual({ status: 409, code: 'COMMAND_CONFLICT' })
      await page.getByRole('button', { name: '基于此报告重新分析', exact: true }).click()
      const nextReport = complete(page); await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
      const next = await nextReport; expect(next.dataReport.scenarioSupplement.previousReportRef).toEqual(old); expect(next.reportRef).not.toEqual(old)
    } else if (caseId === 'B') { expect(supply.baseline.gapQuantity).toBe('0'); expect(supply.candidates).toHaveLength(0); await expect(page.getByText('未生成补货候选', { exact: true })).toBeVisible() }
    else if (caseId === 'C') { expect(supply.baseline.gapQuantity).toBe('0'); expect(supply.baseline.stockoutRisk).toBe(true); await expect(page.getByText(/总量覆盖，但存在中途缺货/)).toBeVisible() }
    else { expect(supply.candidates).toHaveLength(0) }
    observed.push({ caseId, taskRef: task.taskRef, reportRef: report.reportRef, snapshotRef: report.snapshotRef, packageRef: body.parameters.packageRef, completeness: report.completeness, aiStatus: report.analysisReport.ai.status, gapQuantity: supply.baseline?.gapQuantity ?? null, candidateQuantities: supply.candidates.map((c: { quantity: string }) => c.quantity), sourceNature: report.sourceNature, procurementEligible: false })
    if (caseId === 'E') await page.screenshot({ path: path.join(evidenceDir, 'screenshots/detail-E-1440.png'), fullPage: true })
  }
  await page.getByRole('navigation', { name: '主要导航' }).getByRole('link', { name: /补货建议/ }).click(); await expect(page.getByRole('table').locator('tbody tr')).not.toHaveCount(0)
  await page.screenshot({ path: path.join(evidenceDir, 'screenshots/history-1440.png'), fullPage: true })
  await page.getByRole('link', { name: /人工审批/ }).click(); await expect(page.getByRole('heading', { name: '审批功能尚未开放' })).toBeVisible()
  expect(errors).toEqual([])
  writeFileSync(path.join(evidenceDir, 'real-browser-cases.json'), JSON.stringify({ input: 'FIXED_REAL_GET_CAPTURE_OF_SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP', realApi: true, independentWorker: true, erpNetworkRequests: 0, paidModelRequests: 0, cases: observed, consoleErrors: errors }, null, 2) + '\n')
})

test('REAL: queued cancel, refresh resume and evidence revocation do not leak old report', async ({ page }) => {
  await login(page); await control('pauseWorker')
  try {
    const { task } = await create(page)
    await expect(page.getByText('排队中', { exact: true })).toBeVisible()
    await page.reload(); await expect(page.getByText('排队中', { exact: true })).toBeVisible()
    const stale = await page.evaluate(async ({ id, revision }) => { const csrf = decodeURIComponent(document.cookie.split('; ').find(x => x.startsWith('commerce_csrf='))!.slice(14)); const r = await fetch(`/api/v1/analysis-tasks/${id}/cancel`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID(), 'X-CSRF-Token': csrf }, body: JSON.stringify({ expectedRevision: revision + 1 }) }); return { status: r.status, code: (await r.json()).code } }, { id: task.taskRef.taskId, revision: task.revision })
    expect(stale).toEqual({ status: 409, code: 'REVISION_CONFLICT' })
    const cancelResponse = page.waitForResponse(r => r.url().endsWith('/cancel'))
    await page.getByRole('button', { name: '取消分析任务', exact: true }).click()
    const response = await cancelResponse; expect(response.status()).toBe(200); expect((await response.json()).taskRef).toEqual(task.taskRef)
    await expect(page.getByText('已取消', { exact: true })).toBeVisible(); await expect(page.getByRole('heading', { name: '供需与补货分析' })).toHaveCount(0)
  } finally { await control('resumeWorker') }
  await page.getByRole('navigation', { name: '主要导航' }).getByRole('link', { name: /补货建议/ }).click()
  const reportPromise = complete(page); await create(page); await reportPromise
  await control('revokeRead')
  try {
    await page.getByRole('button', { name: '查看证据', exact: true }).first().click()
    await expect(page.getByText('证据不可访问或不存在', { exact: true })).toBeVisible(); await expect(page.locator('.evidence-json')).toHaveCount(0)
    await page.getByRole('button', { name: '关闭弹窗', exact: true }).click()
    await page.getByRole('button', { name: '重新查询状态', exact: true }).click()
    await expect(page.getByRole('heading', { name: '供需与补货分析' })).toHaveCount(0)
    await expect(page.getByText(/不可访问或不存在，请联系数据负责人核实/)).toBeVisible()
    await page.screenshot({ path: path.join(evidenceDir, 'screenshots/revoked-evidence.png'), fullPage: true })
  } finally { await control('restoreRead') }
})

test('REAL: uncertain create reuses persisted key after refresh; CSRF and Origin stay enforced', async ({ page }) => {
  await login(page)
  const requests: { key: string; taskId: string }[] = []
  const lost = page.waitForEvent('requestfailed', { predicate: r => r.method() === 'POST' && r.url().endsWith('/api/v1/analysis-tasks') })
  await page.route('**/api/v1/analysis-tasks', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    const response = await route.fetch(); const value = await response.json()
    requests.push({ key: route.request().headers()['idempotency-key'], taskId: value.taskRef.taskId })
    await route.abort('failed') // Server accepted; browser did not receive the response.
  })
  await page.getByRole('button', { name: '＋ 新建补货分析', exact: true }).click()
  await page.getByRole('combobox', { name: '授权 SKU / 来源', exact: true }).selectOption(session.casePackages[0].packageRef)
  await page.getByRole('button', { name: '发起真实分析任务', exact: true }).click()
  await expect(page.getByText('命令状态待确认', { exact: true })).toBeVisible()
  await lost
  await expect(page.getByRole('alert')).toContainText('状态待确认')
  await page.unroute('**/api/v1/analysis-tasks')
  await page.reload(); await expect(page.getByRole('button', { name: '使用原命令核对' })).toBeEnabled()
  const replay = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v1/analysis-tasks'))
  await page.getByRole('button', { name: '使用原命令核对' }).click()
  const result = await replay; expect(result.request().headers()['idempotency-key']).toBe(requests[0].key); expect((await result.json()).taskRef.taskId).toBe(requests[0].taskId)
  const rejected = await page.evaluate(async () => { const r = await fetch('/api/v1/analysis-tasks', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': 'csrf-negative' }, body: '{}' }); return r.status })
  expect(rejected).toBe(403)
  const cookies = await page.context().cookies(); const csrf = cookies.find(c => c.name === 'commerce_csrf')!.value
  const originRejected = await page.request.post('/api/v1/analysis-tasks', { headers: { Origin: 'https://not-authorized.invalid', 'Idempotency-Key': 'origin-negative', 'X-CSRF-Token': csrf }, data: {} })
  expect(originRejected.status()).toBe(403)
  const safeStorage = await page.evaluate(() => JSON.stringify({ session: { ...sessionStorage }, local: { ...localStorage } }))
  expect(safeStorage).not.toContain(session.token); expect(safeStorage).not.toContain('explanation')
})

test('PROTOCOL FIXTURES: AI statuses, token unknown, failures, empty and bounded history pagination', async ({ page }) => {
  await login(page)
  const reportPromise = complete(page); const { task } = await create(page); const source = await reportPromise
  for (const status of ['AVAILABLE', 'UNAVAILABLE', 'NOT_ATTEMPTED']) {
    const fixture = structuredClone(source)
    fixture.analysisReport.ai = { status, provider: 'MOCK', usage: { inputTokens: 100, outputTokens: 20, totalTokens: 120, cachedInputTokens: 10, actualCost: null }, tokenUsageStatus: 'KNOWN', costStatus: 'UNKNOWN', explanation: Object.fromEntries(['recommendationReasons', 'keyEvidence', 'majorRisks', 'humanConfirmations'].map(k => [k, [{ text: '协议夹具：仅验证展示，不代表真实模型验收。', supportRefs: ['fixture-ref'] }]])) }
    await page.route(`**/api/v1/analysis-tasks/${task.taskRef.taskId}/report`, route => route.fulfill({ json: fixture }))
    await page.getByRole('button', { name: '重新查询状态', exact: true }).click()
    await expect(page.getByText('KNOWN', { exact: false })).not.toHaveCount(0)
    await expect(page.locator('.token-grid')).toContainText('100'); await expect(page.locator('.token-grid')).toContainText('120')
    if (status === 'AVAILABLE') { await expect(page.getByText('协议夹具：仅验证展示，不代表真实模型验收。')).toHaveCount(4); await expect(page.locator('.explanation-section small')).toHaveText(['依据：fixture-ref', '依据：fixture-ref', '依据：fixture-ref', '依据：fixture-ref']) }
    else await expect(page.getByText(status === 'UNAVAILABLE' ? 'AI 解释不可用' : '本次未启用 AI 解释', { exact: true })).toHaveCount(2)
    await page.unroute(`**/api/v1/analysis-tasks/${task.taskRef.taskId}/report`)
  }
  for (const state of ['FAILED', 'CANCELLED']) {
    await page.route(`**/api/v1/analysis-tasks/${task.taskRef.taskId}`, route => route.fulfill({ json: { ...task, state, reportRef: null, errorCode: state } }))
    await page.getByRole('button', { name: '重新查询状态', exact: true }).click(); await expect(page.getByRole('heading', { name: '供需与补货分析' })).toHaveCount(0)
    await page.unroute(`**/api/v1/analysis-tasks/${task.taskRef.taskId}`)
  }
  const blocked = structuredClone(source)
  blocked.completeness = 'BLOCKED'; blocked.dataReport.supplyDemand.baseline = null; blocked.dataReport.supplyDemand.candidates = []; blocked.dataReport.quality = [{ code: 'PROTOCOL_MISSING_INPUT', path: 'demand', severity: 'BLOCK' }]
  blocked.analysisReport.ai = { status: 'NOT_ATTEMPTED' }
  await page.route(`**/api/v1/analysis-tasks/${task.taskRef.taskId}/report`, route => route.fulfill({ json: blocked }))
  await page.getByRole('button', { name: '重新查询状态', exact: true }).click()
  await expect(page.getByText('基线不可计算', { exact: true })).toBeVisible(); await expect(page.getByText('PROTOCOL_MISSING_INPUT', { exact: true })).toBeVisible()
  await expect(page.locator('.token-grid')).toContainText('未知')
  await page.unroute(`**/api/v1/analysis-tasks/${task.taskRef.taskId}/report`)
  for (const status of [404, 409, 422, 503, 403, 401]) {
    await page.route('**/api/v1/s01/options', route => route.fulfill({ status, json: { code: 'PROTOCOL_TEST' } }))
    // This uses an explicit retry, never silently turns an error into a success.
    await page.reload(); await expect(page.getByRole('alert')).toContainText('PROTOCOL_TEST')
    await page.unroute('**/api/v1/s01/options')
  }
  await page.route('**/api/v1/s01/options', route => route.fulfill({ json: { scenarioId: 'S01_BACKEND', mappedChoices: [], limitations: [] } }))
  await page.reload(); await page.getByRole('navigation', { name: '主要导航' }).getByRole('link', { name: /补货建议/ }).click(); await expect(page.getByText('无符合条件的授权包')).toBeVisible(); await expect(page.getByRole('button', { name: '＋ 新建补货分析' })).toBeDisabled()
})

test('PROTOCOL FIXTURES: polling is bounded, stops on denial; exact-scope pagination and keyboard', async ({ page }) => {
  await login(page)
  const reportPromise = complete(page); const { task } = await create(page); await reportPromise
  let count = 0
  await page.clock.install()
  await page.route(`**/api/v1/analysis-tasks/${task.taskRef.taskId}`, route => { count++; return route.fulfill({ json: { ...task, state: 'RUNNING', reportRef: null } }) })
  await page.getByRole('button', { name: '重新查询状态', exact: true }).click()
  await expect(page.getByText('分析中', { exact: true })).toBeVisible()
  for (let i = 1; i <= 59; i++) {
    await page.clock.runFor(2000)
    await expect.poll(() => count).toBe(i + 1)
    await expect(page.getByText('分析中', { exact: true })).toBeVisible()
  }
  await expect(page.getByText(/本次自动查询已到上限/)).toBeVisible()
  await page.clock.runFor(20000); expect(count).toBe(60)
  await page.unroute(`**/api/v1/analysis-tasks/${task.taskRef.taskId}`)
  await page.route(`**/api/v1/analysis-tasks/${task.taskRef.taskId}`, route => { count++; return route.fulfill({ status: 403, json: { code: 'POLICY_DENIED' } }) })
  await page.getByRole('button', { name: '重新查询状态', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('POLICY_DENIED')
  const deniedCount = count; await page.clock.runFor(20000); expect(count).toBe(deniedCount)
  await page.unroute(`**/api/v1/analysis-tasks/${task.taskRef.taskId}`)
  await page.clock.resume()
  await page.getByRole('button', { name: '重新核对会话与选项' }).click()
  await expect(page.getByText('可信会话 · 已连接')).toBeVisible()
  await page.getByRole('navigation', { name: '主要导航' }).getByRole('link', { name: /补货建议/ }).click()
  let calls: string[] = []
  await page.route('**/api/v1/analysis-tasks?**', route => { calls.push(route.request().url()); return route.fulfill({ json: { items: [task], nextCursor: new URL(route.request().url()).searchParams.has('before') ? null : 'bounded-cursor' } }) })
  await page.getByRole('combobox', { name: '当前包 / 精确历史范围', exact: true }).selectOption(session.casePackages[0].packageRef)
  await page.getByRole('button', { name: '刷新历史', exact: true }).click()
  await page.getByRole('button', { name: '下一页', exact: true }).click()
  await expect(page.getByRole('button', { name: '下一页', exact: true })).toBeDisabled()
  const next = new URL(calls.at(-1)!)
  expect(next.searchParams.get('before')).toBe('bounded-cursor'); expect(next.searchParams.get('limit')).toBe('20')
  expect([...next.searchParams.keys()].sort()).toEqual(['before', 'canonicalSkuId', 'limit', 'scenarioId', 'storeId', 'warehouseId'])
  await page.getByRole('button', { name: '＋ 新建补货分析', exact: true }).focus()
  await page.keyboard.press('Enter'); await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '＋ 新建补货分析', exact: true })).toBeFocused()
  await page.getByRole('searchbox', { name: 'SKU 搜索' }).fill('no-such-authorized-sku')
  await expect(page.getByText('无符合条件的授权包')).toBeVisible()
  await expect(page.getByRole('table').locator('tbody tr')).toHaveCount(0)
})

test('REAL API + transport delay: task switch, closed dialog, logout and permission denial discard late evidence', async ({ page }) => {
  await login(page)
  const aReady = complete(page); const a = await create(page, 'A'); const reportA = await aReady
  await page.getByRole('navigation', { name: '主要导航' }).getByRole('link', { name: /补货建议/ }).click()
  const bReady = complete(page); const b = await create(page, 'B'); const reportB = await bReady
  // Test-only transport deliberately ignores Abort after a genuine authorized GET.
  // This verifies the production generation/binding guard, not merely fetch cancellation.
  await page.evaluate(() => {
    const state = { enabled: false, ready: false, finished: false, release: () => {} }
    ;(window as unknown as { evidenceDelay: typeof state }).evidenceDelay = state
    const original = window.fetch.bind(window)
    window.fetch = async (input, init) => {
      if (!state.enabled || !String(input).includes('/evidence/')) return original(input, init)
      state.enabled = false
      const response = await original(input, { ...init, signal: undefined })
      state.ready = true
      await new Promise<void>(resolve => { state.release = resolve })
      state.finished = true
      return response
    }
  })
  const gate = async () => {
    await page.evaluate(() => { const s = (window as unknown as { evidenceDelay: { enabled: boolean; ready: boolean; finished: boolean } }).evidenceDelay; s.enabled = true; s.ready = false; s.finished = false })
    await page.getByRole('button', { name: '查看证据', exact: true }).first().click()
    await expect.poll(() => page.evaluate(() => (window as unknown as { evidenceDelay: { ready: boolean } }).evidenceDelay.ready)).toBe(true)
    await expect(page.getByRole('dialog')).toContainText('正在核对当前读取权限')
  }
  const release = async () => {
    await page.evaluate(() => (window as unknown as { evidenceDelay: { release: () => void } }).evidenceDelay.release())
    await expect.poll(() => page.evaluate(() => (window as unknown as { evidenceDelay: { finished: boolean } }).evidenceDelay.finished)).toBe(true)
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(page.locator('.evidence-json')).toHaveCount(0)
  }
  // Switch while the modal is open by dispatching the real rendered history event;
  // native modal ordinarily prevents pointer access to the background table.
  await gate()
  await page.evaluate(() => { location.hash = '#suggestions' })
  const rowA = page.locator('tbody tr').filter({ hasText: a.task.taskRef.taskId.slice(0, 12) })
  await rowA.getByText(a.task.taskRef.taskId.slice(0, 12), { exact: true }).dispatchEvent('click')
  await expect(page.getByText(reportA.reportRef.reportId, { exact: true }).first()).toBeVisible()
  await release()
  await page.getByRole('button', { name: '查看证据', exact: true }).first().click()
  await expect(page.locator('.evidence-json')).toContainText('gapQuantity')
  await page.getByRole('button', { name: '关闭弹窗', exact: true }).click()
  await gate(); await page.getByRole('button', { name: '关闭弹窗', exact: true }).click(); await release()
  await gate(); await control('revokeRead')
  try {
    await page.getByRole('button', { name: '重新查询状态', exact: true }).dispatchEvent('click')
    await expect(page.getByRole('heading', { name: '供需与补货分析' })).toHaveCount(0)
    await release()
  } finally { await control('restoreRead') }
  await page.getByRole('button', { name: '重新核对会话与选项', exact: true }).click()
  await expect(page.getByText(reportA.reportRef.reportId, { exact: true }).first()).toBeVisible()
  await gate()
  await page.getByRole('button', { name: '退出会话', exact: true }).dispatchEvent('click')
  await release()
  await expect(page.getByText('尚未连接身份', { exact: true })).toBeVisible()
  expect(a.task.taskRef.taskId).not.toBe(b.task.taskRef.taskId)
  expect(reportA.reportRef).not.toEqual(reportB.reportRef)
})
