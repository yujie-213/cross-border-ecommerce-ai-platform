<script setup lang="ts">
import type { AI } from '../api/types'
defineProps<{ai:AI}>()
</script>
<template><details v-if="ai.usage || ai.actualModelRevision"><summary>模型与用量</summary><small>模型 {{ai.actualModelRevision || '未记录'}} · 输入 Token {{ai.usage?.inputTokens ?? '未返回'}} · 输出 Token {{ai.usage?.outputTokens ?? '未返回'}} · 总 Token {{ai.usage?.totalTokens ?? '未返回'}}</small><p class="micro-note">{{ai.usage?.actualCost==null?'费用未返回，不能视为免费':'费用已由服务端记录'}}。用量沿平台任务账本保存。</p></details></template>
