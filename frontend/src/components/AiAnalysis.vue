<script setup lang="ts">
import { computed } from 'vue'
import type { AI, ExplanationItem, TaskState } from '../api/types'
import { issueLabel } from '../api/v2'
const props = defineProps<{ ai: AI | null; taskState?: TaskState | null; loading?: boolean; error?: string; errorCode?: string | null; context?: string; enabled?: boolean; analysisOnly?: boolean }>()
const emit = defineEmits<{ generate: []; refresh: [] }>()
const items = (key: string): ExplanationItem[] => Array.isArray(props.ai?.explanation?.[key]) ? props.ai!.explanation![key] : []
const running = computed(() => !!props.loading || ['QUEUED','RUNNING'].includes(props.taskState || ''))
const ready = computed(() => !running.value && props.ai?.status === 'AVAILABLE')
const failed = computed(() => !running.value && (!!props.error || props.taskState === 'FAILED' || props.ai?.status === 'UNAVAILABLE' || (props.ai?.status === 'NOT_ATTEMPTED' && !props.analysisOnly)))
const label = computed(() => running.value ? (props.analysisOnly ? '更新分析中' : '生成建议中') : ready.value ? '建议已就绪' : failed.value ? '本次未生成' : '等待你的分析请求')
const failure = computed(() => props.errorCode ? issueLabel(props.errorCode) : props.ai?.reason ? issueLabel(props.ai.reason) : props.error || '本次 AI 暂不可用，补货判断仍可查看。')
const actions = computed(() => items('recommendationReasons'))
const primaryIndex = computed(() => Math.max(0, actions.value.findIndex(item => /先|加急|调拨|补齐|核实/.test(item.text))))
const primary = computed(() => actions.value[primaryIndex.value])
const secondary = computed(() => actions.value.filter((_,index) => index !== primaryIndex.value)[0])
</script>
<template>
  <section class="agent-advice" aria-label="AI 行动建议" :data-state="running ? 'running' : ready ? 'ready' : failed ? 'failed' : 'idle'" aria-live="polite">
    <header class="advice-header"><div class="advice-mark">AI</div><div><h2>AI 行动建议</h2><p>{{ context || '针对当前商品与店仓' }}</p></div><span class="advice-status">{{ label }}</span><button class="button primary" :disabled="running" @click="emit('generate')">{{ running ? '正在处理…' : ready ? '重新生成 AI 建议' : failed ? '重试 AI 建议' : '生成 AI 建议' }}</button></header>
    <div v-if="running" class="advice-running" role="status"><span class="spinner" /><div><b>{{ analysisOnly ? '正在读取最新销量、库存与采购条件' : taskState === 'RUNNING' ? '正在分析当前店仓，完成后会在这里展示建议' : '请求已受理，正在准备分析' }}</b><p>{{ analysisOnly ? '本次只更新补货分析，不调用 AI。' : '先核实 ERP 事实，再生成有依据的行动建议。你可以离开，结果会保存。' }}</p></div></div>
    <template v-else-if="ready"><div class="advice-conclusion"><span>建议先做</span><h3>{{ primary?.text || '请核实下方建议与业务事实后行动' }}</h3></div><div class="advice-support"><div v-if="secondary"><h4>接下来</h4><p>{{ secondary.text }}</p></div><div v-if="items('majorRisks')[0]"><h4>重点留意</h4><p>{{ items('majorRisks')[0].text }}</p></div></div><details class="advice-details"><summary>查看建议依据与完整解读</summary><div v-for="section in [{key:'recommendationReasons',label:'行动建议'},{key:'keyEvidence',label:'判断依据'},{key:'majorRisks',label:'风险'},{key:'humanConfirmations',label:'人工核实'}]" :key="section.key"><h4>{{ section.label }}</h4><ul><li v-for="(entry,index) in items(section.key)" :key="index">{{ entry.text }}</li></ul></div><small>模型 {{ ai?.actualModelRevision || ai?.provider || '未记录' }} · Token {{ ai?.usage?.totalTokens ?? '未返回' }} · 费用 {{ ai?.costStatus || '未确认' }}</small></details><p class="advice-boundary">AI 辅助解释与行动判断；数量由补货规则计算，采购须人工确认。</p></template>
    <div v-else-if="failed" class="advice-empty"><b>这次没有生成 AI 建议</b><p>{{ failure }}</p><p>下方已完成的销量、库存和补货结果不会丢失。可点击上方按钮重试。</p><button v-if="taskState && !['FAILED','CANCELLED','SUCCEEDED'].includes(taskState)" class="button" @click="emit('refresh')">重新读取状态</button></div>
    <div v-else class="advice-empty"><h3>让 AI 帮你判断下一步</h3><p>综合销量变化、各仓库存、ERP 建议差异和采购限制，形成可执行的建议。</p><p class="muted small">{{ enabled === false ? '当前 AI 服务未启用；仍可正常更新补货分析。' : '仅点击“生成 AI 建议”时调用模型；缺少报价也可分析。' }}</p></div>
  </section>
</template>
