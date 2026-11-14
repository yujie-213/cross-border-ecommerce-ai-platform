<script setup lang="ts">
import { computed } from 'vue'
import type { SeriesRow } from '../../api/types'

const props = defineProps<{ series: SeriesRow[] }>()

const W = 720, H = 200, L = 40, R = 14, T = 16, B = 26

const points = computed(() => props.series.map((row, index) => ({
  index,
  day: row.day,
  close: Number(row.closingBalance),
  demand: Number(row.demand),
  arrivals: Number(row.arrivals)
})))

const model = computed(() => {
  const values = points.value
  if (values.length < 2) return null
  const max = Math.max(0, ...values.map(p => p.close))
  const min = Math.min(0, ...values.map(p => p.close))
  const span = Math.max(1, max - min)
  const x = (i: number) => L + (W - L - R) * (i / Math.max(1, values.length - 1))
  const y = (v: number) => T + (H - T - B) * (1 - (v - min) / span)
  const line = values.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.close).toFixed(1)}`).join(' ')
  // Shade every negative run separately so the zero crossing stays exact.
  const runs: string[] = []
  let run: typeof values = []
  const flush = () => {
    if (run.length > 1) runs.push(run.map((p, i) => `${i ? 'L' : 'M'}${x(p.index).toFixed(1)},${y(p.close).toFixed(1)}`).join(' ')
      + ` L${x(run[run.length - 1].index).toFixed(1)},${y(0).toFixed(1)} L${x(run[0].index).toFixed(1)},${y(0).toFixed(1)} Z`)
    run = []
  }
  values.forEach(p => { if (p.close < 0) run.push(p); else flush() })
  flush()
  const ticks = [max, (max + min) / 2, min].map(v => ({ value: Math.round(v), y: y(v) }))
  const labels = values.map((p, i) => ({ x: x(i), label: p.day.slice(5), anchor: i === values.length - 1 ? 'end' : i === 0 ? 'start' : 'middle' }))
    .filter((_, i) => i % 2 === 0 || i === values.length - 1)
  const arrivals = values.filter(p => p.arrivals > 0).map(p => ({ x: x(p.index), value: p.arrivals, day: p.day }))
  const lowest = values.reduce((a, b) => (b.close < a.close ? b : a), values[0])
  return { values, x, y, line, runs, ticks, labels, arrivals, lowest, zero: y(0) }
})
</script>

<template>
  <div v-if="model" class="chart-wrap">
    <svg :viewBox="`0 0 ${W} ${H}`" class="chart" role="img"
         :aria-label="`结存预测，最低结存 ${model.lowest.close}，日期 ${model.lowest.day}`">
      <g class="grid">
        <line v-for="tick in model.ticks" :key="tick.value + '-' + tick.y" :x1="L" :x2="W - R" :y1="tick.y" :y2="tick.y" />
        <text v-for="tick in model.ticks" :key="'t' + tick.value" :x="L - 6" :y="tick.y + 3" text-anchor="end">{{ tick.value }}</text>
      </g>
      <path v-for="(run, i) in model.runs" :key="'run' + i" :d="run" class="negative" />
      <line :x1="L" :x2="W - R" :y1="model.zero" :y2="model.zero" class="zero" />
      <g class="arrivals">
        <line v-for="mark in model.arrivals" :key="mark.day" :x1="mark.x" :x2="mark.x" :y1="T" :y2="H - B">
          <title>{{ mark.day }} 到货 {{ mark.value }}</title>
        </line>
      </g>
      <path :d="model.line" class="line" />
      <circle v-for="p in model.values" :key="p.day" :cx="model.x(p.index)" :cy="model.y(p.close)"
              :r="p === model.lowest ? 4 : 2.4" :class="['dot', { low: p.close <= 0 }]">
        <title>{{ p.day }}：需求 {{ p.demand }}，到货 {{ p.arrivals }}，结存 {{ p.close }}</title>
      </circle>
      <g class="xlab">
        <text v-for="label in model.labels" :key="label.label + label.x" :x="label.x" :y="H - 6" :text-anchor="label.anchor">{{ label.label }}</text>
      </g>
    </svg>
    <div class="chart-legend">
      <span><i class="line-key" />结存</span>
      <span><i class="area-key" />负结存</span>
      <span><i class="dash-key" />到货日</span>
      <span class="legend-note">最低 {{ model.lowest.close }} · {{ model.lowest.day.slice(5) }}</span>
    </div>
  </div>
</template>

<style scoped>
.chart { width: 100%; height: auto; display: block }
.grid line { stroke: #eef1f4; stroke-width: 1 }
.grid text { font-size: 9.5px; fill: var(--subtle) }
.zero { stroke: #c3ccd4; stroke-width: 1 }
.line { fill: none; stroke: var(--primary); stroke-width: 2; stroke-linejoin: round }
.negative { fill: #fcefee; opacity: .9 }
.arrivals line { stroke: #c9812f; stroke-dasharray: 4 3; stroke-width: 1 }
.dot { fill: #fff; stroke: var(--primary); stroke-width: 1.8 }
.dot.low { fill: #fff; stroke: var(--danger); stroke-width: 2.4 }
.xlab text { font-size: 9.5px; fill: var(--subtle) }
.chart-legend { display: flex; gap: 14px; align-items: center; font-size: 10.5px; color: var(--muted); padding: 6px 6px 0 }
.chart-legend i { display: inline-block; margin-right: 5px; vertical-align: middle }
.line-key { width: 12px; height: 2px; background: var(--primary) }
.area-key { width: 10px; height: 8px; background: #fcefee; border: 1px solid #f3d3d0 }
.dash-key { width: 2px; height: 10px; background: #c9812f }
.legend-note { margin-left: auto; color: var(--subtle) }
</style>
