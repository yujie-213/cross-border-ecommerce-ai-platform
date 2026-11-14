<script setup lang="ts">
import { computed } from 'vue'
import type { AI, ExplanationItem, TaskState } from '../api/types'
import { issueLabel } from '../api/v2'
const props = defineProps<{ ai: AI | null; taskState?: TaskState | null; loading?: boolean; error?: string; errorCode?: string | null; context?: string; enabled?: boolean; analysisOnly?: boolean }>()
const emit = defineEmits<{ generate: []; refresh: []; purchase: [] }>()
const items = (key: string): ExplanationItem[] => Array.isArray(props.ai?.explanation?.[key]) ? props.ai!.explanation![key] : []
const running = computed(() => !!props.loading || ['QUEUED','RUNNING'].includes(props.taskState || ''))
const ready = computed(() => !running.value && props.ai?.status === 'AVAILABLE')
const failed = computed(() => !running.value && (!!props.error || props.taskState === 'FAILED' || props.ai?.status === 'UNAVAILABLE' || (props.ai?.status === 'NOT_ATTEMPTED' && !props.analysisOnly)))
const partial = computed(() => props.taskState === 'SUCCEEDED' && props.ai?.status !== 'AVAILABLE')
const failure = computed(() => props.errorCode ? issueLabel(props.errorCode) : props.ai?.reason ? issueLabel(props.ai.reason) : props.error || 'AI 暂不可用，请稍后重试。')
const unique = (entries: ExplanationItem[]) => entries.filter((entry,index) => entries.findIndex(other => other.text === entry.text) === index)
const conclusion = computed(() => items('recommendationReasons').find(item => item.supportRefs.includes('conclusion')) || items('recommendationReasons')[0])
const evidence = computed(() => unique(items('keyEvidence')).slice(0,3))
const steps = computed(() => unique(items('humanConfirmations')).slice(0,2))
const risks = computed(() => unique(items('majorRisks')).slice(0,2))
const older = computed(() => props.ai?.adviceVersion !== 's01-purchase-advice-v2')
</script>
<template>
  <section class="agent-advice" aria-label="AI 行动建议" :data-state="running ? 'running' : ready ? 'ready' : failed ? 'failed' : 'idle'" aria-live="polite">
    <header class="advice-header"><div class="advice-mark">AI</div><div><h2>AI 行动建议</h2><p>{{ context || '当前商品与店仓' }}</p></div><button class="button primary" :disabled="running" @click="emit('generate')">{{ running ? '正在处理…' : ready ? '更新 AI 建议' : failed ? '重试 AI 建议' : '生成 AI 建议' }}</button></header>
    <div v-if="running" class="advice-running" role="status"><span class="spinner" /><b>{{ analysisOnly ? '正在更新销量、库存与补货判断…' : taskState === 'QUEUED' ? '已受理，等待开始分析…' : '正在更新补货分析并生成 AI 建议…' }}</b></div>
    <template v-else-if="ready">
      <div class="buyer-brief">
        <h3>{{ conclusion?.text }}</h3>
        <ul v-if="evidence.length" class="buyer-evidence" aria-label="判断依据"><li v-for="entry in evidence" :key="entry.text">{{ entry.text }}</li></ul>
        <div v-if="risks.length" class="buyer-caveats"><p v-for="entry in risks" :key="entry.text">{{ entry.text }}</p></div>
        <div v-if="steps.length" class="buyer-next"><h4>下一步</h4><ol><li v-for="entry in steps" :key="entry.text">{{ entry.text }}</li></ol><button class="button small" @click="emit('purchase')">核对采购条件 →</button></div>
      </div>
      <details class="advice-details"><summary>{{ older ? '历史解读与生成信息' : '查看生成信息' }}</summary><p v-if="older">这是先前版本保存的解读，更新分析可生成新版建议。</p><template v-if="older"><div v-for="section in [{key:'recommendationReasons',label:'原建议'},{key:'keyEvidence',label:'原依据'},{key:'majorRisks',label:'原风险'},{key:'humanConfirmations',label:'原确认项'}]" :key="section.key"><h4>{{ section.label }}</h4><ul><li v-for="(entry,index) in items(section.key)" :key="index">{{ entry.text }}</li></ul></div></template><small>模型 {{ ai?.actualModelRevision || ai?.provider || '未记录' }} · Token {{ ai?.usage?.totalTokens ?? '未返回' }} · 费用 {{ ai?.costStatus || '未确认' }}</small></details>
    </template>
    <div v-else-if="failed" class="advice-empty"><b>{{ partial ? '补货分析已更新，AI 建议未生成' : '这次没有生成 AI 建议' }}</b><p>{{ failure }}</p><button v-if="taskState && !['FAILED','CANCELLED','SUCCEEDED'].includes(taskState)" class="button" @click="emit('refresh')">重新读取状态</button></div>
    <div v-else-if="enabled === false" class="advice-empty"><p>AI 服务未启用</p></div>
  </section>
</template>
