<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Evaluation, Candidate } from '../api/types'
const props = defineProps<{ baseline: Evaluation; candidates: Candidate[] }>()
const table = ref(false)
const lines = computed(() => [{ name: '原有供需基线', series: props.baseline.series }, ...props.candidates.map((c, i) => ({ name: `候选 ${i + 1} · ${c.quantity} 件 · ${c.availableDate}`, series: c.evaluation.series }))])
const days = computed(() => [...new Set(lines.value.flatMap(l => l.series.map(p => p.day)))].sort())
const bounds = computed(() => { const values = lines.value.flatMap(l => l.series.map(p => Number(p.closingBalance))).filter(Number.isFinite); return { min: Math.min(0, ...values), max: Math.max(1, ...values) } })
const x = (day: string) => 55 + (days.value.length <= 1 ? 0 : days.value.indexOf(day) / (days.value.length - 1) * 570)
const y = (value: number) => 185 - (value - bounds.value.min) / (bounds.value.max - bounds.value.min) * 150
const points = (series: Evaluation['series']) => series.map(p => `${x(p.day)},${y(Number(p.closingBalance))}`).join(' ')
const colors = ['#71808e', '#126b65', '#315e8f', '#8a510b']
</script>
<template>
  <div class="section-head"><h3>逐日供需余额 <small class="muted">单位：件</small></h3><button class="button small" :aria-expanded="table" @click="table = !table">{{ table ? '收起数据表' : '查看等价数据表' }}</button></div>
  <svg v-if="days.length" class="chart" viewBox="0 0 660 230" role="img" aria-label="逐日供需余额图。负余额为累计未满足需求，详见等价数据表。">
    <line x1="55" x2="625" :y1="y(0)" :y2="y(0)" stroke="#8996a3" stroke-dasharray="4 4" />
    <g v-for="v in [bounds.max, bounds.min]" :key="v"><line x1="55" x2="625" :y1="y(v)" :y2="y(v)" stroke="#e0e5eb" /><text x="45" :y="y(v) + 4" text-anchor="end">{{ v }}</text></g>
    <g v-for="(line, i) in lines" :key="line.name"><polyline :points="points(line.series)" fill="none" :stroke="colors[i % colors.length]" stroke-width="2.5" :stroke-dasharray="i === 0 ? '5 4' : undefined" /><circle v-for="p in line.series" :key="p.day" :cx="x(p.day)" :cy="y(Number(p.closingBalance))" r="3" :fill="colors[i % colors.length]"><title>{{ line.name }} · {{ p.day }}：{{ p.closingBalance }} 件</title></circle></g>
    <text v-for="day in days" :key="day" :x="x(day)" y="212" text-anchor="middle">{{ day.slice(5) }}</text>
  </svg>
  <div class="legend"><span v-for="(line, i) in lines" :key="line.name"><i :style="{ background: colors[i % colors.length] }" />{{ line.name }}</span></div>
  <p class="chart-caption">负余额表示累计未满足需求，并非真实物理负库存。期末转正仍可能存在到货前的中途缺货风险。</p>
  <div v-if="table" class="table-scroll"><table><caption class="sr-only">与曲线完全相同的服务端逐日数据</caption><thead><tr><th>方案</th><th>日期</th><th class="right">新增需求 / 件</th><th class="right">可用供给 / 件</th><th class="right">日末余额 / 件</th><th>缓冲期</th></tr></thead><tbody><template v-for="line in lines" :key="line.name"><tr v-for="row in line.series" :key="line.name + row.day"><td>{{ line.name }}</td><td>{{ row.day }}</td><td class="right">{{ row.demand }}</td><td class="right">{{ row.arrivals }}</td><td class="right" :class="{ 'danger-text': Number(row.closingBalance) < 0 }">{{ row.closingBalance }}</td><td>{{ row.inBuffer ? '是' : '否' }}</td></tr></template></tbody></table></div>
</template>
