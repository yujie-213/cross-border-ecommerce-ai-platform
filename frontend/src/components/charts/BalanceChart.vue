<script setup lang="ts">
import { computed } from 'vue'
import type { SeriesRow } from '../../api/types'

const props = defineProps<{ series: SeriesRow[]; planSeries?: SeriesRow[]; planLabel?: string }>()

const W = 480, H = 200, L = 40, R = 14, T = 20, B = 26

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
  const planValues = props.planSeries || []
  const closes = [...values.map(p => p.close), ...planValues.map(p => Number(p.closingBalance))]
  const max = Math.max(0, ...closes)
  const min = Math.min(0, ...closes)
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
  const arrivalRows = planValues.length ? planValues.map((p,index) => ({index,day:p.day,arrivals:Number(p.arrivals)})) : values
  const arrivals = arrivalRows.filter(p => p.arrivals > 0).map(p => ({ x: x(p.index), value: p.arrivals, day: p.day }))
  const planLine = planValues.map((p,i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(Number(p.closingBalance)).toFixed(1)}`).join(' ')
  const lowest = values.reduce((a, b) => (b.close < a.close ? b : a), values[0])
  const shortage = values.find(p => p.close < 0)
  return { values, planValues, planLine, x, y, line, runs, ticks, labels, arrivals, lowest, shortage, zero: y(0) }
})
</script>

<template>
  <div v-if="model" class="chart-wrap">
    <svg :viewBox="`0 0 ${W} ${H}`" class="chart" role="img"
         :aria-label="`补货前后供需余额预测，原计划最低余额 ${model.lowest.close}，日期 ${model.lowest.day}${model.planValues.length ? '，包含补货计划对比' : ''}`">
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
      <path :d="model.line" class="line" :class="{'baseline-with-plan':model.planValues.length}" data-curve="baseline" />
      <path v-if="model.planValues.length" :d="model.planLine" class="plan-line" data-curve="plan" />
      <circle v-for="(p,i) in model.planValues" :key="'plan-'+p.day" :cx="model.x(i)" :cy="model.y(Number(p.closingBalance))" r="2.5" class="plan-dot"><title>{{ planLabel || '按计划补货' }} · {{ p.day }}：到货 {{ p.arrivals }}，余额 {{ p.closingBalance }} 件</title></circle>
      <g v-if="model.shortage" class="shortage-marker"><line :x1="model.x(model.shortage.index)" :x2="model.x(model.shortage.index)" :y1="T" :y2="H-B" /><text :x="Math.min(W-120,model.x(model.shortage.index)+6)" :y="T+9">{{ model.shortage.day.slice(5) }} 起短缺</text></g>
      <circle v-for="p in model.values" :key="p.day" :cx="model.x(p.index)" :cy="model.y(p.close)"
              :r="p === model.lowest ? 4 : 2.4" :class="['dot', { low: p.close <= 0 }]">
        <title>{{ p.day }}：需求 {{ p.demand }}，到货 {{ p.arrivals }}，结存 {{ p.close }}</title>
      </circle>
      <g class="xlab">
        <text v-for="label in model.labels" :key="label.label + label.x" :x="label.x" :y="H - 6" :text-anchor="label.anchor">{{ label.label }}</text>
      </g>
    </svg>
    <div class="chart-legend">
      <span><i class="line-key" :class="{'baseline-key':model.planValues.length}" />不新增补货</span>
      <span v-if="model.planValues.length"><i class="plan-key" />{{ planLabel || '按计划补货' }}</span>
      <span><i class="area-key" />缺口</span>
      <span v-if="model.arrivals.length"><i class="dash-key" />到货日</span>
      <span class="legend-note">原计划最低 {{ Number(model.lowest.close.toFixed(1)) }} 件 · {{ model.lowest.day.slice(5) }}</span>
    </div>
  </div>
</template>

<style scoped>
.chart { width: 100%; height: auto; display: block }
.grid line { stroke: #eef1f4; stroke-width: 1 }
.grid text { font-size: 9.5px; fill: var(--subtle) }
.zero { stroke: #c3ccd4; stroke-width: 1 }
.line { fill: none; stroke: var(--primary); stroke-width: 2; stroke-linejoin: round }
.shortage-marker line{stroke:#af4940;stroke-dasharray:3 4;opacity:.65}.shortage-marker text{fill:#a4443a;font-size:10px}
.negative { fill: #fcefee; opacity: .9 }
.arrivals line { stroke: #c9812f; stroke-dasharray: 4 3; stroke-width: 1 }
.dot { fill: #fff; stroke: var(--primary); stroke-width: 1.8 }
.dot.low { fill: #fff; stroke: var(--danger); stroke-width: 2.4 }
.xlab text { font-size: 9.5px; fill: var(--subtle) }
.baseline-with-plan{stroke:#84918f;stroke-dasharray:5 4}.plan-line{fill:none;stroke:#197d72;stroke-width:2.5;stroke-linejoin:round}.plan-dot{fill:#fff;stroke:#197d72;stroke-width:1.8}.plan-key{width:14px;height:3px;background:#197d72}.baseline-key{background:repeating-linear-gradient(to right,#84918f 0 4px,transparent 4px 6px)!important}
.chart-legend { flex-wrap:wrap;display: flex; gap: 14px; align-items: center; font-size: 10.5px; color: var(--muted); padding: 6px 6px 0 }
.chart-legend i { display: inline-block; margin-right: 5px; vertical-align: middle }
.line-key { width: 12px; height: 2px; background: var(--primary) }
.area-key { width: 10px; height: 8px; background: #fcefee; border: 1px solid #f3d3d0 }
.dash-key { width: 2px; height: 10px; background: #c9812f }
.legend-note { margin-left: auto; color: var(--subtle) }
</style>
