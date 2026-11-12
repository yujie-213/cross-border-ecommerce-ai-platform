<script setup lang="ts">
import type { Task } from '../api/types'
import { canReport } from '../domain'
import StatusBadge from './StatusBadge.vue'
defineProps<{ items: Task[]; cursor: string | null; paged: boolean }>()
defineEmits<{ open: [id: string]; next: []; first: [] }>()
</script>
<template><div v-if="!items.length" class="empty compact"><h3>当前精确范围暂无历史任务</h3><p>请选择授权包，或新建一次只读分析。</p></div><div v-else class="table-scroll"><table><caption class="sr-only">当前精确店铺、仓库、SKU 范围历史，每页最多 20 条</caption><thead><tr><th>任务 / 版本</th><th>任务状态</th><th>报告发布</th><th>任务截止（UTC）</th><th>操作</th></tr></thead><tbody><tr v-for="item in items" :key="item.taskRef.taskId"><td><button class="evidence-link mono" @click="$emit('open', item.taskRef.taskId)">{{ item.taskRef.taskId.slice(0, 12) }}</button><small class="product-sub">revision {{ item.revision }} · plan {{ item.planVersion }}</small></td><td><StatusBadge :value="item.state" /><small v-if="item.errorCode" class="product-sub">{{ item.errorCode }}</small></td><td>{{ canReport(item) ? '已发布 · ' + item.reportRef?.reportId.slice(0, 10) : '无可读报告' }}</td><td>{{ item.deadline }}</td><td><button class="button small" @click="$emit('open', item.taskRef.taskId)">{{ canReport(item) ? '查看报告' : '查看任务' }}</button></td></tr></tbody></table></div><div class="table-foot"><span>本页 {{ items.length }} 条 · 精确范围，非全库统计</span><div class="button-row"><button v-if="paged" class="button small" @click="$emit('first')">返回首页</button><button :disabled="!cursor" class="button small" @click="$emit('next')">下一页</button></div></div></template>
