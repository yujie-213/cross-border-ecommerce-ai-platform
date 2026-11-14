import { describe, it, expect } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import HistoricalSalesReference from '../../src/components/HistoricalSalesReference.vue'
import { stateLabel, sourceLabel, type V2Item } from '../../src/api/v2'

describe('usable historical reference without a purchase quantity', () => {
  it.each([['HL-CBL100-2M', 6, '5.571428571', '39'], ['HL-MUG350-WH', 81, '2.714285714', '19']])('shows %s current stock and explicitly historical sales', async (sku, available, average, total) => {
    const item = { sku, unit: 'EA', quantity: null, inventory: { available }, inventoryBasis: { status: 'VERIFIED' },
      demandWindow: { sampleStart: '2026-11-06', sampleEnd: '2026-11-12', referenceDays: 7, referenceAverage: average,
        windowStart: '2026-11-07', windowEnd: '2026-11-13', validDays: 6, missingDays: 1, referenceGrade: 'OBSERVED_STATUS_ONLY',
        observedHistory: [{ businessDate: '2026-11-12', quantity: total, orderRef: 'synthetic' }] }, recoveryHints: [] } as unknown as V2Item
    const html = await renderToString(createSSRApp({ render: () => h(HistoricalSalesReference, { item }) }))
    expect(html).toContain('历史销量参考分析')
    expect(html).toContain(`当前ERP可用库存 ${available}`)
    expect(html).toContain('有效样本 6 日，待核实 1 日')
    expect(html).toContain('不冒充当前7日SMA')
    expect(html).toContain('不生成采购数量')
    expect(html).not.toContain('无法分析')
  })
  it('distinguishes history from ERP reference and old unavailable reports', () => {
    expect(stateLabel('HISTORICAL_REFERENCE')).toBe('历史参考分析')
    expect(sourceLabel('HISTORICAL_REFERENCE')).toBe('历史销量参考')
    expect(stateLabel('UNANALYZABLE')).toBe('无法分析')
    expect(sourceLabel('REFERENCE_ONLY')).toBe('ERP 参考建议')
  })
})
