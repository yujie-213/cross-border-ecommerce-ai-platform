import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { reset, state } from '../../src/s01'
import { route } from '../../src/router'
import type { QualityRiskAdvisory, V2Item } from '../../src/api/v2'
import RiskNotice from '../../src/afterSales/RiskNotice.vue'
import WorkbenchPage from '../../src/pages/WorkbenchPage.vue'
import SuggestionsPage from '../../src/pages/SuggestionsPage.vue'
import SkuPage from '../../src/pages/SkuPage.vue'

const now = new Date('2026-11-16T13:00:00Z')
const risk = { riskId:'confirmed-risk', version:2, reason:'已核实接头松动', limitations:'仅本店本仓批次', sourceNature:'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP', validUntil:'2026-11-17T13:00:00Z' }
function advisory(status = 'MATCHED'): QualityRiskAdvisory {
  return { status, checkedAt:now.toISOString(), reason:status === 'UNVERIFIED' ? '风险未核实' : '', riskRefs:status === 'MATCHED' ? [{ ...risk }] : [] }
}
function item(key: string, status = 'MATCHED'): V2Item {
  return { entityKey:key, sku:key, name:'教学商品 '+key, sourceTenant:'synthetic-tenant', productId:key,
    storeId:'own-store', warehouseId:'own-warehouse', storeName:'自有店', sourceGrade:'RULE_CALCULATED',
    identityVerified:true, identityIssues:[], analysisState:'ANALYZED',
    quantity:28, inventory:{ available:4 }, uncertainties:[], warehouseName:'自有仓',
    decision:{ status:'REPLENISH', forecast:{ available:true, observedDays:7 }, referenceReplenishmentQuantity:25,
      horizonDays:14, leadDays:3, horizonBasis:'synthetic-test', forecastQuantity:'29', purchasableQuantity:28,
      confirmedSupplyQuantity:0, coverageDays:'2', firstShortageDate:'2026-11-18', stockoutRisk:true,
      confidence:'REFERENCE_ONLY', assumptions:[], explanation:[], baseline:null, scenarios:[] },
    procurementEligibility:{ eligible:key === 'eligible', hardBlocks:[], warnings:[] }, qualityRiskAdvisory:advisory(status) }
}
const render = (component: Parameters<typeof h>[0], props = {}) => renderToString(createSSRApp({ render:() => h(component, props) }))
beforeEach(() => {
  vi.useFakeTimers(); vi.setSystemTime(now); reset(); state.busy = false
  route.value = { path:'/sku/eligible', segments:['sku','eligible'], query:{ batch:'batch-one' } }
})
afterEach(() => vi.useRealTimers())

it('keeps just the analysis link in each workbench action area regardless of procurement eligibility', async () => {
  state.batchId = 'batch-one'
  state.progress = { task:{ state:'SUCCEEDED' }, summary:{ discoveredSkuCount:2, scopeObjectCount:2 } } as never
  state.priority = [item('eligible'), item('no-quote')]
  const html = await render(WorkbenchPage)
  const actions = [...html.matchAll(/<div class="attention-next">(.*?)<\/div>/g)].map(match => match[1])
  expect(actions).toEqual(['<b>分析商品 →</b>', '<b>分析商品 →</b>'])
  expect(html).not.toContain('先分析需求'); expect(html).not.toContain('核实后人工请购')
})

it('never decorates product-list rows with either a confirmed risk or an unverified warning', async () => {
  state.batchId = 'batch-one'
  state.list = { total:2, items:[item('eligible'), item('unverified','UNVERIFIED')], stores:[], warehouses:[] }
  const html = await render(SuggestionsPage)
  expect((html.match(/分析商品 →/g) || []).length).toBe(2)
  expect(html).not.toContain('售后'); expect(html).not.toContain('quality-risk')
  expect(state.list.items[0].qualityRiskAdvisory?.status).toBe('MATCHED')
})

it('places one current reminder inside the individual replenishment analysis with its evidence link', async () => {
  state.item = item('eligible'); state.itemKey = 'eligible'
  const html = await render(SkuPage)
  expect((html.match(/售后质量风险提醒/g) || []).length).toBe(1)
  expect(html.indexOf('class="decision-main"')).toBeLessThan(html.indexOf('售后质量风险提醒'))
  expect(html).toContain('已核实接头松动'); expect(html).toContain('已人工确认')
  expect(html).toContain('id=confirmed-risk'); expect(html).toContain('returnTo=')
})

it('renders nothing when there is no advisory or no matching confirmed risk', async () => {
  expect(await render(RiskNotice)).not.toContain('售后')
  expect(await render(RiskNotice,{ advisory:advisory('NONE') })).not.toContain('售后')
})

it('separates an unverified lookup status from the yellow business-risk reminder', async () => {
  const html = await render(RiskNotice,{ advisory:advisory('UNVERIFIED') })
  expect(html).toContain('role="status"'); expect(html).toContain('当前状态未核实')
  expect(html).not.toContain('<aside'); expect(html).not.toContain('售后质量风险提醒')
  expect(html).not.toContain('无风险')
})

it.each(['2026-11-16T12:59:00Z', 'invalid-time', '2026-11-16T13:01:00Z'])('does not present an unchecked snapshot as a current risk (%s)', async checkedAt => {
  const html = await render(RiskNotice,{ advisory:{ ...advisory(), checkedAt } })
  expect(html).toContain('当前状态未核实'); expect(html).not.toContain('已核实接头松动')
  expect(html).not.toContain('<aside')
})

it('stops showing an expired risk even while the lookup itself is still fresh', async () => {
  const current = advisory(); current.riskRefs[0].validUntil = now.toISOString()
  const html = await render(RiskNotice,{ advisory:current })
  expect(html).not.toContain('<aside'); expect(html).not.toContain('售后质量风险提醒')
})

it('keeps a revoked historical reference collapsed and separate from current reminders', async () => {
  const html = await render(RiskNotice,{ advisory:advisory('NONE'), history:advisory() })
  expect(html).toContain('<details'); expect(html).toContain('分析时保存的历史风险')
  expect(html).not.toContain('售后质量风险提醒'); expect(html).not.toContain('<aside')
})

it('retains the teaching label on explicitly authorized middleware demonstrations', async () => {
  const current = advisory(); current.riskRefs[0].sourceNature = 'MIDDLEWARE_TEACHING_DATA'
  expect(await render(RiskNotice,{ advisory:current })).toContain('教学风险演示')
})
