import type { V2Item } from './api/v2'
export const displayDate = (value?: string | null) => value ? value.slice(5, 10).replace('-', '/') : '待核实'
export const resultDate = (value?: string | null) => value ? new Date(value).toLocaleString('zh-CN', { month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Shanghai' }) : '时间未记录'
export const forecastOf = (item: V2Item) => item.decision?.forecast
export const quantityOf = (item: V2Item) => item.decision?.referenceReplenishmentQuantity ?? item.quantity
/** A local editable proposal, not a grant to submit. Prefer the server's constrained candidate. */
export const suggestedPurchaseQuantity = (item: V2Item) => item.decision?.purchasableQuantity ?? item.quantity ?? item.decision?.referenceReplenishmentQuantity ?? null
export const shortageOf = (item: V2Item) => item.decision?.firstShortageDate || item.riskDate
export function nextAction(item: V2Item): string {
  if (item.analysisState === 'FAILED') return '重新分析，核实读取失败的资料'
  if (!item.decision?.forecast.available) return '核实有效销售记录，再判断需求'
  if (item.decision?.status === 'NO_REPLENISHMENT') return '保持观察，暂不追加库存'
  if (item.pendingPurchases?.length || item.formalPurchases?.length) return '先核对已有采购，避免重复请购'
  if (!item.procurementEligibility?.eligible) return '先分析需求，再补齐采购条件'
  return '查看 AI 建议，核实后人工请购'
}
export function confidenceNote(item: V2Item): string {
  const f = forecastOf(item)
  if (!f?.available) return '缺少可信销量，不能将空记录视为零需求'
  const notes = []
  if (f.unknownDays) notes.push(`${f.unknownDays} 天未记录，不补零`)
  if ((f.observedDays || 0) < 3) notes.push('样本少，先核实趋势')
  if ((f.sampleAgeDays || 0) > 7) notes.push(`最近样本距今 ${f.sampleAgeDays} 天`)
  return notes.join(' · ') || `${f.observedDays} 个有记录日 · ${f.spanDays} 天跨度`
}
