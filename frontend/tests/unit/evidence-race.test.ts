import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, onScopeDispose } from 'vue'
import { api, ApiError } from '../../src/api/client'
import { useWorkspace } from '../../src/useWorkspace'
import type { Report, Task } from '../../src/api/types'

// Use a Vue effect scope without a DOM; disposal still exercises production cleanup.
vi.mock('vue', async original => ({ ...await original<typeof import('vue')>(), onUnmounted: (fn: () => void) => onScopeDispose(fn) }))
const deferred = <T>() => { let resolve!: (value: T) => void, reject!: (e: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
let scope: ReturnType<typeof effectScope>
let w: ReturnType<typeof useWorkspace>
const makeTask = (id: string) => ({ taskRef: { tenantId: 't', taskId: id }, reportRef: { tenantId: 't', reportId: `report-${id}` }, state: 'SUCCEEDED' }) as Task
const makeReport = (id: string) => ({ taskRef: makeTask(id).taskRef, reportRef: makeTask(id).reportRef }) as Report
beforeEach(async () => {
  const values = new Map<string, string>()
  vi.stubGlobal('sessionStorage', { getItem: (k: string) => values.get(k) || null, setItem: (k: string, v: string) => values.set(k, v), removeItem: (k: string) => values.delete(k) })
  vi.spyOn(api, 'task').mockImplementation(async id => makeTask(id))
  vi.spyOn(api, 'report').mockImplementation(async id => makeReport(id))
  vi.spyOn(api, 'options').mockResolvedValue({ mappedChoices: [], limitations: [], scenarioId: 'S01_BACKEND' })
  scope = effectScope(); w = scope.run(useWorkspace)!; w.connected.value = true
  await w.openTask('A')
})
afterEach(() => { scope.stop(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
describe('evidence response is bound to the open task, report and read generation', () => {
  it('reads normal evidence without persisting it', async () => {
    vi.spyOn(api, 'evidence').mockResolvedValue({ field: 'normal-A' })
    await w.readEvidence('a'); expect(w.evidence.value).toEqual({ field: 'normal-A' }); expect(w.evidenceLoading.value).toBe(false)
    expect(JSON.stringify(sessionStorage.getItem('xuheng.s01.v1'))).not.toContain('normal-A')
  })
  it.each(['resolve', 'reject'] as const)('ignores late A %s after switching to B, including finally', async outcome => {
    const a = deferred<unknown>(), b = deferred<unknown>(); let signal: AbortSignal | undefined
    vi.spyOn(api, 'evidence').mockImplementation((task, _id, s) => { if (task === 'A') signal = s; return task === 'A' ? a.promise : b.promise })
    const old = w.readEvidence('a'); await w.openTask('B')
    expect(signal?.aborted).toBe(true); expect(w.evidenceOpen.value).toBe(false); expect(w.evidenceLoading.value).toBe(false); expect(w.evidenceError.value).toBe('')
    const current = w.readEvidence('b')
    if (outcome === 'resolve') a.resolve({ secret: 'A' }); else a.reject(new ApiError(403, 'OLD_FORBIDDEN'))
    await old
    expect(w.connected.value).toBe(true); expect(w.evidence.value).toBeUndefined(); expect(w.evidenceError.value).toBe(''); expect(w.evidenceLoading.value).toBe(true)
    b.resolve({ field: 'B' }); await current; expect(w.evidence.value).toEqual({ field: 'B' })
  })
  it.each(['close', 'logout', 'identity', 'denied', 'expired', 'dispose'] as const)('invalidates protected evidence immediately on %s even if transport ignores abort', async action => {
    const response = deferred<unknown>(); let signal: AbortSignal | undefined
    vi.spyOn(api, 'evidence').mockImplementation((_task, _id, s) => { signal = s; return response.promise })
    const reading = w.readEvidence('a')
    if (action === 'close') w.closeEvidence()
    if (action === 'logout') { const logout = deferred<void>(); vi.spyOn(api, 'logout').mockReturnValue(logout.promise); const leaving = w.logout(); expect(w.evidenceOpen.value).toBe(false); logout.resolve(); await leaving }
    if (action === 'identity') { vi.spyOn(api, 'session').mockResolvedValue({ principalRef: { tenantId: 't', principalId: 'different' } }); await w.connect('different') }
    if (action === 'denied' || action === 'expired') { vi.mocked(api.options).mockRejectedValue(new ApiError(action === 'denied' ? 403 : 401, 'DENIED')); await w.connect() }
    if (action === 'dispose') scope.stop()
    expect(signal?.aborted).toBe(true); expect(w.evidenceOpen.value).toBe(false); expect(w.evidenceLoading.value).toBe(false); expect(w.evidenceError.value).toBe('')
    response.resolve({ secret: 'late-A' }); await reading
    expect(w.evidence.value).toBeUndefined(); expect(w.evidenceOpen.value).toBe(false)
  })
  it('does not accept a response from an earlier read of the same task after reopening', async () => {
    const a = deferred<unknown>(), b = deferred<unknown>(); vi.spyOn(api, 'evidence').mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise)
    const old = w.readEvidence('a'); w.closeEvidence(); const current = w.readEvidence('a')
    a.resolve({ secret: 'old-read' }); await old; expect(w.evidence.value).toBeUndefined(); expect(w.evidenceLoading.value).toBe(true)
    b.resolve({ field: 'fresh-read' }); await current; expect(w.evidence.value).toEqual({ field: 'fresh-read' })
  })
  it('rejects late evidence when the task report reference changes', async () => {
    const d = deferred<unknown>(); vi.spyOn(api, 'evidence').mockReturnValue(d.promise)
    const reading = w.readEvidence('a'); w.report.value = { ...makeReport('A'), reportRef: { tenantId: 't', reportId: 'new-report' } }
    expect(w.evidenceOpen.value).toBe(false); expect(w.evidenceLoading.value).toBe(false)
    d.resolve({ secret: 'old-report' }); await reading; expect(w.evidence.value).toBeUndefined()
  })
  it('clears protected data on an active permission denial', async () => {
    vi.spyOn(api, 'evidence').mockRejectedValue(new ApiError(403, 'FORBIDDEN'))
    await w.readEvidence('a'); expect(w.connected.value).toBe(false); expect(w.task.value).toBeNull(); expect(w.evidenceOpen.value).toBe(false); expect(w.evidenceLoading.value).toBe(false)
  })
})
