<script setup lang="ts">
import type { AI } from '../api/types'
import { shown } from '../domain'
import StatusBadge from './StatusBadge.vue'
import Notice from './Notice.vue'
defineProps<{ ai: AI }>()
const sections = [{ key: 'recommendationReasons', name: '建议原因' }, { key: 'keyEvidence', name: '关键依据' }, { key: 'majorRisks', name: '主要风险' }, { key: 'humanConfirmations', name: '人工确认事项' }]
</script>
<template>
  <div class="section-head"><h3>AI 解释</h3><StatusBadge :value="ai.status" /></div>
  <p class="micro-note">仅展示本次报告绑定并通过事实与引用校验的解释；AI 不改变数据质量、补货计算或采购权限。</p>
  <p v-if="ai.actualModelRevision" class="micro-note">本次模型：{{ ai.actualModelRevision }} · 用量引用：{{ shown(ai.usageRef) }}</p>
  <Notice v-if="ai.provider === 'MOCK'" tone="warning" title="工程 Mock 解释">此解释来自明确启用的工程模拟 Provider。</Notice>
  <template v-if="ai.status === 'AVAILABLE'"><section v-for="section in sections" :key="section.key" class="explanation-section"><h3>{{ section.name }}</h3><ul><li v-for="(item, i) in ai.explanation?.[section.key] || []" :key="i">{{ item.text }}<small class="muted">依据：{{ item.supportRefs.join('、') }}<template v-if="item.certainty"> · {{ item.certainty }}</template></small></li></ul></section></template>
  <Notice v-else :title="ai.status === 'NOT_ATTEMPTED' ? '本次未启用 AI 解释' : 'AI 解释不可用'" :tone="ai.status === 'UNAVAILABLE' ? 'warning' : 'info'">合法规则分析仍可查看；解释状态不改变质量、计算结论或采购权限。<p v-if="ai.reason">原因：{{ ai.reason }}</p></Notice>
  <dl class="token-grid"><div><dt>输入 Token</dt><dd>{{ shown(ai.usage?.inputTokens) }}</dd></div><div><dt>输出 Token</dt><dd>{{ shown(ai.usage?.outputTokens) }}</dd></div><div><dt>总 Token</dt><dd>{{ shown(ai.usage?.totalTokens) }}</dd></div><div v-if="ai.usage?.cachedInputTokens != null"><dt>缓存输入 Token</dt><dd>{{ ai.usage.cachedInputTokens }}</dd></div><div v-if="ai.usage?.uncachedInputTokens != null"><dt>未缓存输入 Token</dt><dd>{{ ai.usage.uncachedInputTokens }}</dd></div></dl>
  <p class="micro-note">Token 状态：{{ shown(ai.tokenUsageStatus) }} · 费用：{{ ai.usage?.actualCost == null ? '未知（不代表免费）' : '已由服务端记录' }}。费用未知不阻断合法解释。</p>
</template>
