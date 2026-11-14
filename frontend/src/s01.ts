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
type SingleRow = Task & { sku?: string; entityKey?: string; sourceGrade?: string; aiStatus?: string; observedAt?: string }

const emptyList = (): V2List => ({ total: 0, items: [], stores: [], warehouses: [] })
/** The backend returns its own priority order; the workbench shows the head of it. */
export const PRIORITY_LIMIT = 50
const PENDING_KEY = 'xuheng.s01.v3.pending'

function savePending(value: PendingCommand | null) {
  state.pending = value
  try {
    if (value) sessionStorage.setItem(PENDING_KEY, JSON.stringify(value))
    else sessionStorage.removeItem(PENDING_KEY)
  } catch { /* storage unavailable: keep the in-memory value */ }
}

function restorePending() {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY)
    if (!raw) return
    const value = JSON.parse(raw) as PendingCommand
    if (value && value.key && value.path && value.singleId) state.pending = value
  } catch { /* ignore malformed leftovers */ }
}

/** The pending command belongs to the analysis currently on screen, if any. */
export function pendingFor(singleId: string) {
  return state.pending && state.pending.singleId === singleId ? state.pending : null
}

export const state = reactive({
  options: null as V2Options | null,
  ready: false,
  error: '',
  note: '',

  batches: [] as (Task & { analysisRange?: string })[],
  batchCursor: null as string | null,
  batchId: '',
  progress: null as V2Progress | null,
  progressLoading: false,

  list: emptyList(),
  listLoading: false,
  /** Unfiltered top of the batch order, owned by the workbench (never the list page's query). */
  priority: [] as V2Item[],
  priorityLoading: false,
  filters: { q: '', store: '', warehouse: '', source: '', state: '', decision: '' },
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
  singleMode: null as 'analysis' | 'ai' | null,
  singleError: '',

  singleHistory: [] as SingleRow[],
  requisition: null as V2Requisition | null,
  requisitionLoading: false,
  requisitionReadState: 'idle' as 'idle' | 'loading' | 'ready' | 'error',

  busy: false,
  /** A command whose outcome is unknown: it must only be replayed with its own key. */
  pending: null as PendingCommand | null
})

export interface PendingCommand {
  key: string
  path: string
  body: object
  kind: string
  createdAt: string
  singleId: string
  entityKey: string
  sku: string
}

export const summary = computed(() => state.progress?.summary || null)

export const grouped = computed(() => {
  const s = summary.value
  if (!s) return []
  if (s.judgedScopeCount !== undefined) return [
    { key: 'confirm', label: '建议补货', count: s.replenishScopeCount || 0, color: '#0f6b64' },
    { key: 'none', label: '暂不补货', count: s.noReplenishmentScopeCount || 0, color: '#8baaa0' },
    { key: 'review', label: '依据不足', count: s.reviewScopeCount || 0, color: '#c9812f' }
  ].filter(x => x.count > 0)
  return [
    { key: 'confirm', label: '有建议数量', count: s.ruleCalculated + s.erpReference, color: '#0f6b64' },
    { key: 'history', label: '历史参考', count: s.historicalReference || 0, color: '#7a8fa6' },
    { key: 'review', label: '需核实', count: s.unanalyzable, color: '#c9812f' },
    { key: 'none', label: '无需补货', count: s.noReplenishment, color: '#c3ccd4' },
    { key: 'broken', label: '失败/未完成', count: s.failed + s.unfinished, color: '#a8382f' }
  ].filter(x => x.count > 0)
})

/* ---------------- helpers ---------------- */

export type Stage = 'confirm' | 'history' | 'review' | 'none' | 'broken' | 'pending'

