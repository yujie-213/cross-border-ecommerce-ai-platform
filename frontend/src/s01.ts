import { computed, reactive, watch } from 'vue'
import { request, ApiError, errorText } from './api/client'
import type { Task } from './api/types'
import type { V2Item, V2List, V2Options, V2Progress, V2Single, V2Requisition } from './api/v2'
import { terminal } from './domain'

/**
 * Single source of truth for the S01 replenishment workspace.
 * Everything here is read from the real API; nothing is derived by the client
 * except pure grouping of server-returned counts.
 */
type SingleRow = Task & { sku?: string; entityKey?: string; sourceGrade?: string }

const emptyList = (): V2List => ({ total: 0, items: [], stores: [], warehouses: [] })

export const state = reactive({
  options: null as V2Options | null,
  ready: false,
  error: '',
  note: '',

  batches: [] as Task[],
  batchCursor: null as string | null,
  batchId: '',
  progress: null as V2Progress | null,
  progressLoading: false,

  list: emptyList(),
  listLoading: false,
  filters: { q: '', store: '', warehouse: '', source: '', state: '' },
  offset: 0,
  limit: 50,

  item: null as V2Item | null,
  itemLoading: false,
  itemKey: '',

  singleId: '',
  singleTask: null as Task | null,
  singleReport: null as V2Single['report'],
  singleLoading: false,
  singlePolling: false,

  singleHistory: [] as SingleRow[],
  requisition: null as V2Requisition | null,
  requisitionLoading: false,

  busy: false,
  pending: null as { key: string; path: string; body: object; kind: string; createdAt: string } | null
})

export const summary = computed(() => state.progress?.summary || null)

export const grouped = computed(() => {
  const s = summary.value
  if (!s) return []
  return [
    { key: 'confirm', label: '待确认', count: s.ruleCalculated + s.erpReference, color: '#0f6b64' },
    { key: 'history', label: '历史参考', count: s.historicalReference || 0, color: '#7a8fa6' },
    { key: 'review', label: '需核实', count: s.unanalyzable, color: '#c9812f' },
    { key: 'none', label: '无需补货', count: s.noReplenishment, color: '#c3ccd4' },
    { key: 'broken', label: '失败/未完成', count: s.failed + s.unfinished, color: '#a8382f' }
  ].filter(x => x.count > 0)
})

/* ---------------- helpers ---------------- */

export type Stage = 'confirm' | 'history' | 'review' | 'none' | 'broken' | 'pending'

export function stageOf(item: V2Item): Stage {
  switch (item.analysisState) {
    case 'ANALYZED':
    case 'ERP_REFERENCE': return 'confirm'
    case 'HISTORICAL_REFERENCE': return 'history'
    case 'NO_REPLENISHMENT': return 'none'
    case 'NEEDS_REVIEW':
    case 'UNANALYZABLE': return 'review'
    case 'FAILED': return 'broken'
    case 'PENDING': return 'pending'
    default: return 'review'
  }
}

export const STAGE_LABEL: Record<Stage, string> = {
  confirm: '待确认', history: '历史参考', review: '需核实', none: '无需补货', broken: '分析失败', pending: '等待处理'
}
export const STAGE_TONE: Record<Stage, string> = {
  confirm: 'primary', history: 'info', review: 'warning', none: 'muted', broken: 'danger', pending: 'muted'
}

export const unitOf = (item: V2Item) => (item.unit === 'EA' ? '件' : item.unit || '件')
export const dash = (v: unknown) => (v === null || v === undefined || v === '' ? '—' : String(v))

/** Backend returns exact decimals (e.g. 1.0769230752662721); operators need a readable number. */
export function fmt(value: unknown, digits = 1): string {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  const rounded = Number(n.toFixed(digits))
  return String(rounded)
}

/** Rule coverage is only meaningful when the rule engine produced a baseline. */
export function coverage(item: V2Item) {
  return item.ruleResult?.supplyDemand?.baseline?.coverageDays ?? null
}

export function leadDays(item: V2Item) {
  return item.ruleResult?.forecast?.leadDays ?? null
}

let initPromise: Promise<void> | null = null
let epoch = 0
let listEpoch = 0
let detailEpoch = 0
let pollTimer: ReturnType<typeof setTimeout> | undefined
let singleTimer: ReturnType<typeof setTimeout> | undefined

function fail(error: unknown) {
  state.error = errorText(error)
  if (error instanceof ApiError && [401, 403].includes(error.status)) {
    state.ready = false
    state.progress = null
    state.list = emptyList()
    state.item = null
  }
}

export async function init() {
  if (initPromise) return initPromise
  initPromise = (async () => {
    try {
      state.options = await request<V2Options>('/s01/v2/options')
      await Promise.all([loadHistory(), loadSingleHistory()])
      state.ready = true
    } catch (e) { fail(e) }
  })()
  return initPromise
}

