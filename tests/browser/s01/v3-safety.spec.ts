import { test, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { mkdirSync, writeFileSync } from 'node:fs'
import path from 'node:path'

/**
 * Safety and state-isolation checks for the V3 workspace.
 * Requisition writes and single analyses are mocked at the network boundary:
 * no ERP call, no model call, no procurement write.
 */
const root = path.resolve(import.meta.dirname, '../../..')
const screenshots = path.join(root, 'docs/evidence/S01-V3/screenshots')
const password = process.env.S01_LOCAL_PASSWORD || ''
const skip = () => test.skip(process.env.S01_V3_BROWSER !== 'true', 'Explicit local platform + password required')

const item = (over: Record<string, unknown> = {}) => ({
  entityKey: 'mock-key-1', sourceTenant: '1', productId: '9001', sku: 'MOCK-SKU-1', name: '模拟测试商品',
  storeId: '2', warehouseId: '3', storeName: 'MIMI Apparel Online', warehouseName: '美西仓',
  identityVerified: true, identityIssues: [], analysisState: 'ANALYZED', sourceGrade: 'RULE_CALCULATED',
  quantity: 48, sourceQuantity: 48, unit: 'EA',
  inventory: { available: 6 }, observedAt: '2026-11-14T04:03:00', snapshotRef: 'snapshot-mock',
  riskGroup: 'RULE_CONFIRMED', riskDate: '2026-11-15', uncertainties: [],
  constraints: {
    moq: 12, orderMultiple: 8, unitPrice: '2.40', currency: 'USD', minimumAmount: '28.80',
    supplierId: '7', supplierName: '示例供应商', quoteNo: 'QT-1', quoteValidFrom: '2026-11-10',
    quoteValidTo: '2026-12-13', quoteId: '11', hardBlocks: []
  },
  procurementEligibility: { eligible: true, hardBlocks: [], warnings: [], scopeAuthorized: true },
  formalPurchases: [],
  dataQuality: {
    identity: { status: 'VERIFIED', reasons: [] }, demand: { status: 'VERIFIED', reasons: [] },
    inventory: { status: 'VERIFIED', reasons: [] }, procurement: { status: 'VERIFIED', reasons: [] }
  },
  capabilities: {
    facts: { enabled: true, reasons: [] }, reference: { enabled: true, reasons: [] }, risk: { enabled: true, reasons: [] },
    rules: { enabled: true, reasons: [] }, requisition: { enabled: true, reasons: [] }
  },
  recoveryHints: [],
  ...over
})

const singleBody = (taskId: string, over: Record<string, unknown> = {}) => ({
  task: {
    taskRef: { tenantId: 's01-v2-teaching-local', taskId }, state: 'SUCCEEDED', revision: 2,
    planVersion: 's01-v2', reportRef: { tenantId: 's01-v2-teaching-local', reportId: 'mock-report' },
    scenarioId: 'S01_V2_SINGLE', deadline: '2026-11-14T05:00:00Z', errorCode: null,
    sourceNature: 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'
  },
  report: {
    dataReport: { item: item(over) },
    analysisReport: {
      ai: { status: 'NOT_ATTEMPTED', reason: 'MODEL_NOT_ENABLED', explanation: null, usage: null }
    }
  }
})

const requisitionBody = (finalQuantity = 48) => ({
  operationId: 'op-mock', reportId: 'mock-report', state: 'SUBMITTED',
  erpId: '9001', erpNumber: 'S01-RQ-mock', erpStatus: '待审核',
  aiQuantity: '48', finalQuantity, adjustmentReason: '', errorCode: null,
  verifiedAt: '2026-11-14T05:10:00Z', queryPath: '/mock', resultMeaning: '已提交'
})

async function login(page) {
  await page.goto('/')
  await page.getByLabel('账号').fill('admin')
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.locator('.kpi-row')).toBeVisible({ timeout: 45000 })
}