export function stageOf(item: V2Item): Stage {
  if (item.productSummary) {
    if (item.productSummary.replenishScopeCount) return 'confirm'
    if (item.productSummary.judgedScopeCount < item.productSummary.scopeCount) return 'review'
    return 'none'
  }
  if (item.decision) return item.decision.status === 'REPLENISH' ? 'confirm' : item.decision.status === 'NO_REPLENISHMENT' ? 'none' : 'review'
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
  confirm: '建议补货', history: '历史参考', review: '需核实', none: '无需补货', broken: '分析失败', pending: '等待处理'
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
  return item.decision?.coverageDays ?? item.ruleResult?.supplyDemand?.baseline?.coverageDays ?? null
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
      restorePending()
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
  state.singleMode = null; state.singleError = ''; state.singleLoading = false; state.singlePolling = false
  state.singleHistory = []; state.requisition = null; savePending(null)
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
  detailEpoch++; clearTimeout(singleTimer)
  state.item = null; state.itemKey = ''; state.singleReport = null; state.singleTask = null; state.singleId = ''
  state.singleLoading = false; state.singlePolling = false; state.singleError = ''; state.singleMode = null
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
    const historyRow = state.batches.find(t => t.taskRef.taskId === data.task.taskRef.taskId)
    if (historyRow) Object.assign(historyRow, data.task, { analysisRange: data.analysisRange })
    await Promise.all([loadList(), loadPriority()])
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
  const params = new URLSearchParams({ limit: String(state.limit), offset: String(state.offset), group: 'sku' })
  Object.entries(state.filters).forEach(([key, value]) => { if (value) params.set(key, value) })
  try {
    const data = await request<V2List>(`/s01/v2/batches/${state.batchId}/items?${params}`)
    if (mine === listEpoch) state.list = data
  } catch (e) { if (mine === listEpoch) fail(e) }
  finally { if (mine === listEpoch) state.listLoading = false }
}

export async function loadPriority() {
  if (!state.batchId) return
  const batch = state.batchId
  state.priorityLoading = true
  try {
    const data = await request<V2List>(`/s01/v2/batches/${batch}/items?limit=${PRIORITY_LIMIT}&offset=0`)
    if (batch === state.batchId) state.priority = data.items
  } catch (e) { fail(e) }
  finally { if (batch === state.batchId) state.priorityLoading = false }
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
  clearTimeout(singleTimer)
  state.itemKey = key
  state.item = null
  state.itemLoading = true
  state.singleId = ''; state.singleReport = null; state.singleTask = null; state.requisition = null; state.requisitionReadState = 'idle'
  state.singleMode = null; state.singleError = ''; state.singleLoading = false; state.singlePolling = false; state.error = ''
  try {
    const item = await request<V2Item>(`/s01/v2/batches/${state.batchId}/items/${key}`)
    if (mine !== detailEpoch) return
    state.item = item
    // Only an explicitly referenced analysis is opened: an older single must never
    // silently replace the current batch conclusion.
    state.itemLoading = false
    if (singleId) await openSingle(singleId)
  } catch (e) {
    // Opened from somewhere without a batch context (e.g. the requisition ledger):
    // the referenced analysis is still valid even if this batch lacks the entity.
    if (mine === detailEpoch && singleId) {
      state.itemLoading = false
      await openSingle(singleId)
      if (state.singleReport) { state.error = ''; return }
    }
    if (mine === detailEpoch) fail(e)
  }
  finally { if (mine === detailEpoch) state.itemLoading = false }
}

export async function openSingle(id: string, mode: 'analysis' | 'ai' | null = null) {
  clearTimeout(singleTimer)
  const mine = ++detailEpoch
  state.singleId = id
  state.requisition = null; state.requisitionReadState = 'idle'
  state.singleReport = null
  state.singleTask = null
  state.singleMode = mode; state.singleError = ''; state.singlePolling = false
  state.singleLoading = true
  await pollSingle(id, mine)
  if (mine === detailEpoch) state.singleLoading = false
}

async function pollSingle(id: string, mine: number, count = 0) {
  try {
    const data = await request<V2Single>(`/s01/v2/singles/${id}`)
    if (mine !== detailEpoch || state.singleId !== id) return
    state.singleTask = data.task
    if (data.report) {
      if (data.report.dataReport.item.entityKey !== state.itemKey) {
        state.singleError = '这份分析不属于当前店仓，请返回该商品重新分析。'
        state.singleReport = null; state.singleTask = null; state.singlePolling = false; state.singleLoading = false
        return
      }
      state.singleReport = data.report
      state.item = { ...data.report.dataReport.item, relatedScopes: state.item?.relatedScopes }
      state.singleLoading = false
      state.singlePolling = false
      await readRequisition()
      await loadSingleHistory()
    } else if (!terminal(data.task.state) && count < 300) {
      state.singlePolling = true
      singleTimer = setTimeout(() => void pollSingle(id, mine, count + 1), 2000)
    } else {
      state.singlePolling = false
      state.singleLoading = false
      if (data.task.state === 'FAILED') state.singleError = data.task.errorCode || '分析未完成，请重试。'
      if (data.task.state === 'CANCELLED') state.singleError = '本次分析已停止，可重新分析。'
      if (!terminal(data.task.state)) state.singleError = '本次分析仍在处理中，请重新读取状态；不要重复创建。'
    }
  } catch (e) { if (mine === detailEpoch) { state.singleError = errorText(e); state.singlePolling = false; state.singleLoading = false } }
}

