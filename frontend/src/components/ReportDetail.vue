<script setup lang="ts">
import { computed } from 'vue'
import type { Report } from '../api/types'
import { label, shown, sourceText } from '../domain'
import Panel from './Panel.vue'
import Notice from './Notice.vue'
import StatusBadge from './StatusBadge.vue'
import InventoryChart from './InventoryChart.vue'
import AIExplanation from './AIExplanation.vue'
const props = defineProps<{ report: Report }>()
defineEmits<{ evidence: [id: string] }>()
const data = computed(() => props.report.dataReport)
const baseline = computed(() => data.value.supplyDemand.baseline)
const legacyOwned = computed(() => !!data.value.scenarioSupplement.monitoring && !!data.value.forecast && data.value.forecast.constraints.wholeCartonRequired !== true)
const issues = computed(() => data.value.quality.filter((item, index, all) => all.findIndex(x => x.code === item.code && x.path === item.path) === index))
const facts = computed(() => baseline.value ? [
  ['当前可用库存', baseline.value.availableQuantity, '件'], ['计入计算的已有供给', baseline.value.inTransitQuantity, '件'],
  ['窗口需求（含缓冲）', baseline.value.targetQuantity, '件'], ['总量缺口', baseline.value.gapQuantity, '件'],
] : [])
</script>
<template>
  <div class="detail-top"><div><div class="eyebrow">S01 / REPORT</div><h1>{{ report.scope.canonicalSkuIds.join('、') }}</h1><p class="subtitle">{{ report.scope.storeIds.join('、') }} / {{ report.scope.warehouseIds.join('、') }} · 分析时点 {{ shown(data.scenarioSupplement.asOf) }}</p></div><StatusBadge :value="report.completeness" /></div>
  <Notice tone="warning" :title="sourceText(report.sourceNature)"><p class="mono wrap">{{ report.sourceNature }}</p>仅教学 / 只读复核，企业正式四项门禁保持 BLOCKED，当前结果不可作为正式采购依据。</Notice>
  <Notice v-if="legacyOwned" tone="danger" title="历史规则报告 · 采购候选已失效">本快照采用整箱规则确认前的参数，旧候选和 AI 解释仅为历史证据，不能作为当前有效建议。请基于此报告重新分析，按 ERP 有效报价 MOQ 与商品箱规生成新候选。</Notice>
  <Panel v-if="data.acquisition" title="本次 ERP 在线采集" note="历史报告始终读取本次快照">
    <details><summary>查看采集明细与来源</summary><dl class="metadata"><dt>采集标识</dt><dd>{{ data.acquisition.acquisitionId }}</dd><dt>开始 / 完成</dt><dd>{{ data.acquisition.startedAt }} / {{ data.acquisition.completedAt }}</dd><dt>映射版本</dt><dd>{{ data.acquisition.mappingVersion }}</dd></dl>
    <div v-for="(item, name) in data.acquisition.interfaces" :key="name" class="key-value"><span>{{ name }}</span><strong>{{ item.error || (item.complete ? '读取完整' : '覆盖不完整') }}<template v-if="item.total !== undefined"> · {{ item.total }} 条</template></strong></div>
    <p class="micro-note">教学 ERP 只读网络采集，多接口不保证原子时点；采集时间不代表业务数据新鲜。缺失与失败不按零处理。</p>
    <div v-for="domain in data.observedDomains || []" :key="domain.domain"><template v-if="domain.measurements.length"><p>{{ domain.domain }} · {{ domain.state }} · 源时点 {{ domain.sourceTimes.join('、') || '未知' }}</p><p v-for="(measurement, i) in domain.measurements" :key="i">{{ measurement.field }}：{{ shown(measurement.value) }}（{{ measurement.unit }}，ERP 原字段观测，业务语义仍须核实）</p></template></div></details>
  </Panel>
  <Panel v-if="data.forecast" title="需求预测与 ERP 采购约束" note="最近完整业务日 · 可配置 SMA 策略">
    <p>{{ data.forecast.windowStart }} — {{ data.forecast.windowEnd }}（{{ data.forecast.timezone }}）：{{ data.forecast.observationDays }} 个完整业务日，共销售 {{ data.forecast.totalSales }} 件，日均 {{ Number(data.forecast.averageDailyDemand).toFixed(4) }} 件。</p>
    <p>未来 {{ data.forecast.forecastDays }} 日基础需求 {{ Number(data.forecast.forecastQuantity).toFixed(4) }} 件；ERP 交期 {{ data.forecast.leadDays }} 天 + 补货覆盖 {{ data.forecast.coverageDays }} 天，本次供需计算覆盖 {{ data.forecast.calculationHorizonDays }} 天。</p>
    <table><thead><tr><th>业务日期</th><th>已履约销量 / 件</th></tr></thead><tbody><tr v-for="day in data.forecast.dailySales" :key="day.day"><td>{{ day.day }}</td><td>{{ day.quantity }}</td></tr></tbody></table>
    <p v-if="data.forecast.constraints.wholeCartonRequired">有效报价 v{{ data.forecast.constraints.quoteVersion }}：MOQ {{ data.forecast.constraints.moq }} 件；ERP 箱规 / 采购订购倍数 {{ data.forecast.constraints.orderMultiple }} 件/箱，必须整箱采购。来源：{{ data.forecast.constraints.moqSource }}、{{ data.forecast.constraints.orderMultipleSource }}；业务规则 {{ data.forecast.constraints.ruleVersion }}。</p>
    <p v-else>历史有效报价 v{{ data.forecast.constraints.quoteVersion }}：MOQ {{ data.forecast.constraints.moq }} 件；当时独立订购倍数{{ data.forecast.constraints.orderMultiple || '未确认' }}，整数件取整不代表符合当前整箱规则。</p>
    <p v-if="data.forecast.constraints.wholeCartonRequired" class="micro-note">其他采购条件尚未确认：报价交期不代表承诺可售日期；审批、到货质检 / 上架耗时仍须复核。需求从采集业务日次日计算，未覆盖采集当日剩余需求。</p>
    <p>库存对账：期初 {{ data.forecast.stockReconciliation.openingQuantity }} − 已履约 {{ data.forecast.stockReconciliation.fulfilledQuantity }} = 当前可用 {{ data.forecast.stockReconciliation.availableQuantity }} 件（{{ data.forecast.stockReconciliation.status }}）。历史业务日与实际付款、出库过账日分别保存，未回写系统时间。</p>
    <Notice v-for="item in data.forecast.excludedSupply" :key="item.orderRef" tone="warning" title="未计入有效在途">{{ item.status }}采购的 pending 数量 {{ item.pendingQuantity }} 件尚未生效，不能抵扣需求缺口。</Notice>
    <p v-if="data.scenarioSupplement.monitoring" class="micro-note">自有监控数据集 {{ data.scenarioSupplement.monitoring.datasetId }} · scopeVersion {{ data.scenarioSupplement.monitoring.scopeVersion }} · 仅已登记并独立核验成员。</p>
  </Panel>
  <Panel v-if="data.existingPurchases" title="ERP 已审批正式采购" note="只发现有效正式状态 · 不检查未审批单">
    <p v-if="!data.existingPurchases.items.length">本次未发现归属已确认的有效正式采购。覆盖：{{ data.existingPurchases.coverage }}。</p>
    <Notice v-if="data.existingPurchases.unresolvedScopeCount" tone="warning" title="正式采购归属待核实">有 {{ data.existingPurchases.unresolvedScopeCount }} 张关联 SKU 的正式采购无法确认店铺或销售备货用途，未作为本范围供给。</Notice>
    <div v-for="item in data.existingPurchases.items" :key="item.erpId + ':' + item.lineIndex" class="source-item"><div><b>{{ item.erpNumber }} / ERP ID {{ item.erpId }} / {{ item.status }}</b><p>{{ item.sku }}：采购 {{ item.orderedQuantity ?? '未知' }} / 已收 {{ item.receivedQuantity ?? '未知' }} / 未收 {{ item.unreceivedQuantity ?? '未知' }} 件。</p><p>计划到货 {{ item.plannedArrival || '未知' }}；可售日期 {{ item.sellableDate || '未知' }}；{{ item.includedInCalculation ? '已纳入计算' : '未抵扣供给' }}。</p></div></div>
    <p class="micro-note">ERP 计划到货不是可售日期。有效剩余量、关闭规则或可售时间未确认时，不将原始采购总量作为在途；报告仍展示相关限制。</p>
  </Panel>
  <div class="detail-grid"><div>
    <Panel title="供需与补货分析" note="服务端 B01 / B02 计算结果">
      <div v-if="baseline" class="summary-grid"><div v-for="[name, value, unit] in facts" :key="name" class="summary-item"><small>{{ name }}</small><strong>{{ value }} <span>{{ unit }}</span></strong></div></div>
      <Notice v-else tone="danger" title="基线不可计算">关键数据不足或质量阻断。未知值不按零处理，请核实下方质量问题。</Notice>
      <div v-if="baseline" class="facts"><div class="fact"><span>首次预计缺货</span><strong>{{ baseline.firstShortageDate || '窗口内未发现' }}</strong></div><div class="fact"><span>中途缺货风险</span><strong :class="{ 'danger-text': baseline.stockoutRisk }">{{ baseline.stockoutRisk ? '存在' : '未发现' }}</strong></div><div class="fact"><span>平均日需求 / 件</span><strong>{{ baseline.averageDailyDemand }}</strong></div><div class="fact"><span>期末供需余额 / 件</span><strong>{{ baseline.closingBalance }}</strong></div></div>
      <div v-if="!baseline && data.reliableFacts?.inventory?.length" class="facts"><div v-for="(row, i) in data.reliableFacts.inventory" :key="i" class="fact"><span>可信库存（{{ row.unit }}）</span><strong>{{ row.availableQuantity }}<small>{{ row.sourceUpdatedAt }}</small></strong></div></div>
      <div class="spacer" />
      <InventoryChart v-if="baseline" :baseline="baseline" :candidates="legacyOwned ? [] : data.supplyDemand.candidates" />
    </Panel>
    <Panel title="质量、限制与风险" note="质量与 AI 状态独立">
      <Notice v-for="(issue, i) in issues" :key="i" :tone="issue.severity === 'BLOCK' ? 'danger' : 'warning'" :title="issue.code"><p>{{ issue.message || issue.path }}</p><p>字段：{{ issue.path }} · 严重度：{{ issue.severity }}。请数据 / 质量负责人核实后重新分析。</p></Notice>
      <p v-if="!data.quality.length" class="muted">本报告未返回质量问题，不代表企业业务准入已通过。</p>
      <ul class="limitations"><li v-for="limit in data.supplyDemand.limitations" :key="limit">{{ label(limit) }}<small class="mono">{{ limit }}</small></li><li v-for="rule in data.scenarioSupplement.unverifiedRules || []" :key="rule">{{ label(rule) }}</li></ul>
      <p class="micro-note">需求方法：{{ label(data.supplyDemand.demandMethod || '未知') }}。已有供给以报告口径展示；教学计划供给不等同于真实已下单在途。</p>
    </Panel>
    <Panel :title="legacyOwned ? '历史解释与模型用量（旧规则）' : '解释与模型用量'"><AIExplanation :ai="report.analysisReport.ai" /></Panel>
    <Panel title="报告证据" note="每次打开均按当前权限解析">
      <div v-if="!data.evidence.length" class="empty compact">本报告未提供可解析证据。</div>
      <div v-for="ev in data.evidence" :key="ev.evidenceId" class="source-item"><div><b>{{ ev.fieldPath }}</b><small class="mono wrap">{{ ev.evidenceId }}</small></div><button class="evidence-link" @click="$emit('evidence', ev.evidenceId)">查看证据</button></div>
    </Panel>
  </div><aside>
    <Panel title="补货候选" note="未经采购批准">
      <Notice v-if="legacyOwned" tone="warning" title="旧规则候选已失效">请重新分析以获取满足 MOQ 和整箱要求的候选；历史快照仍保留用于追溯。</Notice>
      <template v-else-if="data.supplyDemand.candidates.length"><div v-for="(candidate, i) in data.supplyDemand.candidates" :key="candidate.candidateId" class="candidate"><h3>候选 {{ i + 1 }}</h3><div class="big">{{ candidate.quantity }} <small>件<template v-if="data.forecast?.constraints.wholeCartonRequired">（{{ Number(candidate.quantity) / Number(data.forecast.constraints.orderMultiple) }} 箱）</template></small></div><div class="key-value"><span>建议可售日期</span><strong>{{ candidate.availableDate }}</strong></div><div class="key-value"><span>最早缺货</span><strong>{{ candidate.evaluation.firstShortageDate || '窗口内未发现' }}</strong></div><Notice v-if="candidate.evaluation.stockoutRisk" tone="warning" title="到货前风险仍存在">期末余额 {{ candidate.evaluation.closingBalance }} 件，不代表全程无缺货。</Notice><p class="micro-note">约束版本：{{ candidate.constraintVersion }}。{{ data.forecast?.constraints.wholeCartonRequired ? 'MOQ 与整箱倍数见 ERP 采购约束；日期仍为假设，质量和审批条件未解除。' : '当前公开 API 不提供已确认的 MOQ / 订购倍数，无法在此核实。' }}</p></div></template>
      <Notice v-else title="未生成补货候选">{{ baseline && !baseline.stockoutRisk && baseline.gapQuantity === '0' ? '当前窗口无需补货。无候选不等于生成 0 件采购订单。' : '候选缺失的原因请查看质量与限制；不能推断候选量为零。' }}</Notice>
      <Notice tone="danger" title="采购适用性：不可用于正式采购">企业准入仍未开放；已授权教学范围可在下方人工确认并提交 ERP 请购，等待 ERP 领导审批。</Notice>
    </Panel>
    <Panel title="版本与追溯"><dl class="metadata"><dt>本次任务</dt><dd>{{ report.taskRef.taskId }}</dd><dt>本次报告</dt><dd>{{ report.reportRef.reportId }}</dd><dt>快照</dt><dd>{{ report.snapshotRef }}</dd><dt>计划 / 场景 / 契约版本</dt><dd>{{ report.planVersion }} / {{ report.scenarioVersion }} / {{ report.contractVersion }}</dd><dt>规则版本</dt><dd>{{ shown(data.scenarioSupplement.ruleVersion) }}</dd><dt>固定 packageRef</dt><dd>{{ data.scenarioSupplement.packageRef }}</dd><dt>前序报告</dt><dd>{{ data.scenarioSupplement.previousReportRef?.reportId || '无' }}</dd><dt>企业准入</dt><dd>{{ data.scenarioSupplement.realAdmission }}</dd></dl></Panel>
  </aside></div>
</template>