test('V3 SAFETY: an unknown requisition blocks new submissions and only its own key may replay', async ({ page }) => {
  skip()
  test.setTimeout(120000)
  mkdirSync(screenshots, { recursive: true })
  await login(page)

  await page.route('**/api/v1/s01/v2/batches/*/items/mock-key-1', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(item()) }))
  await page.route('**/api/v1/s01/v2/singles/mock-single-1', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(singleBody('mock-single-1')) }))
  await page.route('**/api/v1/s01/v2/singles/mock-single-1/requisition', route => route.fulfill({ status: 200, contentType: 'application/json', body: 'null' }))

  const aborted: string[] = []
  await page.route('**/api/v1/s01/v2/singles/mock-single-1/requisition', async route => {
    if (route.request().method() !== 'POST') return route.fulfill({ status: 200, contentType: 'application/json', body: 'null' })
    aborted.push(route.request().headers()['idempotency-key'] || '')
    await route.abort('failed')            // request left the browser, outcome unknown
  })

  await page.goto('/#/suggestions')
  await page.waitForTimeout(1500)
  const batch = await page.evaluate(() => new URLSearchParams(location.hash.split('?')[1] || '').get('batch') || '')
  await page.goto(`/#/sku/mock-key-1?batch=${batch}&single=mock-single-1`)
  await expect(page.locator('.verdict')).toContainText('规则建议')

  await expect(page.getByLabel('最终采购数量')).toHaveValue('48')
  await page.getByRole('checkbox').check()
  await expect(page.getByRole('button', { name: '提交请购', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: '提交请购', exact: true }).click()
  await expect(page.locator('.actionbar')).toContainText('上一笔结果未确认', { timeout: 20000 })
  const firstKey = aborted[0]
  expect(firstKey && firstKey.length > 10).toBe(true)

  // The form must be gone: only the original command can be checked.
  await expect(page.getByRole('button', { name: '提交请购', exact: true })).toHaveCount(0)
  await expect(page.locator('.actionbar')).toContainText('使用原命令核对')

  // Cross-SKU isolation: the same pending command must not appear on another analysis.
  await page.route('**/api/v1/s01/v2/batches/*/items/mock-key-2', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(item({ entityKey: 'mock-key-2', sku: 'MOCK-SKU-2' })) }))
  await page.route('**/api/v1/s01/v2/singles/mock-single-2', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(singleBody('mock-single-2', { entityKey: 'mock-key-2', sku: 'MOCK-SKU-2' })) }))
  await page.route('**/api/v1/s01/v2/singles/mock-single-2/requisition', route => route.fulfill({ status: 200, contentType: 'application/json', body: 'null' }))
  await page.goto(`/#/sku/mock-key-2?batch=${batch}&single=mock-single-2`)
  await expect(page.locator('.verdict')).toContainText('规则建议')
  await expect(page.locator('.actionbar')).toContainText('提交请购')
  await expect(page.locator('.actionbar')).not.toContainText('使用原命令核对')
  await expect(page.getByText('另一个 SKU（MOCK-SKU-1）')).toBeVisible()
  await page.screenshot({ path: path.join(screenshots, '11-pending-other-sku-1440.png'), fullPage: false })

  // Back on the original analysis the replay must reuse the same idempotency key.
  const replayed: string[] = []
  await page.unroute('**/api/v1/s01/v2/singles/mock-single-1/requisition')
  await page.route('**/api/v1/s01/v2/singles/mock-single-1/requisition', async route => {
    if (route.request().method() !== 'POST') return route.fulfill({ status: 200, contentType: 'application/json', body: 'null' })
    replayed.push(route.request().headers()['idempotency-key'] || '')
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(requisitionBody()) })
  })
  await page.goto(`/#/sku/mock-key-1?batch=${batch}&single=mock-single-1`)
  await expect(page.locator('.actionbar')).toContainText('使用原命令核对')
  await page.screenshot({ path: path.join(screenshots, '10-pending-unknown-1440.png'), fullPage: false })
  await page.locator('.actionbar').getByRole('button', { name: '使用原命令核对', exact: true }).click()
  await expect(page.locator('.actionbar')).toContainText('待 ERP 审批', { timeout: 15000 })
  expect(replayed[0]).toBe(firstKey)
  await expect(page.getByRole('button', { name: '提交请购', exact: true })).toHaveCount(0)

  writeFileSync(path.join(root, 'docs/evidence/S01-V3/safety-result.json'), JSON.stringify({
    result: 'PASS', reusedIdempotencyKey: replayed[0] === firstKey, blockedSecondSubmit: true, crossSkuIsolated: true
  }, null, 2))
})