export async function createSingle(explainAI = false) {
  const item = state.item
  if (!item || state.busy || !state.batchId) return
  state.busy = true; state.error = ''; state.note = ''
  state.singleLoading = true
  state.singleMode = explainAI ? 'ai' : 'analysis'; state.singleError = ''
  state.singleReport = null; state.singleTask = null; state.singleId = ''; state.singlePolling = false
  const mine = detailEpoch, batch = state.batchId, entityKey = item.entityKey
  const key = crypto.randomUUID()
  try {
    const task = await request<Task>('/s01/v2/singles', {
      method: 'POST',
      headers: { 'Idempotency-Key': key },
      body: JSON.stringify({ batchId: state.batchId, entityKey: item.entityKey, explainAI })
    })
    if (mine !== detailEpoch || state.itemKey !== entityKey || state.batchId !== batch) return
    await openSingle(task.taskRef.taskId, explainAI ? 'ai' : 'analysis')
    return task.taskRef.taskId
  } catch (e) {
    // A definite rejection is not an unknown outcome; never silently retry it.
    if (mine === detailEpoch) { state.singleError = errorText(e); state.singleLoading = false }
  } finally { state.busy = false }
}

let requisitionEpoch = 0
export async function readRequisition() {
  const epoch = ++requisitionEpoch
  const id = state.singleId
  if (!id) { state.requisitionReadState = 'idle'; return }
  state.requisitionLoading = true; state.requisitionReadState = 'loading'
  try {
    const value = await request<V2Requisition | null>(`/s01/v2/singles/${id}/requisition`)
    if (id !== state.singleId || epoch !== requisitionEpoch) return
    state.requisition = value; state.requisitionReadState = 'ready'
  } catch (e) {
    if (id !== state.singleId || epoch !== requisitionEpoch) return
    state.requisitionReadState = 'error'
    fail(e)
  } finally { if (id === state.singleId && epoch === requisitionEpoch) state.requisitionLoading = false }
}

export async function submitRequisition(finalQuantity: number, adjustmentReason: string) {
  if (!state.singleId || state.busy || !state.item?.procurementEligibility?.eligible) return
  // Safety: never start a second requisition while one exists or its outcome is unknown.
  if (state.requisitionReadState !== 'ready' || state.requisitionLoading || state.requisition || (state.pending && state.pending.entityKey === state.item.entityKey)) {
    state.note = '该分析已有请购单或结果未确认，请先核对原命令，不能重复提交。'
    return
  }
  const singleId = state.singleId
  const entityKey = state.item.entityKey
  const sku = state.item.sku
  state.busy = true; state.error = ''; state.note = ''
  const key = crypto.randomUUID()
  savePending({ key, kind:'requisition', createdAt:new Date().toISOString(), path:`/s01/v2/singles/${singleId}/requisition`, body:{finalQuantity, adjustmentReason, sourceAcknowledged:true}, singleId, entityKey, sku })
  try {
    state.requisition = await request<V2Requisition>(`/s01/v2/singles/${state.singleId}/requisition`, {
      method: 'POST',
      headers: { 'Idempotency-Key': key },
      body: JSON.stringify({ finalQuantity, adjustmentReason, sourceAcknowledged: true })
    }, undefined, 90000)
    savePending(null)
    state.note = '请购已提交 ERP，等待独立回读审批状态。'
  } catch (e) {
    // Transport failure after send: keep the key bound to this analysis and SKU.
    if (!(e instanceof ApiError)) {
      // A transport failure is represented by the pending command itself; a second
      // generic banner would say exactly the same thing again.
      savePending({
        key, kind: 'requisition', createdAt: new Date().toISOString(),
        path: `/s01/v2/singles/${singleId}/requisition`,
        body: { finalQuantity, adjustmentReason, sourceAcknowledged: true },
        singleId, entityKey, sku
      })
      state.error = ''
    } else {
      if (e.status < 500) savePending(null)
      state.requisitionReadState = 'error'
      fail(e)
    }
  } finally { state.busy = false }
}

