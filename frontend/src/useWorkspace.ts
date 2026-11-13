import { computed, onUnmounted, ref, watch } from 'vue'
import { api, ApiError, createBody, errorText } from './api/client'
import type { Choice, Command, Ref, Report, Task } from './api/types'
import { canReport, terminal, choiceKey } from './domain'

const storageKey = 'xuheng.s01.v1'
interface Saved { taskId?: string; packageRef?: string; pending?: Command; owner?: string }
const restore = (): Saved => { try { return JSON.parse(sessionStorage.getItem(storageKey) || '{}') } catch { return {} } }
export function useWorkspace() {
  const saved = restore()
  const choices = ref<Choice[]>([]), selectedRef = ref(saved.packageRef || '')
  const selected = computed(() => choices.value.find(x => choiceKey(x) === selectedRef.value))
  const task = ref<Task | null>(null), report = ref<Report | null>(null), history = ref<Task[]>([])
  const cursor = ref<string | null>(null), historyBefore = ref<string | undefined>()
  const connected = ref(false), busy = ref(false), loading = ref(false), error = ref(''), pollNote = ref('')
  const v2Enabled = ref(false)
  const pending = ref<Command | undefined>(saved.pending)
  const evidence = ref<unknown>(), evidenceError = ref(''), evidenceLoading = ref(false), evidenceOpen = ref(false)
  let evidenceEpoch = 0
  let owner = saved.owner, taskId = saved.taskId, epoch = 0, timer: ReturnType<typeof setTimeout> | undefined
  let readController = new AbortController(), evidenceController = new AbortController(), historyController = new AbortController()
  let historyEpoch = 0
  const persist = () => sessionStorage.setItem(storageKey, JSON.stringify({ taskId, packageRef: selectedRef.value, pending: pending.value, owner }))
  function stop() { closeEvidence(); clearTimeout(timer); timer = undefined; epoch++; readController.abort(); readController = new AbortController() }
  function hideProtected() { stop(); evidenceController.abort(); historyController.abort(); historyEpoch++; loading.value = false; report.value = null; task.value = null; history.value = []; choices.value = []; evidence.value = undefined; connected.value = false; v2Enabled.value = false }
  function fail(e: unknown) { error.value = errorText(e); if (e instanceof ApiError && [401, 403].includes(e.status)) hideProtected() }
  async function loadHistory(before?: string) {
    if (!selected.value || !connected.value) return
    historyController.abort(); historyController = new AbortController()
    const current = ++historyEpoch
    history.value = []; cursor.value = null; historyBefore.value = before
    try {
      const data = await api.history(selected.value, before, historyController.signal)
      if (current !== historyEpoch) return
      history.value = data.items; cursor.value = data.nextCursor
    } catch (e) { if (current === historyEpoch && !historyController.signal.aborted) fail(e) }
  }
  async function selectPackage(value: string) { historyController.abort(); historyEpoch++; history.value = []; cursor.value = null; historyBefore.value = undefined; selectedRef.value = value; persist(); await loadHistory() }
  async function connect(token?: string) {
    if (busy.value) return
    busy.value = true; error.value = ''; closeEvidence()
    try {
      if (token) {
        const identity = await api.session(token)
        const next = JSON.stringify(identity.principalRef)
        if (owner && owner !== next) { taskId = undefined; pending.value = undefined; selectedRef.value = ''; hideProtected() }
        owner = next
      }
      const data = await api.options()
      v2Enabled.value = data.v2Enabled === true
      choices.value = data.mappedChoices; connected.value = true
      if (!choices.value.some(x => choiceKey(x) === selectedRef.value)) selectedRef.value = ''
      persist()
      if (selected.value) await loadHistory()
      if (taskId && !v2Enabled.value) await openTask(taskId)
    } catch (e) { fail(e) } finally { busy.value = false }
  }
  async function logout() {
    if (busy.value) return
    busy.value = true; hideProtected()
    try { await api.logout(); taskId = undefined; owner = undefined; pending.value = undefined; sessionStorage.removeItem(storageKey) }
    catch (e) { fail(e) } finally { busy.value = false }
  }
  async function refreshTask(current: number, count = 0) {
    if (!taskId || current !== epoch) return
    try {
      const value = await api.task(taskId, readController.signal)
      if (current !== epoch) return
      task.value = value
      if (canReport(value)) {
        const result = await api.report(taskId, readController.signal)
        if (current !== epoch) return
        // Require this task's actual published ref, never a historical fallback.
        if (result.taskRef.taskId !== taskId || result.reportRef.reportId !== value.reportRef?.reportId) throw new ApiError(502, 'REPORT_BINDING_MISMATCH')
        if (JSON.stringify(report.value?.reportRef) !== JSON.stringify(result.reportRef)) closeEvidence()
        report.value = result
        await loadHistory(historyBefore.value)
      } else if (value.state === 'SUCCEEDED') pollNote.value = '任务已完成，但报告尚不可访问。请手动重新查询。'
      if (terminal(value.state)) return
      if (count >= 59) { pollNote.value = '本次自动查询已到上限，服务端状态未被修改。可手动重新查询。'; return }
      timer = setTimeout(() => void refreshTask(current, count + 1), 2000)
    } catch (e) {
      if (current !== epoch) return
      // A denied/missing report must not leave a stale report on screen.
      closeEvidence(); report.value = null; fail(e); pollNote.value = '自动查询已停止，请核对会话或手动重新查询。'
    }
  }
  async function openTask(id: string) {
    stop(); taskId = id; task.value = null; report.value = null; error.value = ''; pollNote.value = ''; persist()
    loading.value = true
    const current = epoch
    try { await refreshTask(current) } finally { if (current === epoch) loading.value = false }
  }
  async function send(command: Command) {
    if (busy.value || !connected.value) return
    busy.value = true; error.value = ''; pending.value = command; persist()
    try {
      const value = await api.command(command)
      pending.value = undefined; persist(); await openTask(value.taskRef.taskId)
      await loadHistory()
    } catch (e) {
      // A definitive rejection is not transport uncertainty. Never silently create a replacement command.
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) { pending.value = undefined; persist() }
      fail(e)
    } finally { busy.value = false }
  }
  async function create(previous: Ref | null = null) {
    if (!selected.value || pending.value || busy.value) return
    await send({ kind: 'create', key: crypto.randomUUID(), path: '/analysis-tasks', body: createBody(selected.value, previous), createdAt: new Date().toISOString() })
  }
  async function cancel() {
    if (!task.value || terminal(task.value.state) || pending.value || busy.value) return
    await send({ kind: 'cancel', key: crypto.randomUUID(), path: `/analysis-tasks/${task.value.taskRef.taskId}/cancel`, body: { expectedRevision: task.value.revision }, createdAt: new Date().toISOString() })
  }
  async function readEvidence(id: string) {
    closeEvidence()
    if (!connected.value || !task.value || !report.value) return
    const requestedTask = task.value.taskRef.taskId
    const requestedReport = JSON.stringify(report.value.reportRef)
    if (report.value.taskRef.taskId !== requestedTask || requestedTask !== taskId) return
    const current = evidenceEpoch, context = epoch, signal = evidenceController.signal
    evidenceOpen.value = true; evidenceLoading.value = true
    const active = () => current === evidenceEpoch && context === epoch && !signal.aborted &&
      evidenceOpen.value && connected.value && taskId === requestedTask &&
      task.value?.taskRef.taskId === requestedTask && JSON.stringify(report.value?.reportRef) === requestedReport
    try { const value = await api.evidence(requestedTask, id, signal); if (active()) evidence.value = value }
    catch (e) { if (active()) { evidenceError.value = errorText(e); if (e instanceof ApiError && [401, 403].includes(e.status)) fail(e) } }
    finally { if (active()) evidenceLoading.value = false }
  }
  function closeEvidence() {
    evidenceEpoch++; evidenceController.abort(); evidenceController = new AbortController()
    evidenceOpen.value = false; evidence.value = undefined; evidenceError.value = ''; evidenceLoading.value = false
  }
  watch([() => task.value?.taskRef.taskId, () => JSON.stringify(report.value?.reportRef)], closeEvidence, { flush: 'sync' })
  onUnmounted(() => { stop(); historyController.abort(); evidenceController.abort() })
  return { v2Enabled, choices, selectedRef, selected, task, report, history, cursor, historyBefore, connected, busy, loading, error, pollNote, pending, evidence, evidenceError, evidenceLoading, evidenceOpen, connect, logout, selectPackage, loadHistory, openTask, create, cancel, readEvidence, closeEvidence, retryCommand: () => pending.value && send(pending.value) }
}
