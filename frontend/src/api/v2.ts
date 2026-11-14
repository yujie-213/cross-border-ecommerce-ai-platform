import type { AI, Task, Requisition, Forecast, Evaluation } from './types'
/** D03 public admission projection, sealed in the immutable result manifest. */
export interface QualityEntry { status: string; reasons: string[] }
export interface Capability { enabled: boolean; reasons: string[] }
export interface V2DemandWindow {
  windowStart: string; windowEnd: string; validDays: number; missingDays: number
  referenceAverage: string | null; referenceDays: number; sampleStart: string | null; sampleEnd: string | null
  referenceGrade: string; observedHistory: { businessDate: string; quantity: string; orderRef: string }[]
}
export interface V2Admission {
  admissionVersion?: string
  dataQuality?: Record<'identity' | 'demand' | 'inventory' | 'procurement', QualityEntry>
  riskResult?: Evaluation | null
  capabilities?: {
    facts: Capability; reference: Capability; risk: Capability; rules: Capability
    requisition: Capability & { permissionCheck?: string }
  }
}
export interface V2Item extends V2Admission {
  decisionVersion?: string; decision?: ProductDecision; erpComparison?: ERPComparison; relatedScopes?: V2Item[]
  productSummary?: { scopeCount: number; storeCount: number; warehouseCount: number; referencePlanTotal: number | null; replenishScopeCount: number; judgedScopeCount: number; riskScopeCount: number; analyzedSkuCount: number; productIds: string[] }
  entityKey: string; sourceTenant: string; productId: string | null; sku: string; name: string
  storeId: string | null; warehouseId: string | null; storeName: string | null; warehouseName: string | null
  identityVerified: boolean; identityIssues: string[]; analysisState: string; sourceGrade: string; quantity: number | null; sourceQuantity?: number | null; unit?: string | null
  inventory?: { available: number | null }; observedAt?: string; snapshotRef?: string; snapshotManifest?: unknown
  riskGroup?: string; riskDate?: string | null; sourceUrgency?: string | null; ruleFailureCodes?: string[]; uncertainties: string[]
  constraints?: { moq: number | null; orderMultiple: number | null; unitPrice: string | null; currency: string | null; minimumAmount: string | null; supplierId: string | null; supplierName?: string | null; quoteNo?: string | null; quoteValidFrom?: string | null; quoteValidTo?: string | null; quoteId: string | null; hardBlocks: string[] }
  procurementEligibility?: { eligible: boolean; hardBlocks: string[]; warnings: string[]; scopeAuthorized?: boolean }
  formalPurchases?: { erpId: string; erpNumber: string; status: string; warehouseName?: string; warehouseMatch?: boolean; orderedQuantity: number | null; receivedQuantity: number | null; unreceivedQuantity: number | null; plannedArrival: string | null; sellableDate: string | null }[]
  sourceSuggestion?: Record<string, unknown> | null
  sourceSuggestions?: Record<string, unknown>[]; sourceSuggestionCount?: number
  ruleResult?: { forecast: Forecast; supplyDemand: { baseline: Evaluation | null } } | null
  demandWindow?: V2DemandWindow | null
  inventoryBasis?: { status: string; observedAt?: string | null; rowUpdatedAt?: string | null; residual?: unknown; issues?: string[]; checkpoint?: { version?: string; evidenceDigest?: string } } | null
  recoveryHints?: { code: string; message: string; action: string }[]
}
export interface ProductForecast {
  available: boolean; reason?: string; sampleStart?: string; sampleEnd?: string; sampleAgeDays?: number
  observedDays?: number; spanDays?: number; unknownDays?: number; orderCount?: number; totalSales?: string
  averageDailyDemand?: string; salesRecordDayAverage?: string; confidence?: string; risks?: string[]; assumption?: string
  dailySales?: { day: string; quantity: string }[]; excluded?: Record<string, number>
}
export interface ProductDecision {
  status: 'REPLENISH' | 'NO_REPLENISHMENT' | 'NEEDS_REVIEW'; forecast: ProductForecast; horizonDays: number; leadDays: number | null
  horizonBasis: string; forecastQuantity: string | null; referenceReplenishmentQuantity: number | null; purchasableQuantity: number | null
  confirmedSupplyQuantity: number | null; coverageDays: string | null; firstShortageDate: string | null; stockoutRisk: boolean
  confidence: string; assumptions: string[]; explanation: string[]; baseline: Evaluation | null
  scenarios: { days: number; forecastQuantity: string; recordDayScenarioQuantity: string; referenceReplenishmentQuantity: number | null }[]
}
export interface ERPComparison { status: string; platformQuantity: number | null; erpQuantity: number | null; difference: number | null; significant: boolean; recordCount: number; explanation: string }
export interface V2Options { enabled: boolean; analysisRange?: string; sourceTenant: string; singleAIEnabled: boolean; canSubmit: boolean; principalRef: { tenantId: string; principalId: string } }
export interface V2Summary { forecastScopeCount?: number; analyzedSkuCount?: number; judgedSkuCount?: number; judgedScopeCount?: number; replenishSkuCount?: number; replenishScopeCount?: number; noReplenishmentSkuCount?: number; noReplenishmentScopeCount?: number; reviewSkuCount?: number; reviewScopeCount?: number; riskSkuCount?: number; riskScopeCount?: number; erpDifferenceSkuCount?: number; erpDifferenceScopeCount?: number; forecastCoverage?: number; decisionCoverage?: number; discoveredSkuCount: number; scopeObjectCount: number; processedCount: number; ruleCalculated: number; erpReference: number; historicalReference?: number; noReplenishment: number; unanalyzable: number; failed: number; unfinished: number; coverage: number; processingCoverage: number; modelCalls: number; businessMutations: number }
export interface V2Progress { analysisRange?: string; task: Task; summary: V2Summary; statisticsVersion?: string; enumerationComplete: boolean | null; sourceLimits?: Record<string, { complete: boolean; total?: number; error?: string }> }
export interface V2List { total: number; items: V2Item[]; stores: [string, string][]; warehouses: [string, string][] }
export interface V2Single { task: Task; report: { dataReport: { item: V2Item }; analysisReport: { ai: AI } } | null }
export interface PendingV2 { key: string; path: string; body: object; kind: 'batch' | 'single' | 'requisition' | 'cancel'; createdAt: string; displayHint?: string }
export const sourceLabel = (v: string) => ({ PLATFORM_REFERENCE: '平台独立试算', DEMAND_REFERENCE: '独立需求预测', RULE_CALCULATED: '平台规则计算', REFERENCE_ONLY: 'ERP 参考建议', HISTORICAL_REFERENCE: '历史销量参考', USABLE_FALLBACK: '已核验降级来源', UNAVAILABLE: '无可用来源', UNVERIFIED: '来源待核实' }[v] || v)
export const stateLabel = (v: string) => ({ PENDING: '等待处理', ANALYZED: '规则建议', ERP_REFERENCE: 'ERP 参考建议', HISTORICAL_REFERENCE: '历史参考分析', NO_REPLENISHMENT: '规则判断无需补货', NEEDS_REVIEW: '需要核实', UNANALYZABLE: '无法分析', FAILED: '分析失败' }[v] || v)
export function quantityError(item: V2Item, quantity: number, reason: string) {
  const c = item.constraints
  if (!c || !c.moq || !c.orderMultiple || !Number.isSafeInteger(quantity) || quantity <= 0 || quantity > 100000 || quantity < c.moq || quantity % c.orderMultiple) return '数量须为正整数，并同时满足 MOQ 和整箱倍数。'
  if (quantity !== item.quantity && !reason.trim()) return '调整数量时请填写原因。'
  return ''
}
export type V2Requisition = Requisition & { sourceGrade?: string; sourceAcknowledged?: boolean; sourceUncertainties?: string[] }
const issueLabels: Record<string, string> = {
  PROCUREMENT_LEAD_UNCONFIRMED: '采购交期未确认；当前需求采用明确规划假设', REGISTERED_RECORD_MISSING: '登记记录未返回，请核对源数据',
  REGISTERED_RELATION_MISSING: '登记店仓关系未完整回读', V2_REGISTERED_SCOPE_CHANGED: '登记范围已改变，请重新检查自有商品',
  V2_BUSINESS_SCOPE_NOT_REGISTERED: '该商品店仓未登记为本项目成员', SALES_ENUMERATION_INCOMPLETE: '登记销售未完整读取，当前仅部分样本',
  AI_FACT_CONTEXT_INVALID: '解释事实校验未通过，规则结论仍可查看',

  DEMAND_DAY_COVERAGE_INCOMPLETE: '部分日期尚不能作为完整预测样本，当前提供历史参考', STOCK_MOVEMENT_COVERAGE_INCOMPLETE: '库存流水未完整读取，当前库存仅为ERP读取值',
  INVENTORY_BUCKET_RELATION_UNCONFIRMED: '存在多条库存记录，未证明可相加；库存总量待核实', INVENTORY_QUANTITY_UNCONFIRMED: '库存数量未满足有效非负整数要求',
  NO_ATOMIC_CROSS_INTERFACE_SNAPSHOT: '各接口分时读取，可能存在数据时差', SELLABLE_ETA_UNKNOWN: '实际到货可售日期未确认',
  FORMAL_PURCHASE_DEDUCTION_UNCONFIRMED: '已有正式采购未确认有效供给，未抵扣', ERP_ALGORITHM_UNKNOWN: 'ERP 内部计算依据未知',
  ERP_DAILY_SALES_WINDOW_UNKNOWN: 'ERP 日均销量统计窗口未知', ERP_GENERATION_TIME_UNVERIFIED: '源生成时间语义未确认', ERP_PURCHASE_NETTING_UNKNOWN: 'ERP 建议是否已计入采购未知',
  OVERSEAS_FBA_BUCKETS_NOT_ADDED: '海外与 FBA 库存可能同源，未重复相加', RELATED_PURCHASE_TARGETS_DIFFERENT_WAREHOUSE: '存在同 SKU 其他仓采购，转仓关系需核实',
  RULE_CONSTRAINTS_INCOMPLETE: '采购约束不完整，未执行规则计算', RULE_HISTORY_COVERAGE_INCOMPLETE: '经营历史或库存覆盖不完整',
  FULFILLED_SALES_HISTORY_UNPROVEN: '缺少可独立核验的履约销售历史', SALES_NOT_NET_FULFILLED: '销售的支付、发货或退款状态未满足核验条件',
  BUSINESS_SCOPE_UNRESOLVED: '店铺、仓库或商品归属未确认', IDENTITY_MAPPING_UNVERIFIED: '业务身份关联未核验',
  EFFECTIVE_QUOTE_MISSING_OR_AMBIGUOUS: '没有唯一有效供应商报价', SUPPLIER_RELATION_MISSING: '供应商关联缺失',
  PROCUREMENT_UNIT_UNCONFIRMED: '采购单位未确认', CARTON_QUANTITY_MISSING_OR_INVALID: '缺少合法整箱倍数', QUOTE_MOQ_INVALID: '报价最小起订量不合法',
  QUOTE_PRICE_INVALID: '报价金额不合法', QUOTE_CURRENCY_UNCONFIRMED: '报价币种未确认', QUOTE_QUERY_INCOMPLETE: '报价查询未完整完成',
  FORMAL_PURCHASE_QUERY_INCOMPLETE: '已有正式采购查询未完整完成', NO_POSITIVE_RECOMMENDATION_BASIS: '没有可靠正数量采购依据',
  KNOWN_FORMAL_PURCHASE_FOR_SOURCE_PLAN: '该源建议已有正式采购，请先核对已有单据',
  SUGGESTION_AMBIGUOUS_OR_QUERY_INCOMPLETE: '建议存在多条冲突记录或读取不完整', SUGGESTION_WAREHOUSE_OR_PRODUCT_UNRESOLVED: '建议无法唯一关联商品或仓库',
  PRODUCT_IDENTITY_AMBIGUOUS: '商品标识存在歧义', STORE_IDENTITY_AMBIGUOUS: '店铺归属存在歧义', WAREHOUSE_IDENTITY_AMBIGUOUS: '仓库归属存在歧义',
  NO_UNIQUE_STORE_WAREHOUSE_RELATION: '未建立唯一店仓业务关系', OPENING_AND_LEDGER_COVERAGE_UNPROVEN: '期初库存与完整流水未核验',
  SOURCE_FIELDS_INVALID: '源数据字段不符合约定', MODEL_NOT_ENABLED: '模型未启用', MODEL_ALLOWANCE_UNAVAILABLE: '当前模型额度不可用',
}
export const issueLabel = (code: string) => issueLabels[code] || (code.startsWith('IDENTITY_ENUMERATION_INCOMPLETE:') ? '身份目录未完整读取' : `资料待核实（${code}）`)
export const unitLabel = (unit?: string | null) => unit === 'EA' ? '件' : '单位未确认'
