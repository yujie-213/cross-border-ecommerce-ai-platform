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
const facts = computed(() => baseline.value ? [
  ['当前可用库存', baseline.value.availableQuantity, '件'], ['已有在途 / 计划供给', baseline.value.inTransitQuantity, '件'],
  ['窗口需求（含缓冲）', baseline.value.targetQuantity, '件'], ['总量缺口', baseline.value.gapQuantity, '件'],
] : [])
</script>
<template>
  <div class="detail-top"><div><div class="eyebrow">S01 / REPORT</div><h1>{{ report.scope.canonicalSkuIds.join('、') }}</h1><p class="subtitle">{{ report.scope.storeIds.join('、') }} / {{ report.scope.warehouseIds.join('、') }} · 分析时点 {{ shown(data.scenarioSupplement.asOf) }}</p></div><StatusBadge :value="report.completeness" /></div>
  <Notice tone="warning" :title="sourceText(report.sourceNature)"><p class="mono wrap">{{ report.sourceNature }}</p>仅教学 / 只读复核，企业正式四项门禁保持 BLOCKED，当前结果不可作为正式采购依据。</Notice>
  <Panel v-if="data.acquisition" title="本次 ERP 在线采集" note="历史报告始终读取本次快照">
    <dl class="metadata"><dt>采集标识</dt><dd>{{ data.acquisition.acquisitionId }}</dd><dt>开始 / 完成</dt><dd>{{ data.acquisition.startedAt }} / {{ data.acquisition.completedAt }}</dd><dt>映射版本</dt><dd>{{ data.acquisition.mappingVersion }}</dd></dl>
    <div v-for="(item, name) in data.acquisition.interfaces" :key="name" class="key-value"><span>{{ name }}</span><strong>{{ item.error || (item.complete ? '读取完整' : '覆盖不完整') }}<template v-if="item.total !== undefined"> · {{ item.total }} 条</template></strong></div>
    <p class="micro-note">教学 ERP 只读网络采集，多接口不保证原子时点；采集时间不代表业务数据新鲜。缺失与失败不按零处理。</p>
    <div v-for="domain in data.observedDomains || []" :key="domain.domain"><template v-if="domain.measurements.length"><p>{{ domain.domain }} · {{ domain.state }} · 源时点 {{ domain.sourceTimes.join('、') || '未知' }}</p><p v-for="(measurement, i) in domain.measurements" :key="i">{{ measurement.field }}：{{ shown(measurement.value) }}（{{ measurement.unit }}，ERP 原字段观测，业务语义仍须核实）</p></template></div>
  </Panel>
  <div class="detail-grid"><div>
    <Panel title="供需与补货分析" note="服务端 B01 / B02 计算结果">
      <div v-if="baseline" class="summary-grid"><div v-for="[name, value, unit] in facts" :key="name" class="summary-item"><small>{{ name }}</small><strong>{{ value }} <span>{{ unit }}</span></strong></div></div>
      <Notice v-else tone="danger" title="基线不可计算">关键数据不足或质量阻断。未知值不按零处理，请核实下方质量问题。</Notice>
      <div v-if="baseline" class="facts"><div class="fact"><span>首次预计缺货</span><strong>{{ baseline.firstShortageDate || '窗口内未发现' }}</strong></div><div class="fact"><span>中途缺货风险</span><strong :class="{ 'danger-text': baseline.stockoutRisk }">{{ baseline.stockoutRisk ? '存在' : '未发现' }}</strong></div><div class="fact"><span>平均日需求 / 件</span><strong>{{ baseline.averageDailyDemand }}</strong></div><div class="fact"><span>期末供需余额 / 件</span><strong>{{ baseline.closingBalance }}</strong></div></div>
      <div v-if="!baseline && data.reliableFacts?.inventory?.length" class="facts"><div v-for="(row, i) in data.reliableFacts.inventory" :key="i" class="fact"><span>可信库存（{{ row.unit }}）</span><strong>{{ row.availableQuantity }}<small>{{ row.sourceUpdatedAt }}</small></strong></div></div>
      <div class="spacer" />
      <InventoryChart v-if="baseline" :baseline="baseline" :candidates="data.supplyDemand.candidates" />
    </Panel>
    <Panel title="质量、限制与风险" note="质量与 AI 状态独立">
      <Notice v-for="(issue, i) in data.quality" :key="i" :tone="issue.severity === 'BLOCK' ? 'danger' : 'warning'" :title="issue.code"><p>{{ issue.message || issue.path }}</p><p>字段：{{ issue.path }} · 严重度：{{ issue.severity }}。请数据 / 质量负责人核实后重新分析。</p></Notice>
      <p v-if="!data.quality.length" class="muted">本报告未返回质量问题，不代表企业业务准入已通过。</p>
      <ul class="limitations"><li v-for="limit in data.supplyDemand.limitations" :key="limit">{{ label(limit) }}<small class="mono">{{ limit }}</small></li><li v-for="rule in data.scenarioSupplement.unverifiedRules || []" :key="rule">{{ label(rule) }}</li></ul>
      <p class="micro-note">需求方法：{{ shown(data.supplyDemand.demandMethod) }}。已有供给以报告口径展示；教学计划供给不等同于真实已下单在途。</p>
    </Panel>
    <Panel title="解释与模型用量"><AIExplanation :ai="report.analysisReport.ai" /></Panel>
    <Panel title="报告证据" note="每次打开均按当前权限解析">
      <div v-if="!data.evidence.length" class="empty compact">本报告未提供可解析证据。</div>
      <div v-for="ev in data.evidence" :key="ev.evidenceId" class="source-item"><div><b>{{ ev.fieldPath }}</b><small class="mono wrap">{{ ev.evidenceId }}</small></div><button class="evidence-link" @click="$emit('evidence', ev.evidenceId)">查看证据</button></div>
    </Panel>
  </div><aside>
    <Panel title="补货候选" note="未经采购批准">
      <template v-if="data.supplyDemand.candidates.length"><div v-for="(candidate, i) in data.supplyDemand.candidates" :key="candidate.candidateId" class="candidate"><h3>候选 {{ i + 1 }}</h3><div class="big">{{ candidate.quantity }} <small>件</small></div><div class="key-value"><span>可售日期</span><strong>{{ candidate.availableDate }}</strong></div><div class="key-value"><span>最早缺货</span><strong>{{ candidate.evaluation.firstShortageDate || '窗口内未发现' }}</strong></div><Notice v-if="candidate.evaluation.stockoutRisk" tone="warning" title="到货前风险仍存在">期末余额 {{ candidate.evaluation.closingBalance }} 件，不代表全程无缺货。</Notice><p class="micro-note">约束版本：{{ candidate.constraintVersion }}。当前公开 API 不提供 MOQ / 订购倍数数值，无法在此核实。</p></div></template>
      <Notice v-else title="未生成补货候选">{{ baseline && !baseline.stockoutRisk && baseline.gapQuantity === '0' ? '当前窗口无需补货。无候选不等于生成 0 件采购订单。' : '候选缺失的原因请查看质量与限制；不能推断候选量为零。' }}</Notice>
      <Notice tone="danger" title="采购适用性：不可用于正式采购">只读教学分析；采购确认、审批和执行尚未开放。</Notice>
    </Panel>
    <Panel title="版本与追溯"><dl class="metadata"><dt>本次任务</dt><dd>{{ report.taskRef.taskId }}</dd><dt>本次报告</dt><dd>{{ report.reportRef.reportId }}</dd><dt>快照</dt><dd>{{ report.snapshotRef }}</dd><dt>计划 / 场景 / 契约版本</dt><dd>{{ report.planVersion }} / {{ report.scenarioVersion }} / {{ report.contractVersion }}</dd><dt>规则版本</dt><dd>{{ shown(data.scenarioSupplement.ruleVersion) }}</dd><dt>固定 packageRef</dt><dd>{{ data.scenarioSupplement.packageRef }}</dd><dt>前序报告</dt><dd>{{ data.scenarioSupplement.previousReportRef?.reportId || '无' }}</dd><dt>企业准入</dt><dd>{{ data.scenarioSupplement.realAdmission }}</dd></dl></Panel>
  </aside></div>
</template>
