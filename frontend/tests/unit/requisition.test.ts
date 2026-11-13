import { describe, it, expect, vi, afterEach } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ReportDetail from '../../src/components/ReportDetail.vue'
import RequisitionPanel from '../../src/components/RequisitionPanel.vue'
import type { Report } from '../../src/api/types'

function report(): Report {
  return { sourceNature: 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP', completeness: 'RULES_ONLY',
    scope: { tenantId: 'fixture', storeIds: ['store'], warehouseIds: ['warehouse'], canonicalSkuIds: ['sku'] },
    taskRef: { taskId: 'task' }, reportRef: { tenantId: 'fixture', reportId: 'task' },
    dataReport: { quality: [], evidence: [], scenarioSupplement: {}, supplyDemand: { baseline: null, candidates: [], limitations: [] },
      existingPurchases: { policyVersion: 's01-approved-purchases-v1', coverage: 'COMPLETE_FILTERED_FORMAL_STATES', unresolvedScopeCount: 1,
        items: [{ erpId: '91', erpNumber: 'fixture-approved', lineIndex: 0, sku: 'sku', status: '待到货', orderedQuantity: '48', receivedQuantity: '16', unreceivedQuantity: '32', plannedArrival: '2026-11-15', sellableDate: null, includedInCalculation: false }] } },
    analysisReport: { ai: { status: 'NOT_ATTEMPTED' } } } as unknown as Report
}
afterEach(() => vi.unstubAllGlobals())
describe('formal purchases and narrow teaching request UI', () => {
  it('shows per-line receipts and unknown sellable time without treating remaining as transit', async () => {
    const html = await renderToString(createSSRApp({ render: () => h(ReportDetail, { report: report() }) }))
    expect(html).toContain('ERP 已审批正式采购')
    expect(html).toContain('采购 48 / 已收 16 / 未收 32 件')
    expect(html).toContain('可售日期 未知')
    expect(html).toContain('未抵扣供给')
    expect(html).toContain('无法确认店铺或销售备货用途')
    expect(html).not.toContain('待审核采购')
  })
  it('does not render a submit button or issue reads without explicit current capability', async () => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher)
    const html = await renderToString(createSSRApp({ render: () => h(RequisitionPanel, { report: report(), enabled: false }) }))
    expect(html).toContain('当前未开放请购提交')
    expect(html).not.toContain('确认并提交 ERP 请购')
    expect(fetcher).not.toHaveBeenCalled()
  })
})
