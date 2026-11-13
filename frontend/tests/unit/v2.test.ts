import { describe, it, expect } from 'vitest'
import { quantityError, sourceLabel, stateLabel, type V2Item } from '../../src/api/v2'
const reference = { sourceGrade: 'REFERENCE_ONLY', quantity: 120, constraints: { moq: 12, orderMultiple: 8 } } as V2Item
describe('V2 source and human quantity policy', () => {
  it('keeps ERP reference distinct and permits compliant human quantities', () => {
    expect(sourceLabel(reference.sourceGrade)).toBe('ERP 参考建议')
    expect(quantityError(reference, 120, '')).toBe('')
    expect(quantityError(reference, 128, '业务需求调整')).toBe('')
  })
  it('requires MOQ, whole cartons and an adjustment reason', () => {
    expect(quantityError(reference, 8, '调整')).not.toBe('')
    expect(quantityError(reference, 121, '调整')).not.toBe('')
    expect(quantityError(reference, 128, '')).toContain('原因')
    expect(quantityError(reference, 120.5, '调整')).not.toBe('')
  })
  it('does not label unresolved or zero-source records as no replenishment', () => {
    expect(stateLabel('NEEDS_REVIEW')).toBe('需要核实')
    expect(stateLabel('NO_REPLENISHMENT')).toBe('规则判断无需补货')
    expect(sourceLabel('UNAVAILABLE')).toBe('无可用来源')
  })
})