export function reset() {
  initPromise = null
  clearTimeout(pollTimer); clearTimeout(singleTimer)
  epoch++; listEpoch++; detailEpoch++
  state.options = null; state.ready = false; state.error = ''
  state.batches = []; state.batchId = ''; state.progress = null
  state.list = emptyList(); state.item = null; state.itemKey = ''
  state.singleId = ''; state.singleReport = null; state.singleTask = null
  state.singleHistory = []; state.requisition = null; state.pending = null
}

export async function loadHistory(before?: string) {
  try {
    const query = before ? '?before=' + encodeURIComponent(before) : ''
    const data = await request<{ items: Task[]; nextCursor: string | null }>('/s01/v2/batches' + query)
    state.batches = data.items
    state.batchCursor = data.nextCursor
    return data.items
  } catch (e) { fail(e); return [] }
}

export async function loadSingleHistory() {
  try {
    const data = await request<{ items: SingleRow[] }>('/s01/v2/singles')
    state.singleHistory = data.items
    return data.items
  } catch (e) { fail(e); return [] }
}

/** Opens a batch and, when it already has results, loads the first page. */
export async function openBatch(id: string) {
  if (!id) return
  if (state.batchId === id && state.progress) return
  clearTimeout(pollTimer)
  const mine = ++epoch
  state.batchId = id
  state.progress = null
  state.progressLoading = true
  state.list = emptyList()
  try {
    await pollBatch(mine)
  } finally {
    if (mine === epoch) state.progressLoading = false
  }
}

async function pollBatch(mine: number, count = 0) {
  if (mine !== epoch) return
  try {
    const data = await request<V2Progress>(`/s01/v2/batches/${state.batchId}`)
    if (mine !== epoch) return
    state.progress = data
    await loadList()
    if (!terminal(data.task.state) && count < 300) {
      pollTimer = setTimeout(() => void pollBatch(mine, count + 1), 2000)
    } else if (!terminal(data.task.state)) {
      state.note = '自动查询已到上限，可手动刷新状态。'
    }
  } catch (e) { if (mine === epoch) fail(e) }
}

export async function refreshBatch() {
  if (!state.batchId) return
  await pollBatch(epoch)
  await loadHistory()
}

export async function loadList() {
  if (!state.batchId) return
  const mine = ++listEpoch
  state.listLoading = true
  const params = new URLSearchParams({ limit: String(state.limit), offset: String(state.offset) })
  Object.entries(state.filters).forEach(([key, value]) => { if (value) params.set(key, value) })
  try {
    const data = await request<V2List>(`/s01/v2/batches/${state.batchId}/items?${params}`)
    if (mine === listEpoch) state.list = data
  } catch (e) { if (mine === listEpoch) fail(e) }
  finally { if (mine === listEpoch) state.listLoading = false }
}

export function setFilters(next: Partial<typeof state.filters>) {
  state.filters = { ...state.filters, ...next }
  state.offset = 0
  return loadList()
}

export function setOffset(offset: number) {
  state.offset = Math.max(0, offset)
  return loadList()
}

export async function openItem(key: string, singleId?: string) {
  const mine = ++detailEpoch
  state.itemKey = key
  state.item = null
  state.itemLoading = true
  state.singleId = ''; state.singleReport = null; state.singleTask = null; state.requisition = null
  try {
    const item = await request<V2Item>(`/s01/v2/batches/${state.batchId}/items/${key}`)
    if (mine !== detailEpoch) return
    state.item = item
    // Only an explicitly referenced analysis is opened: an older single must never
    // silently replace the current batch conclusion.
    if (singleId) await openSingle(singleId)
  } catch (e) { if (mine === detailEpoch) fail(e) }
  finally { if (mine === detailEpoch) state.itemLoading = false }
}

export async function openSingle(id: string) {
  clearTimeout(singleTimer)
  const mine = ++detailEpoch
  state.singleId = id
  state.singleReport = null
  state.singleTask = null
  state.singleLoading = true
  await pollSingle(id, mine)
  state.singleLoading = false
}

async function pollSingle(id: string, mine: number, count = 0) {
  try {
    const data = await request<V2Single>(`/s01/v2/singles/${id}`)
    if (mine !== detailEpoch || state.singleId !== id) return
    state.singleTask = data.task
    if (data.report) {
      state.singleReport = data.report
      state.item = data.report.dataReport.item
      state.singleLoading = false
      await readRequisition()
      await loadSingleHistory()
    } else if (!terminal(data.task.state) && count < 300) {
      state.singlePolling = true
      singleTimer = setTimeout(() => void pollSingle(id, mine, count + 1), 2000)
    } else {
      state.singlePolling = false
    }
  } catch (e) { if (mine === detailEpoch) fail(e) }
}

