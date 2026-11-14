<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ days: { day: string; quantity: string }[]; average?: string | null; total?: string | null }>()

const W = 720, H = 140, L = 34, R = 10, T = 12, B = 24

const model = computed(() => {
  const rows = props.days.map(d => ({ day: d.day, quantity: Number(d.quantity) }))
  if (!rows.length) return null
  const max = Math.max(1, ...rows.map(r => r.quantity))
  const slot = (W - L - R) / rows.length
  const barWidth = Math.min(38, slot * 0.52)
  const y = (v: number) => T + (H - T - B) * (1 - v / max)
  const average = props.average === null || props.average === undefined ? null : Number(props.average)
  return {
    rows: rows.map((r, i) => ({
      ...r,
      x: L + slot * i + (slot - barWidth) / 2,
      width: barWidth,
      y: y(r.quantity),
      height: Math.max(1, H - B - y(r.quantity)),
      labelX: L + slot * i + slot / 2
    })),
    average: average && average > 0 ? { y: y(average), value: average } : null,
    baseline: H - B,
    max,
    slot
  }
})
</script>

<template>
  <div v-if="model" class="bars-wrap">
    <svg :viewBox="`0 0 ${W} ${H}`" class="bars" role="img"
         :aria-label="`最近 ${model.rows.length} 个完整业务日销量，合计 ${total || model.rows.reduce((a, r) => a + r.quantity, 0)}`">
      <line :x1="L" :x2="W - R" :y1="model.baseline" :y2="model.baseline" class="axis" />
      <text :x="L - 6" :y="model.baseline" text-anchor="end" class="ytick">0</text>
      <text :x="L - 6" :y="T + 4" text-anchor="end" class="ytick">{{ model.max }}</text>
      <rect v-for="bar in model.rows" :key="bar.day" :x="bar.x" :y="bar.y" :width="bar.width" :height="bar.height" rx="2" class="bar">
        <title>{{ bar.day }}：{{ bar.quantity }} 件</title>
      </rect>
      <line v-if="model.average" :x1="L" :x2="W - R" :y1="model.average.y" :y2="model.average.y" class="avg">
        <title>日均 {{ model.average.value }} 件</title>
      </line>
      <text v-for="bar in model.rows" :key="'l' + bar.day" :x="bar.labelX" :y="H - 6" text-anchor="middle" class="xlab">{{ bar.day.slice(5) }}</text>
    </svg>
  </div>
</template>

<style scoped>
.bars { width: 100%; height: auto; display: block }
.axis { stroke: #dde3e8 }
.ytick, .xlab { font-size: 9.5px; fill: var(--subtle) }
.bar { fill: #7fa8a3 }
.bar:hover { fill: var(--primary) }
.avg { stroke: #c9812f; stroke-dasharray: 4 3 }
</style>
