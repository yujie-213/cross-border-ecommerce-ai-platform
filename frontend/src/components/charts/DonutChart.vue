<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ segments: { label: string; count: number; color: string }[]; total: number; size?: number }>()
const size = computed(() => props.size || 132)
const geometry = computed(() => {
  const s = size.value, cx = s / 2, cy = s / 2, stroke = Math.round(s * 0.13), radius = (s - stroke) / 2 - 2
  const circumference = 2 * Math.PI * radius
  let offset = 0
  const arcs = props.segments.map(seg => {
    const length = props.total ? seg.count / props.total * circumference : 0
    const arc = { ...seg, dash: `${length.toFixed(2)} ${(circumference - length).toFixed(2)}`, offset: (-offset).toFixed(2) }
    offset += length
    return arc
  })
  return { cx, cy, stroke, radius, arcs }
})
</script>

<template>
  <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="donut" role="img"
       :aria-label="segments.map(s => `${s.label} ${s.count}`).join('，') + `，共 ${total}`">
    <circle :cx="geometry.cx" :cy="geometry.cy" :r="geometry.radius" fill="none" stroke="#eef1f4" :stroke-width="geometry.stroke" />
    <circle v-for="arc in geometry.arcs" :key="arc.label" :cx="geometry.cx" :cy="geometry.cy" :r="geometry.radius"
            fill="none" :stroke="arc.color" :stroke-width="geometry.stroke" :stroke-dasharray="arc.dash"
            :stroke-dashoffset="arc.offset" :transform="`rotate(-90 ${geometry.cx} ${geometry.cy})`" class="arc">
      <title>{{ arc.label }} {{ arc.count }} 项</title>
    </circle>
    <text :x="geometry.cx" :y="geometry.cy" text-anchor="middle" dominant-baseline="central" class="donut-total">{{ total }}</text>
  </svg>
</template>

<style scoped>
.donut { display: block }
.donut-total { font: 600 26px/1 "Segoe UI", "Microsoft YaHei", sans-serif; fill: var(--ink) }
.arc { transition: opacity .15s }
.donut:hover .arc { opacity: .55 }
.donut .arc:hover { opacity: 1 }
</style>