/** Replays the exact pending requisition command with its original idempotency key. */
export async function replayPending() {
  const pending = state.pending
  // Only the analysis the command belongs to may replay it.
  if (!pending || state.busy || pending.singleId !== state.singleId) return
  state.busy = true; state.error = ''
  try {
    const value = await request<V2Requisition>(pending.path, {
      method: 'POST', headers: { 'Idempotency-Key': pending.key }, body: JSON.stringify(pending.body)
    }, undefined, 90000)
    if (pending.singleId === state.singleId) state.requisition = value
    savePending(null)
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

export async function cancelBatch() {
  if (!state.progress || state.busy) return
  state.busy = true
  try {
    await request(`/s01/v2/batches/${state.batchId}/cancel`, { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({ expectedRevision: state.progress.task.revision }) })
    await refreshBatch()
  } catch (e) { fail(e) } finally { state.busy = false }
}

/** Latest finished batch, used to give the workbench content on first visit. */
export function latestBatchId() {
  const available = state.options?.analysisRange === 'OWNED_REGISTERED' ? state.batches.filter(t => t.analysisRange === 'OWNED_REGISTERED') : state.batches
  const done = available.find(t => t.state === 'SUCCEEDED')
  return (done || available[0])?.taskRef.taskId || ''
}

export type RequisitionCategory = 'pending' | 'approved' | 'unknown' | 'blocked' | 'draft'

/** ERP text is returned by an external system: only an explicit approval counts as approved. */
const APPROVED_TEXT = /(审批通过|审核通过|已审批|已批准|已通过)/
const UNKNOWN_STATES = ['SUBMIT_UNKNOWN', 'CREATE_UNKNOWN']

export function requisitionCategory(requisition: V2Requisition | null): RequisitionCategory {
  const platform = requisition?.state || ''
  if (UNKNOWN_STATES.includes(platform)) return 'unknown'
  if (platform === 'BLOCKED') return 'blocked'
  if (platform !== 'SUBMITTED') return 'draft'
  return APPROVED_TEXT.test(String(requisition?.erpStatus || '')) ? 'approved' : 'pending'
}

export interface RequisitionRow { task: SingleRow; requisition: V2Requisition | null }
export const requisitionRows = reactive({ items: [] as RequisitionRow[], loading: false, loaded: false, failed: 0, error: '' })

export async function loadRequisitions() {
  if (requisitionRows.loading) return
  requisitionRows.loading = true
  requisitionRows.failed = 0
  requisitionRows.error = ''
  try {
    const rows = state.singleHistory.filter(row => row.state === 'SUCCEEDED')
    const result: RequisitionRow[] = []
    // Bounded concurrency: the backend exposes no ledger endpoint yet, so this
    // reads each known single analysis individually.
    for (let i = 0; i < rows.length; i += 4) {
      const chunk = await Promise.all(rows.slice(i, i + 4).map(async row => {
        try {
          const value = await request<V2Requisition | null>(`/s01/v2/singles/${row.taskRef.taskId}/requisition`)
          return { task: row, requisition: value, failed: false }
        } catch (error) {
          // A read failure is not "no requisition": keep them apart.
          requisitionRows.failed++
          if (!requisitionRows.error) requisitionRows.error = errorText(error)
          return { task: row, requisition: null, failed: true }
        }
      }))
      chunk.forEach(row => { if (!row.failed) result.push({ task: row.task, requisition: row.requisition }) })
    }
    requisitionRows.items = result
    requisitionRows.loaded = true
  } catch (e) { fail(e) }
  finally { requisitionRows.loading = false }
}

watch(() => state.error, value => { if (!value) return; setTimeout(() => { if (state.error === value) state.error = '' }, 12000) })
