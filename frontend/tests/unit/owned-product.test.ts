import { afterEach, describe, expect, it } from 'vitest'
import { latestBatchId, state, stageOf } from '../../src/s01'
import type { V2Item, V2Options } from '../../src/api/v2'

afterEach(() => { state.options = null; state.batches = [] })

describe('registered owned product navigation', () => {
  it('never auto-opens old shared reports when no owned report exists', () => {
    state.options = { analysisRange: 'OWNED_REGISTERED' } as V2Options
    state.batches = [{ taskRef: { taskId: 'shared' }, state: 'SUCCEEDED', analysisRange: 'LEGACY_SHARED' }] as never
    expect(latestBatchId()).toBe('')
    state.batches.push({ taskRef: { taskId: 'owned' }, state: 'SUCCEEDED', analysisRange: 'OWNED_REGISTERED' } as never)
    expect(latestBatchId()).toBe('owned')
  })
  it('presents a positive reference gap even without a purchasable candidate', () => {
    const item = { analysisState: 'ANALYZED', sourceGrade: 'PLATFORM_REFERENCE', quantity: null,
      decision: { status: 'REPLENISH', referenceReplenishmentQuantity: 45 } } as V2Item
    expect(stageOf(item)).toBe('confirm')
    expect(item.quantity).toBeNull()
  })
})
