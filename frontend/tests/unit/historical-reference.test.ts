import { describe, it, expect } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import HistoricalSalesReference from '../../src/components/HistoricalSalesReference.vue'
import { stateLabel, sourceLabel, type V2Item } from '../../src/api/v2'
import { readFileSync } from 'node:fs'

// Whitelisted real read-only API captures, not fabricated business fixtures.
const captured = JSON.parse(readFileSync(new URL('../../../docs/evidence/S01-TWO-SKU-FIX/api-worker.json', import.meta.url), 'utf8')) as { results: { sku: string; item: V2Item }[] }

describe('usable historical reference without a purchase quantity', () => {
  it.each(captured.results.map((r: { sku: string; item: V2Item }) => [r.sku, r.item] as const))('shows %s current stock and explicitly historical sales', async (_sku, item) => {
    const available = item.inventory?.available
    expect(item.quantity).toBeNull()
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
