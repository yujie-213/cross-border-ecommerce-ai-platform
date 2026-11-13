import { describe, it, expect } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ReportDetail from '../../src/components/ReportDetail.vue'
import type { Report } from '../../src/api/types'

function fixture(wholeCarton: boolean, candidate = true): Report {
  const baseline = { availableQuantity: '6', inTransitQuantity: '0', targetQuantity: '50.14285722', gapQuantity: '44.14285722',
    firstShortageDate: '2026-11-15', stockoutRisk: true, closingBalance: '-44.14285722', averageDailyDemand: '5.57142858', series: [] }
  return { scope: { canonicalSkuIds: ['fixture'], storeIds: ['store'], warehouseIds: ['warehouse'] }, completeness: 'RULES_ONLY',
    sourceNature: 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP', taskRef: { taskId: 'task' }, reportRef: { reportId: 'report' },
    dataReport: { quality: [], evidence: [], scenarioSupplement: { monitoring: { datasetId: 'fixture', scopeVersion: 1 } },
      supplyDemand: { baseline, candidates: candidate ? [{ candidateId: 'candidate', quantity: wholeCarton ? '48' : '45', availableDate: '2026-11-15', constraintVersion: 'fixture-carton-v1', evaluation: { ...baseline, firstShortageDate: null, stockoutRisk: false } }] : [], limitations: [] },
      forecast: { windowStart: '2026-11-06', windowEnd: '2026-11-12', timezone: 'UTC+08:00', observationDays: 7, totalSales: '39',
        averageDailyDemand: '5.57142858', forecastDays: 7, forecastQuantity: '39', leadDays: 2, coverageDays: 7, calculationHorizonDays: 9,
        dailySales: [], excludedSupply: [], stockReconciliation: { openingQuantity: '45', fulfilledQuantity: '39', availableQuantity: '6', status: 'PASS' },
        constraints: { quoteVersion: 1, moq: '12', orderMultiple: wholeCarton ? '8' : null, ...(wholeCarton ? { wholeCartonRequired: true, ruleVersion: 's01-whole-carton-v1', moqSource: 'supplier-quotes.minimum_quantity', orderMultipleSource: 'products.default_carton_qty' } : {}) } } },
    analysisReport: { ai: { status: 'NOT_ATTEMPTED' } } } as unknown as Report
}
const render = (report: Report) => renderToString(createSSRApp({ render: () => h(ReportDetail, { report }) }))

describe('whole-carton report presentation', () => {
  it('shows 48 pieces as six cartons with both ERP constraint sources and remaining conditions', async () => {
    const html = await render(fixture(true))
    expect(html).toContain('48 <small>件')
    expect(html).toContain('6 箱')
    expect(html).toContain('8 件/箱')
    expect(html).toContain('supplier-quotes.minimum_quantity')
    expect(html).toContain('products.default_carton_qty')
    expect(html).toContain('s01-whole-carton-v1')
    expect(html).toContain('未覆盖采集当日剩余需求')
    expect(html).toContain('审批、到货质检')
    expect(html).not.toContain('旧规则候选已失效')
  })
  it('marks pre-rule history obsolete and removes its 45-piece candidate card', async () => {
    const html = await render(fixture(false))
    expect(html).toContain('历史规则报告 · 采购候选已失效')
    expect(html).toContain('历史解释与模型用量（旧规则）')
    expect(html).toContain('旧规则候选已失效')
    expect(html).not.toContain('class="big"')
  })
  it('does not invent a zero or MOQ order when there is no candidate', async () => {
    const html = await render(fixture(true, false))
    expect(html).toContain('未生成补货候选')
    expect(html).not.toContain('class="big"')
    expect(html).not.toContain('旧规则候选已失效')
  })
})
