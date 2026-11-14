<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { init, state, latestBatchId } from '../s01'
import { href } from '../router'

const labels: Record<string,string> = { SUCCEEDED:'已完成', RUNNING:'进行中', CREATED:'等待开始', QUEUED:'排队中', FAILED:'需处理', CANCELLED:'已停止' }
const recent = computed(() => [
  ...state.batches.filter(t => t.analysisRange === 'OWNED_REGISTERED').map(t => ({ task:t, name:'自有商品补货检查', url:href('/workbench',{batch:t.taskRef.taskId}) })),
  ...state.singleHistory.map(t => ({ task:t, name:t.sku ? `${t.sku} · ${t.aiStatus === 'AVAILABLE' ? 'AI 行动建议' : '补货分析'}` : '单品分析', url:t.entityKey ? href('/sku/'+t.entityKey,{single:t.taskRef.taskId}) : href('/workbench') }))
].sort((a,b) => (b.task.createdAt || b.task.deadline).localeCompare(a.task.createdAt || a.task.deadline)).slice(0,5))
const attention = computed(() => recent.value.filter(r => r.task.state === 'FAILED'))
onMounted(init)
</script>

<template>
  <div class="page platform-home">
    <header class="page-head"><div><span class="eyebrow">跨境电商智慧 AI 中台</span><h1>工作首页</h1><p class="page-sub">让业务问题找到合适的 AI 工作伙伴。</p></div></header>
    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>
    <section aria-labelledby="capabilities-title">
      <h2 id="capabilities-title" class="home-title">业务能力</h2>
      <a class="panel agent-entry" :href="href('/workbench', {batch:latestBatchId() || undefined})">
        <span class="agent-mark">补</span><div><span class="chip primary">已接入</span><h2>智能补货</h2><p>找到缺货风险，理解分仓建议，核实后人工请购。</p><small>自有商品分析 / AI 行动建议 / 采购状态追踪</small></div><span class="agent-arrow">进入工作区 →</span>
      </a>
    </section>
    <div class="home-lower">
      <section class="panel"><div class="panel-head"><h2>近期任务</h2></div>
        <a v-for="row in recent" :key="row.task.taskRef.taskId" class="task-entry" :href="row.url"><div><b>{{ row.name }}</b><small>智能补货</small></div><span class="chip" :class="row.task.state === 'FAILED' ? 'danger' : 'plain'">{{ labels[row.task.state] || '处理中' }}</span></a>
        <p v-if="!recent.length" class="empty-inline">暂无任务，进入智能补货开始检查。</p>
      </section>
      <section class="panel"><div class="panel-head"><h2>重要事项</h2></div>
        <div class="home-notes"><p v-if="state.pending"><b>有一笔请购结果待核对</b><br>请进入原分析核对，避免重复提交。<a :href="href('/sku/'+state.pending.entityKey,{single:state.pending.singleId})">查看 →</a></p>
          <p v-for="row in attention" :key="row.task.taskRef.taskId"><a :href="row.url">{{ row.name }}需要处理 →</a></p>
          <p v-if="!state.pending && !attention.length" class="muted">暂无需要处理的任务异常。</p>
          <small class="muted">当前为教学环境。采购申请须人工确认，并由 ERP 完成审批。</small>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home-title{font-size:16px;margin:8px 0 16px}.agent-entry{display:flex;align-items:center;gap:24px;padding:30px;color:inherit;text-decoration:none;max-width:960px}.agent-entry:hover{border-color:#0f6b64}.agent-entry h2{font-size:26px;margin:8px 0}.agent-entry p{margin:8px 0;color:var(--ink-2,#526270)}.agent-entry small{color:var(--muted,#74818c)}.agent-mark{display:grid;place-items:center;width:78px;height:78px;background:#e7f2ef;color:#0f6b64;border-radius:20px;font-size:32px;font-weight:700}.agent-arrow{margin-left:auto;color:#0f6b64;white-space:nowrap}.home-lower{display:grid;grid-template-columns:1.4fr 1fr;gap:24px;margin-top:32px}.task-entry{display:flex;align-items:center;gap:16px;justify-content:space-between;padding:20px 24px;border-top:1px solid #edf0f2;color:inherit;text-decoration:none}.task-entry:hover{background:#f7faf9}.task-entry small{display:block;margin-top:6px;color:#74818c}.home-notes{padding:8px 24px 28px;line-height:1.8}.home-notes p{margin-bottom:24px}@media(max-width:1000px){.home-lower{grid-template-columns:1fr}.agent-entry{padding:24px;gap:16px}.agent-arrow{font-size:12px}}
</style>
