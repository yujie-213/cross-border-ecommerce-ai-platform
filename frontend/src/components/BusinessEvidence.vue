<script setup lang="ts">
import { computed } from 'vue'
import type { V2Item } from '../api/v2'
import { fmt, dash } from '../s01'
import { confidenceNote } from '../business'
import SalesBars from './charts/SalesBars.vue'
import BalanceChart from './charts/BalanceChart.vue'
const props = defineProps<{ item: V2Item }>()
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
      <article class="panel evidence-chart"><header><h3>库存将如何变化</h3><span>{{ item.decision?.horizonDays || '—' }} 天规划周期</span></header><BalanceChart v-if="series.length" :series="series" /><div v-else class="chart-empty">当前依据不足，暂不能推算缺货日期。</div><p>预测未计入到货日期待核实的在途。</p></article>
    </div>
    <article class="panel erp-comparison"><div><h3>ERP 建议对比</h3></div><div class="compare-values"><div><span>平台参考补充</span><strong>{{ dash(comparison?.platformQuantity ?? item.decision?.referenceReplenishmentQuantity) }}<small> 件</small></strong><i :style="{width: Math.max(0,(comparison?.platformQuantity || 0)/maximum*100)+'%'}" /></div><div><span>ERP 原有建议</span><strong>{{ comparison?.erpQuantity ?? (comparison?.status === 'ERP_AMBIGUOUS' ? '存在冲突' : '未提供') }}<small v-if="comparison?.erpQuantity != null"> 件</small></strong><i class="erp-bar" :style="{width: Math.max(0,(comparison?.erpQuantity || 0)/maximum*100)+'%'}" /></div></div><div class="compare-delta"><span>平台 − ERP</span><strong>{{ comparison?.difference != null ? (comparison.difference > 0 ? '+' : '') + fmt(comparison.difference,0) : '—' }}</strong><small v-if="comparison?.significant">差异明显，需核对口径</small></div></article>
  </section>
</template>
