<script setup lang="ts">
import { computed } from 'vue'
import type { AI, ExplanationItem, TaskState } from '../api/types'

const props = defineProps<{ ai: AI | null; taskState?: TaskState | null; loading?: boolean; error?: string }>()
const emit = defineEmits<{ generate: [] }>()

const SECTIONS: { key: string; label: string }[] = [
  { key: 'keyEvidence', label: '关键事实' },
  { key: 'majorRisks', label: '风险提醒' },
  { key: 'humanConfirmations', label: '建议人工核实' }
]

const items = (key: string): ExplanationItem[] => {
  const value = props.ai?.explanation?.[key]
  return Array.isArray(value) ? value : []
}

const singleRunning = computed(() => !!props.taskState && ['QUEUED', 'RUNNING'].includes(props.taskState))

const running = computed(() => !!props.loading || singleRunning.value)

const status = computed(() => {
  if (running.value) return { key: 'running', label: '生成中', tone: 'info' }
  if (!props.ai) return { key: 'none', label: '未生成', tone: 'muted' }
  if (props.ai.status === 'AVAILABLE') return { key: 'ok', label: '已生成', tone: 'success' }
  if (props.ai.status === 'NOT_ATTEMPTED') return { key: 'none', label: '未调用', tone: 'muted' }
  return { key: 'failed', label: '未生成', tone: 'danger' }
})

const conclusion = computed(() => items('recommendationReasons')[0]?.text || '')
const reasons = computed(() => items('recommendationReasons').slice(1))
const columns = computed(() => SECTIONS.map(section => ({ ...section, list: items(section.key) })).filter(section => section.list.length))
const tokens = computed(() => props.ai?.usage?.totalTokens ?? null)
const reason = computed(() => props.ai?.reason || props.error || '')
</script>

<template>
  <section class="ai-panel" aria-label="智能分析">
    <header class="ai-head">
      <span class="ai-badge">AI</span>
      <h2>智能分析</h2>
      <span class="chip" :class="status.tone">{{ status.label }}</span>
      <span v-if="status.key === 'ok'" class="ai-scope">基于本次已读取的库存、销量与采购条件</span>
      <button v-if="status.key === 'none' || status.key === 'failed'" class="button small ai-cta"
              :disabled="running" @click="emit('generate')">
        {{ status.key === 'failed' ? '重新生成' : '生成 AI 解读' }}
      </button>
    </header>

    <div v-if="status.key === 'running'" class="ai-body">
      <p class="ai-note">正在重新读取该店仓的最新事实并请求模型解释；规则结论不受影响。</p>
      <div class="skeleton w80" /><div class="skeleton w95" /><div class="skeleton w60" />
    </div>

    <div v-else-if="status.key === 'ok'" class="ai-body">
      <p class="ai-lead">{{ conclusion }}</p>
      <div class="ai-grid" :style="{ gridTemplateColumns: `repeat(${Math.max(1, columns.length)}, minmax(0, 1fr))` }">
        <div v-for="column in columns" :key="column.key" class="ai-col">
          <h4>{{ column.label }}</h4>
          <ul><li v-for="(item, index) in column.list" :key="index">{{ item.text }}</li></ul>
        </div>
      </div>
      <details v-if="reasons.length" class="ai-more">
        <summary>完整建议依据（{{ reasons.length }} 条）</summary>
        <ul><li v-for="(item, index) in reasons" :key="index">{{ item.text }}</li></ul>
      </details>
      <footer class="ai-meta">
        <span>来源：本次单品分析</span>
        <span v-if="tokens !== null">Token {{ tokens }}</span>
        <span class="ai-boundary">AI 仅解释，不计算补货数量</span>
      </footer>
    </div>

    <div v-else-if="status.key === 'failed'" class="ai-body">
      <p class="ai-note strong">本次未生成解释</p>
      <p class="ai-reason">{{ reason || '模型未返回内容，可重新尝试。' }}</p>
      <p class="ai-hint">规则建议数量与采购条件仍然有效；AI 不可用不影响人工判断。</p>
    </div>

    <div v-else class="ai-body">
      <p class="ai-note">尚未生成解读。生成时会重新读取该店仓的最新库存、销量与采购条件，并按需调用模型；不会修改规则建议数量，也不创建任何单据。</p>
    </div>
  </section>
</template>

<style scoped>
.ai-panel { background: #fff; border: 1px solid var(--line); border-left: 3px solid var(--nav); border-radius: 8px; overflow: hidden }
.ai-head { display: flex; align-items: center; gap: 10px; padding: 11px 18px; border-bottom: 1px solid var(--line); flex-wrap: wrap }
.ai-head h2 { font-size: 14px }
.ai-badge { display: grid; place-items: center; height: 19px; padding: 0 6px; border-radius: 4px; background: var(--nav); color: #fff; font-size: 9.5px; font-weight: 700; letter-spacing: .6px }
.ai-scope { font-size: 10.5px; color: var(--subtle) }
.ai-cta { margin-left: auto }
.ai-body { padding: 16px 18px }
.ai-lead { font-size: 14px; line-height: 1.75; color: #22303e; margin-bottom: 14px }
.ai-grid { display: grid; gap: 20px }
.ai-col h4 { margin: 0 0 5px; font-size: 10.5px; font-weight: 600; color: var(--subtle); letter-spacing: .4px }
.ai-col ul, .ai-more ul { margin: 0; padding-left: 15px; font-size: 12px; line-height: 1.75; color: #3b4a58 }
.ai-col li { margin-bottom: 4px }
.ai-more { margin-top: 12px; border-top: 1px dashed #eef1f4; padding-top: 8px; font-size: 11.5px; color: var(--muted) }
.ai-more summary { cursor: pointer; color: var(--primary) }
.ai-meta { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 14px; padding-top: 9px; border-top: 1px solid #f2f4f6; font-size: 10.5px; color: var(--subtle) }
.ai-boundary { margin-left: auto; color: var(--muted) }
.ai-note { font-size: 12px; line-height: 1.75; color: var(--muted) }
.ai-note.strong { color: var(--ink); font-weight: 600; margin-bottom: 4px }
.ai-reason { font-size: 12px; color: var(--danger); margin-bottom: 6px }
.ai-hint { font-size: 11px; color: var(--subtle) }
.chip { font-size: 10px; padding: 1px 7px; border-radius: 4px; background: #eef1f4; color: #556575; white-space: nowrap }
.chip.success { background: var(--success-bg); color: var(--success) }
.chip.info { background: var(--info-bg); color: var(--info) }
.chip.danger { background: var(--danger-bg); color: var(--danger) }
.skeleton { height: 9px; border-radius: 4px; background: #eef2f4; margin: 8px 0; animation: pulse 1.4s infinite }
.w80 { width: 80% } .w95 { width: 95% } .w60 { width: 60% }
@keyframes pulse { 50% { opacity: .45 } }
</style>
