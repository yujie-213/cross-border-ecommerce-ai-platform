import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, createBody, errorText, request } from '../../src/api/client'
import { canReport, shown, terminal } from '../../src/domain'
import type { Choice, Task, TaskState } from '../../src/api/types'
const choice: Choice = { packageRef: 'fixed-package', sourceMode: 'TEACHING_SIMULATION', asOf: '2026-11-12T00:00:00Z', sourceNature: 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP', scope: { tenantId: 'server-only', storeIds: ['s'], warehouseIds: ['w'], canonicalSkuIds: ['sku'], fields: ['quantity'] } }
afterEach(() => vi.unstubAllGlobals())
describe('S01 HTTP consumer contract', () => {
  it('submits exact scope without tenant and binds only explicit previous report', () => {
    const body = createBody(choice, { tenantId: 'server-only', reportId: 'old' })
    expect(body).toEqual({ scenarioId: 'S01_BACKEND', analysisMode: 'SINGLE', scope: { storeIds: ['s'], warehouseIds: ['w'], canonicalSkuIds: ['sku'], fields: ['quantity'] }, parameters: { packageRef: 'fixed-package' }, previousReportRef: { tenantId: 'server-only', reportId: 'old' } })
    expect(createBody(choice).previousReportRef).toBeNull()
  })
  it.each(['QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED'] as TaskState[])('gates report publication independently for %s', state => {
    const t = { state, reportRef: { tenantId: 't', reportId: 'r' } } as Task
    expect(canReport(t)).toBe(state === 'SUCCEEDED')
    expect(canReport({ ...t, reportRef: null })).toBe(false)
    expect(terminal(state)).toBe(!['QUEUED', 'RUNNING'].includes(state))
  })
  it.each([null, undefined, ''])('preserves missing usage as unknown (%s)', value => expect(shown(value)).toBe('未知'))
  it('preserves a genuine zero token value', () => expect(shown(0)).toBe('0'))
  it.each([401, 403, 404, 409, 422, 503])('renders actual HTTP %s without inventing success', async status => {
    vi.stubGlobal('document', { cookie: '' }); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: 'TEST_REJECTION', traceId: 'trace-safe' }), { status })))
    await expect(request('/s01/options')).rejects.toMatchObject({ status, code: 'TEST_REJECTION' })
    expect(errorText(new ApiError(status, 'TEST_REJECTION'))).toContain('TEST_REJECTION')
  })
  it('sends same idempotency key and exact body on replay, with Cookie CSRF', async () => {
    vi.stubGlobal('document', { cookie: 'commerce_csrf=bound-csrf' }); const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response('{}', { status: 202 }))); vi.stubGlobal('fetch', fetch)
    const command = { kind: 'create' as const, key: 'stable-key', path: '/analysis-tasks', body: createBody(choice), createdAt: 'now' }
    await api.command(command); await api.command(command)
    for (const call of fetch.mock.calls) { expect(call[1].headers.get('Idempotency-Key')).toBe('stable-key'); expect(call[1].headers.get('X-CSRF-Token')).toBe('bound-csrf'); expect(call[1].credentials).toBe('same-origin'); expect(JSON.parse(call[1].body)).toEqual(command.body) }
  })
  it('queries one exact history scope with a bounded cursor, never scans catalog', async () => {
    vi.stubGlobal('document', { cookie: '' }); const fetch = vi.fn().mockResolvedValue(new Response('{}')); vi.stubGlobal('fetch', fetch)
    await api.history(choice, 'cursor-id')
    const url = new URL(fetch.mock.calls[0][0], 'http://localhost')
    expect(Object.fromEntries(url.searchParams)).toEqual({ storeId: 's', warehouseId: 'w', canonicalSkuId: 'sku', scenarioId: 'S01_BACKEND', limit: '20', before: 'cursor-id' })
  })
  it('preserves network uncertainty', () => expect(errorText(new TypeError('failed'))).toContain('状态待确认'))
})
