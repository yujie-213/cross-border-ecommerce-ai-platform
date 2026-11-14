<script setup lang="ts">
import { computed } from 'vue'
import type { V2Item, PlanPreview } from '../api/v2'
import { fmt, dash } from '../s01'
import { confidenceNote } from '../business'
import SalesBars from './charts/SalesBars.vue'
import BalanceChart from './charts/BalanceChart.vue'
const props = defineProps<{ item: V2Item; plan?: PlanPreview | null; planLoading?: boolean; planError?: string; assumedArrival?: boolean; arrivalDate?: string }>()
const emit = defineEmits<{ retry: [] }>()
const forecast = computed(() => props.item.decision?.forecast)
const days = computed(() => forecast.value?.dailySales || props.item.ruleResult?.forecast.dailySales || [])
const series = computed(() => props.item.decision?.baseline?.series || props.item.ruleResult?.supplyDemand.baseline?.series || [])
const comparison = computed(() => props.item.erpComparison)
const maximum = computed(() => Math.max(1, comparison.value?.platformQuantity || 0, comparison.value?.erpQuantity || 0))
</script>
<template>
  <section class="evidence-section" aria-label="补货判断依据"><div class="section-title"><div><h2>销量与库存</h2></div></div>
    <div class="evidence-grid">
      <article class="panel evidence-chart"><header><h3>销量变化</h3><span v-if="forecast?.available">{{ forecast.totalSales }} 件 / {{ forecast.observedDays }} 个有记录日</span></header><SalesBars v-if="days.length" :days="days" :total="forecast?.totalSales" record-dates-only /><div v-else class="chart-empty">没有可核实的有效销量，暂不绘制趋势。</div><p v-if="forecast?.unknownDays || (forecast?.observedDays || 0) < 3 || (forecast?.sampleAgeDays || 0) > 7">{{ confidenceNote(item) }}</p></article>
      <article class="panel evidence-chart plan-chart" :aria-busy="!!planLoading"><header><h3>补货前后对比</h3><span>{{ item.decision?.horizonDays || '—' }} 天规划周期</span></header><BalanceChart v-if="series.length" :series="series" :plan-series="plan?.evaluation.series" :plan-label="assumedArrival ? '假设补货后' : '按计划补货'" /><div v-else class="chart-empty">当前依据不足，暂不能推算缺货日期。</div><div class="plan-chart-status" aria-live="polite"><span v-if="planLoading" role="status">正在更新计划…</span><template v-else-if="planError"><span class="danger">计划曲线未更新</span><button class="text-action" @click="emit('retry')">重试</button></template><template v-else-if="plan"><b>{{ plan.quantity }} 件 · {{ plan.availableDate.slice(5) }} {{ assumedArrival ? '假设到货' : '预计到货' }}</b><span :class="{danger:plan.evaluation.stockoutRisk}">{{ plan.evaluation.firstShortageDate ? plan.evaluation.firstShortageDate.slice(5)+' 起仍有缺口' : '规划期内未出现缺口' }}</span></template><span v-else-if="series.length && !arrivalDate">填写到货日后查看补货效果</span></div><details v-if="series.length" class="chart-semantics"><summary>查看计算口径</summary><p>负余额表示累计未满足需求，不是物理负库存。计划曲线按所选数量与日期计算，不代表已确认在途；未抵扣日期待核实的已有采购。</p></details></article>
    </div>
    <article class="panel erp-comparison"><div><h3>ERP 建议对比</h3></div><div class="compare-values"><div><span>平台参考补充</span><strong>{{ dash(comparison?.platformQuantity ?? item.decision?.referenceReplenishmentQuantity) }}<small> 件</small></strong><i :style="{width: Math.max(0,(comparison?.platformQuantity || 0)/maximum*100)+'%'}" /></div><div><span>ERP 原有建议</span><strong>{{ comparison?.erpQuantity ?? (comparison?.status === 'ERP_AMBIGUOUS' ? '存在冲突' : '未提供') }}<small v-if="comparison?.erpQuantity != null"> 件</small></strong><i class="erp-bar" :style="{width: Math.max(0,(comparison?.erpQuantity || 0)/maximum*100)+'%'}" /></div></div><div class="compare-delta"><span>平台 − ERP</span><strong>{{ comparison?.difference != null ? (comparison.difference > 0 ? '+' : '') + fmt(comparison.difference,0) : '—' }}</strong><small v-if="comparison?.significant">差异明显，需核对口径</small></div></article>
  </section>
</template>
