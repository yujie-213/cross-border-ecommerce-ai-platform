import { describe, expect, it } from 'vitest'
import { fmt, stageOf, STAGE_LABEL, unitOf, requisitionCategory } from '../../src/s01'
import type { V2Item } from '../../src/api/v2'

const base = (over: Partial<V2Item>): V2Item => ({
  entityKey: 'k', sourceTenant: '1', productId: null, sku: 'SKU-1', name: '商品',
  storeId: null, warehouseId: null, storeName: null, warehouseName: null,
  identityVerified: true, identityIssues: [], analysisState: 'ANALYZED', sourceGrade: 'RULE_CALCULATED',
  quantity: 10, uncertainties: [], ...over
})

describe('S01 V3 presentation rules', () => {
  it('maps every analysis state to a stage without inventing a new one', () => {
    expect(stageOf(base({ analysisState: 'ANALYZED' }))).toBe('confirm')
    expect(stageOf(base({ analysisState: 'ERP_REFERENCE', sourceGrade: 'REFERENCE_ONLY' }))).toBe('confirm')
    expect(stageOf(base({ analysisState: 'HISTORICAL_REFERENCE', sourceGrade: 'HISTORICAL_REFERENCE', quantity: null }))).toBe('history')
    expect(stageOf(base({ analysisState: 'NO_REPLENISHMENT' }))).toBe('none')
    expect(stageOf(base({ analysisState: 'NEEDS_REVIEW' }))).toBe('review')
    expect(stageOf(base({ analysisState: 'UNANALYZABLE' }))).toBe('review')
    expect(stageOf(base({ analysisState: 'FAILED' }))).toBe('broken')
    expect(stageOf(base({ analysisState: 'PENDING' }))).toBe('pending')
    expect(stageOf(base({ analysisState: 'SOMETHING_NEW' }))).toBe('review')
    for (const stage of ['confirm', 'history', 'review', 'none', 'broken', 'pending'] as const) {
      expect(STAGE_LABEL[stage]).toBeTruthy()
    }
  })

  it('never presents a historical reference as a replenishment quantity', () => {
    const item = base({ analysisState: 'HISTORICAL_REFERENCE', sourceGrade: 'HISTORICAL_REFERENCE', quantity: null })
    expect(item.quantity).toBeNull()
    expect(stageOf(item)).toBe('history')
  })

  it('formats exact backend decimals for operators', () => {
    expect(fmt('1.0769230752662721918980427816953187973918172347818', 1)).toBe('1.1')
    expect(fmt('50.14285722', 0)).toBe('50')
    expect(fmt('0', 0)).toBe('0')
    expect(fmt(null)).toBe('—')
    expect(fmt('')).toBe('—')
    expect(fmt('not-a-number')).toBe('not-a-number')
  })

  it('keeps zero stock as a number and unknown stock as a dash', () => {
    expect(unitOf(base({ unit: 'EA' }))).toBe('件')
    expect(unitOf(base({ unit: null }))).toBe('件')
  })

  it('classifies requisitions by platform state, never guessing ERP approval', () => {
    const rq = (state: string, erpStatus: string | null = null) => ({ state, erpStatus } as never)
    expect(requisitionCategory(null)).toBe('draft')
    expect(requisitionCategory(rq('CREATED'))).toBe('draft')
    expect(requisitionCategory(rq('SUBMITTED', '待审核'))).toBe('pending')
    expect(requisitionCategory(rq('SUBMITTED', null))).toBe('pending')
    expect(requisitionCategory(rq('SUBMITTED', '审批通过'))).toBe('approved')
    expect(requisitionCategory(rq('SUBMITTED', '已审批'))).toBe('approved')
    expect(requisitionCategory(rq('SUBMITTED', '审核中'))).toBe('pending')
    expect(requisitionCategory(rq('SUBMIT_UNKNOWN', '待审核'))).toBe('unknown')
    expect(requisitionCategory(rq('CREATE_UNKNOWN'))).toBe('unknown')
    expect(requisitionCategory(rq('BLOCKED'))).toBe('blocked')
  })
})