test('V3 URL: a new single analysis is written to the URL and survives reload and back', async ({ page }) => {
  skip()
  test.setTimeout(120000)
  mkdirSync(screenshots, { recursive: true })
  await login(page)

  const taskId = 'mock-created-single'
  await page.route('**/api/v1/s01/v2/batches/*/items/mock-key-3', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify(item({
      entityKey: 'mock-key-3', sku: 'MOCK-SKU-3', quantity: null,
      analysisState: 'HISTORICAL_REFERENCE', sourceGrade: 'HISTORICAL_REFERENCE',
      procurementEligibility: { eligible: false, hardBlocks: ['NO_POSITIVE_RECOMMENDATION_BASIS'], warnings: [], scopeAuthorized: true }
    }))
  }))
  await page.route('**/api/v1/s01/v2/singles', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    return route.fulfill({ status: 202, contentType: 'application/json', body: JSON.stringify({ taskRef: { tenantId: 's01-v2-teaching-local', taskId }, state: 'QUEUED', revision: 1, planVersion: 's01-v2', reportRef: null, scenarioId: 'S01_V2_SINGLE', deadline: '2026-11-14T05:00:00Z', errorCode: null, sourceNature: 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP' }) })
  })
  await page.route(`**/api/v1/s01/v2/singles/${taskId}`, route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(singleBody(taskId, { entityKey: 'mock-key-3', sku: 'MOCK-SKU-3' })) }))
  await page.route(`**/api/v1/s01/v2/singles/${taskId}/requisition`, route => route.fulfill({ status: 200, contentType: 'application/json', body: 'null' }))

  await page.goto('/#/suggestions')
  await page.waitForTimeout(1500)
  const batch = await page.evaluate(() => new URLSearchParams(location.hash.split('?')[1] || '').get('batch') || '')
  await page.goto(`/#/sku/mock-key-3?batch=${batch}`)
  await expect(page.locator('.verdict')).toContainText('未形成')

  await page.locator('.ai-head').getByRole('button', { name: '生成 AI 解读', exact: true }).click()
  await expect(page).toHaveURL(new RegExp(`single=${taskId}`), { timeout: 20000 })
  await expect(page.locator('.verdict')).toContainText('规则建议')
  await expect(page.getByText('含单品分析结果')).toBeVisible()

  await page.reload()
  await expect(page).toHaveURL(new RegExp(`single=${taskId}`), { timeout: 20000 })
  await expect(page.locator('.verdict')).toContainText('规则建议', { timeout: 20000 })

  await page.goBack()
  await expect(page).not.toHaveURL(/single=/)
  await expect(page.locator('.verdict')).toContainText('未形成', { timeout: 20000 })
  await page.screenshot({ path: path.join(screenshots, '12-url-single-sync-1440.png'), fullPage: false })
})

test('V3 ISOLATION: the workbench queue ignores list filters and paging', async ({ page }) => {
  skip()
  test.setTimeout(150000)
  await login(page)

  const firstQueue = async () => (await page.locator('.qrow .qname small').first().innerText()).split(' ')[0]
  const before = await firstQueue()
  const totalBefore = await page.locator('.qrow').count()
  expect(totalBefore).toBeGreaterThan(0)

  // Filtered AND paged: page 2 of ERP references (a subset, not the batch order).
  await page.goto('/#/suggestions?source=REFERENCE_ONLY&offset=50')
  await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 40000 })
  await expect(page.locator('.table-foot span').first()).toContainText('第 2')

  await page.goto('/#/workbench')
  await page.waitForTimeout(6000)
  expect(await page.locator('.qrow').count()).toBe(totalBefore)
  expect(await firstQueue()).toBe(before)
  await page.screenshot({ path: path.join(screenshots, '13-workbench-after-filter-1440.png'), fullPage: false })
})

test('V3 LAYOUT: 1440 / 1080 / 820 keep the reviewed composition layout', async ({ page }) => {
  skip()
  test.setTimeout(150000)
  mkdirSync(screenshots, { recursive: true })
  await login(page)

  for (const [width, height, tag] of [[1440, 960, '1440'], [1080, 960, '1080'], [820, 900, '820']] as const) {
    await page.setViewportSize({ width, height })
    await page.goto('/#/workbench')
    await page.waitForTimeout(5000)
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0)
    /** KPI and composition share a row from 1080 up, stack below 1000. */
    const stacked = await page.evaluate(() => {
      const kpi = document.querySelector('.kpi-panel')?.getBoundingClientRect()
      const compose = document.querySelector('.compose-panel')?.getBoundingClientRect()
      return !!kpi && !!compose && compose.top > kpi.bottom - 1
    })
    if (width >= 1000) expect(stacked, `KPI and composition must share a row at ${width}`).toBe(false)
    else expect(stacked, `KPI and composition must stack at ${width}`).toBe(true)
    await page.screenshot({ path: path.join(screenshots, `14-workbench-${tag}.png`), fullPage: false })
  }
})

test('V3 LEDGER: a read failure is reported as a failure, never as "no records"', async ({ page }) => {
  skip()
  test.setTimeout(90000)
  await login(page)

  await page.route('**/api/v1/s01/v2/singles/*/requisition', route =>
    route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ code: 'UPSTREAM_UNAVAILABLE' }) }))

  await page.goto('/#/requisitions')
  await expect(page.getByRole('heading', { name: '请购管理', exact: true })).toBeVisible()
  await expect(page.getByText(/条请购状态读取失败/)).toBeVisible({ timeout: 30000 })
  await expect(page.locator('.empty-inline')).toContainText('读取失败')
  await expect(page.getByText('当前范围内没有已保存的请购记录。')).toHaveCount(0)
  await page.screenshot({ path: path.join(screenshots, '15-ledger-read-failure-1440.png'), fullPage: false })
})
