import { describe, it, expect } from 'vitest'
import { createBody } from '../../src/api/client'
import { choiceKey, matchesReport } from '../../src/domain'
import type { Choice, Report } from '../../src/api/types'

const choice: Choice = { choiceRef: 'online-scope', inputMode: 'ONLINE_TEACHING_ERP', sourceMode: 'ONLINE_TEACHING_ERP', asOf: null,
  sourceNature: 'TEACHING_ERP_OBSERVED', scope: { tenantId: 'fixture', storeIds: ['store'], warehouseIds: ['warehouse'], canonicalSkuIds: ['sku'], fields: ['quantity'] } }
describe('online commands and historical scope', () => {
  it('creates an authorized online command without a catalog, source facts or tenant supplied by the browser', () => {
    const body = createBody(choice)
    expect(body.parameters).toEqual({ inputMode: 'ONLINE_TEACHING_ERP' })
    expect(body.scope).toEqual({ storeIds: ['store'], warehouseIds: ['warehouse'], canonicalSkuIds: ['sku'], fields: ['quantity'] })
    expect(choiceKey(choice)).toBe('online-scope')
  })
  it('matches a report after MySQL reorders JSON keys and rejects a different SKU', () => {
    const report = { scope: { fields: ['quantity'], warehouseIds: ['warehouse'], canonicalSkuIds: ['sku'], tenantId: 'fixture', storeIds: ['store'] },
      dataReport: { scenarioSupplement: { inputMode: 'ONLINE_TEACHING_ERP' } } } as Report
    expect(matchesReport(choice, report)).toBe(true)
    expect(matchesReport({ ...choice, scope: { ...choice.scope, canonicalSkuIds: ['outside'] } }, report)).toBe(false)
  })
})
