import type { Task, TaskState } from './api/types'
export const labels: Record<string, string> = {
  QUEUED: '排队中', RUNNING: '分析中', SUCCEEDED: '任务已完成', FAILED: '任务失败', CANCELLED: '已取消',
  BLOCKED: '数据阻断', PARTIAL: '部分完整 · 候选受限', RULES_ONLY: '规则报告',
  AVAILABLE: '解释可用', UNAVAILABLE: 'AI 解释不可用', NOT_ATTEMPTED: '本次未启用 AI 解释',
  NO_REPLENISHMENT_NEEDED: '当前规则下无需补货；未生成采购候选。',
  INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED: '总量覆盖，但存在中途缺货；桥接采购规则未定义，未生成候选。',
  NO_FEASIBLE_QUANTITY: '采购约束下无可行候选量。', CANDIDATE_RULES_OR_QUALITY_BLOCKED: '质量或规则限制，候选已阻断。', DATA_QUALITY_BLOCKED: '关键数据不足，基线不可计算。',
  PROCUREMENT_EXECUTION_NOT_AUTHORIZED: '仅供教学复核，采购执行未授权。', TEACHING_RULES_ONLY: '仅教学规则，企业规则尚未签认。',
  ENGINEERING_RULES_UNVERIFIED: '工程样例规则未经业务签认。',
}
export const label = (v: string) => labels[v] || v
export const terminal = (state: TaskState) => ['SUCCEEDED', 'FAILED', 'CANCELLED'].includes(state)
export const canReport = (task: Task) => task.state === 'SUCCEEDED' && task.reportRef !== null
export const shown = (v: unknown) => v === null || v === undefined || v === '' ? '未知' : String(v)
export const sourceText = (nature: string) => nature === 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP' ? '教学 ERP 仿真业务数据' : nature === 'SIMULATED_ENGINEERING' ? '本地工程模拟数据' : nature === 'TEACHING_ERP_OBSERVED' ? '教学 ERP 只读观测数据' : nature
export const choiceLabel = (choice: import('./api/types').Choice) => `${choice.scope.canonicalSkuIds.join('、')} · ${choice.asOf || '时点未知'} · ${choice.inputMode === 'ONLINE_TEACHING_ERP' ? '在线 ERP · 每次新采集' : choice.packageRef?.slice(0, 10)}`

export const choiceKey = (choice: import('./api/types').Choice) => choice.choiceRef || choice.packageRef || ''
export const matchesReport = (choice: import('./api/types').Choice, report: import('./api/types').Report) => choice.inputMode === 'ONLINE_TEACHING_ERP' ? report.dataReport.scenarioSupplement.inputMode === 'ONLINE_TEACHING_ERP' && choice.scope.tenantId === report.scope.tenantId && (['storeIds', 'warehouseIds', 'canonicalSkuIds', 'fields'] as const).every(k => JSON.stringify(choice.scope[k]) === JSON.stringify(report.scope[k])) : choice.packageRef === report.dataReport.scenarioSupplement.packageRef
