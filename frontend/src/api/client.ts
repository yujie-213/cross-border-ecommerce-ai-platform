import type { Choice, Command, CreateBody, Options, Ref, Report, Task } from './types'

export class ApiError extends Error {
  constructor(public status: number, public code: string, public traceId?: string) { super(code) }
}
const messages: Record<number, string> = { 401: '会话失效，请重新连接可信身份。', 403: '当前授权不足或已撤销，已停止读取。', 404: '不可访问或不存在，请联系数据负责人核实。', 409: '命令或版本冲突，请重新读取当前状态后核对。', 422: '请求或选项不合法，请刷新授权选项后重选。', 503: '服务暂不可用，请稍后查询实际状态。' }
export function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${messages[error.status] || '接口响应异常，请稍后重试。'} [${error.code}]${error.traceId ? ' · 追踪 ' + error.traceId : ''}`
  return '网络异常或请求超时，状态待确认；命令可能已受理，请用原命令核对。'
}
export function csrfCookie(): string {
  const raw = document.cookie.split('; ').find(x => x.startsWith('commerce_csrf='))?.slice('commerce_csrf='.length)
  return raw ? decodeURIComponent(raw) : ''
}
export async function request<T>(path: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (init.method && !['GET', 'HEAD'].includes(init.method)) {
    const csrf = csrfCookie()
    if (csrf) headers.set('X-CSRF-Token', csrf)
  }
  const response = await fetch('/api/v1' + path, { ...init, headers, credentials: 'same-origin', cache: 'no-store', signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000) })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new ApiError(response.status, typeof data.code === 'string' ? data.code : 'HTTP_ERROR', data.traceId)
  }
  return response.json() as Promise<T>
}
export function createBody(choice: Choice, previous: Ref | null = null): CreateBody {
  const { storeIds, warehouseIds, canonicalSkuIds, fields } = choice.scope
  return { analysisMode: 'SINGLE', scenarioId: 'S01_BACKEND', scope: { storeIds, warehouseIds, canonicalSkuIds, fields }, parameters: choice.inputMode === 'ONLINE_TEACHING_ERP' ? { inputMode: 'ONLINE_TEACHING_ERP' } : { packageRef: choice.packageRef! }, previousReportRef: previous }
}
export const api = {
  options: (signal?: AbortSignal) => request<Options>('/s01/options', {}, signal),
  session: (token: string) => request<{ principalRef: { tenantId: string; principalId: string } }>('/session', { method: 'POST', headers: { Authorization: 'Bearer ' + token } }),
  logout: () => request('/session', { method: 'DELETE' }),
  task: (id: string, signal?: AbortSignal) => request<Task>('/analysis-tasks/' + encodeURIComponent(id), {}, signal),
  report: (id: string, signal?: AbortSignal) => request<Report>('/analysis-tasks/' + encodeURIComponent(id) + '/report', {}, signal),
  evidence: (task: string, id: string, signal?: AbortSignal) => request<unknown>('/analysis-tasks/' + encodeURIComponent(task) + '/evidence/' + encodeURIComponent(id), {}, signal),
  command: (command: Command) => request<Task>(command.path, { method: 'POST', headers: { 'Idempotency-Key': command.key }, body: JSON.stringify(command.body) }),
  history: (choice: Choice, before?: string, signal?: AbortSignal) => {
    const params = new URLSearchParams({ storeId: choice.scope.storeIds[0], warehouseId: choice.scope.warehouseIds[0], canonicalSkuId: choice.scope.canonicalSkuIds[0], scenarioId: 'S01_BACKEND', limit: '20' })
    if (before) params.set('before', before)
    return request<{ items: Task[]; nextCursor: string | null }>('/analysis-tasks?' + params, {}, signal)
  },
}