export async function createSingle() {
  const item = state.item
  if (!item || state.busy || !state.batchId) return
  state.busy = true; state.error = ''; state.note = ''
  state.singleLoading = true
  const key = crypto.randomUUID()
  try {
    const task = await request<Task>('/s01/v2/singles', {
      method: 'POST',
      headers: { 'Idempotency-Key': key },
      body: JSON.stringify({ batchId: state.batchId, entityKey: item.entityKey })
    })
    await openSingle(task.taskRef.taskId)
  } catch (e) {
    // A definite rejection is not an unknown outcome; never silently retry it.
    fail(e)
    state.singleLoading = false
  } finally { state.busy = false }
}

export async function readRequisition() {
  if (!state.singleId || !state.options?.canSubmit) { state.requisition = null; return }
  state.requisitionLoading = true
  try {
    state.requisition = await request<V2Requisition | null>(`/s01/v2/singles/${state.singleId}/requisition`)
  } catch (e) {
    if (e instanceof ApiError && [404, 409].includes(e.status)) state.requisition = null
    else fail(e)
  } finally { state.requisitionLoading = false }
}

export async function submitRequisition(finalQuantity: number, adjustmentReason: string) {
  if (!state.singleId || state.busy || !state.item?.procurementEligibility?.eligible) return
  state.busy = true; state.error = ''; state.note = ''
  const key = crypto.randomUUID()
  try {
    state.requisition = await request<V2Requisition>(`/s01/v2/singles/${state.singleId}/requisition`, {
      method: 'POST',
      headers: { 'Idempotency-Key': key },
      body: JSON.stringify({ finalQuantity, adjustmentReason, sourceAcknowledged: true })
    }, undefined, 90000)
    state.note = '请购已提交 ERP，等待独立回读审批状态。'
  } catch (e) {
    // Transport failure after send: keep the key as an explicit pending command.
    if (!(e instanceof ApiError)) {
      state.pending = {
        key, kind: 'requisition', createdAt: new Date().toISOString(),
        path: `/s01/v2/singles/${state.singleId}/requisition`,
        body: { finalQuantity, adjustmentReason, sourceAcknowledged: true }
      }
    }
    fail(e)
  } finally { state.busy = false }
}

/** Replays the exact pending requisition command with its original idempotency key. */
export async function replayPending() {
  const pending = state.pending
  if (!pending || state.busy) return
  state.busy = true; state.error = ''
  try {
    state.requisition = await request<V2Requisition>(pending.path, {
      method: 'POST', headers: { 'Idempotency-Key': pending.key }, body: JSON.stringify(pending.body)
    }, undefined, 90000)
    state.pending = null
    state.note = '已用原命令核对，未创建第二张单据。'
  } catch (e) { fail(e) }
  finally { state.busy = false }
}

export async function startBatch() {
  if (state.busy) return
  state.busy = true; state.error = ''
  try {
    const task = await request<Task>('/s01/v2/batches', {
      method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({})
    })
    state.batchId = ''
    await loadHistory()
    await openBatch(task.taskRef.taskId)
    return task.taskRef.taskId
  } catch (e) { fail(e); return '' }
  finally { state.busy = false }
}

/** Latest finished batch, used to give the workbench content on first visit. */
export function latestBatchId() {
  const done = state.batches.find(t => t.state === 'SUCCEEDED')
  return (done || state.batches[0])?.taskRef.taskId || ''
}

export interface RequisitionRow { task: SingleRow; requisition: V2Requisition | null }
export const requisitionRows = reactive({ items: [] as RequisitionRow[], loading: false, loaded: false })

export async function loadRequisitions() {
  if (requisitionRows.loading) return
  requisitionRows.loading = true
  try {
    const rows = state.singleHistory.filter(row => row.state === 'SUCCEEDED')
    const result: RequisitionRow[] = []
    // Bounded concurrency: the backend exposes no ledger endpoint yet, so this
    // reads each known single analysis individually.
    for (let i = 0; i < rows.length; i += 4) {
      const chunk = await Promise.all(rows.slice(i, i + 4).map(async row => {
        try {
          const value = await request<V2Requisition | null>(`/s01/v2/singles/${row.taskRef.taskId}/requisition`)
          return { task: row, requisition: value }
        } catch { return { task: row, requisition: null } }
      }))
      result.push(...chunk)
    }
    requisitionRows.items = result
    requisitionRows.loaded = true
  } catch (e) { fail(e) }
  finally { requisitionRows.loading = false }
}

watch(() => state.error, value => { if (!value) return; setTimeout(() => { if (state.error === value) state.error = '' }, 12000) })
