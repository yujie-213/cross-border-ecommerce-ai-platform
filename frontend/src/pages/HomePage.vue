<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { request } from '../api/client'
import { init, state, latestBatchId } from '../s01'
import { href } from '../router'

const labels: Record<string,string> = { SUCCEEDED:'已完成', RUNNING:'进行中', CREATED:'等待开始', QUEUED:'排队中', FAILED:'需处理', CANCELLED:'已停止' }
const bTasks=ref<any[]>([])
const recent = computed(() => [
  ...bTasks.value.map(t=>({task:t,name:t.scenarioId.includes('CASE')?'售后问题处理':t.scenarioId.includes('EXPERIENCE')?'客户体验分析':'售后资料核验',url:href('/after-sales/workbench')})),
  ...state.batches.filter(t => t.analysisRange === 'OWNED_REGISTERED').map(t => ({ task:t, name:'自有商品补货检查', url:href('/workbench',{batch:t.taskRef.taskId}) })),
  ...state.singleHistory.map(t => ({ task:t, name:t.sku ? `${t.sku} · ${t.aiStatus === 'AVAILABLE' ? 'AI 行动建议' : '补货分析'}` : '单品分析', url:t.entityKey ? href('/sku/'+t.entityKey,{single:t.taskRef.taskId}) : href('/workbench') }))
].sort((a,b) => (b.task.createdAt || b.task.deadline).localeCompare(a.task.createdAt || a.task.deadline)).slice(0,5))
const attention = computed(() => recent.value.filter(r => r.task.state === 'FAILED'))
onMounted(init)
const bEnabled=ref(false)
onMounted(async()=>{try{const status=await request<{enabled:boolean}>('/status',{},undefined,15000,'/api/b/v1');bEnabled.value=status.enabled;if(status.enabled){const result=await request<{items:any[]}>('/tasks?workspaceId=after-sales-v1&limit=5',{},undefined,15000,'/api/b/v1');bTasks.value=result.items}}catch{/* S01 remains usable when B is unavailable. */}})
</script>

<template>
  <div class="page platform-home">
    <header class="page-head"><div><span class="eyebrow">跨境电商智慧 AI 中台</span><h1>工作台</h1><p class="page-sub">补货运营与售后服务概览</p></div></header>
    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>
    <section aria-labelledby="capabilities-title">
      <h2 id="capabilities-title" class="home-title">业务模块</h2>
      <div class="home-modules">
        <a class="panel agent-entry" :href="href('/workbench', {batch:latestBatchId() || undefined})">
          <span class="agent-mark">补</span><div class="agent-copy"><span class="chip primary">已接入</span><h2>智能补货</h2><small>商品分析 / AI 行动建议 / 请购管理</small></div><span class="agent-arrow" aria-hidden="true">→</span>
        </a>
        <a class="panel agent-entry" :href="href('/after-sales/workbench')"><span class="agent-mark">客</span><div class="agent-copy"><span class="chip" :class="bEnabled ? 'primary' : 'plain'">{{ bEnabled ? '已接入' : '暂不可用' }}</span><h2>售后与客户体验</h2><small>售后处理 / 退货与商品分析 / 调查与质量风险</small></div><span class="agent-arrow" aria-hidden="true">→</span></a>
      </div>
    </section>
    <div class="home-lower">
      <section class="panel"><div class="panel-head"><h2>近期任务</h2></div>
        <a v-for="row in recent" :key="row.task.taskRef.taskId" class="task-entry" :href="row.url"><div><b>{{ row.name }}</b><small>{{row.task.scenarioId.startsWith('B_')?'智能售后':'智能补货'}}</small></div><span class="chip" :class="row.task.state === 'FAILED' ? 'danger' : 'plain'">{{ labels[row.task.state] || '处理中' }}</span></a>
        <p v-if="!recent.length" class="empty-inline">暂无任务，进入智能补货开始检查。</p>
      </section>
      <section class="panel"><div class="panel-head"><h2>重要事项</h2></div>
        <div class="home-notes"><p v-if="state.pending"><b>有一笔请购结果待核对</b><br>请进入原分析核对，避免重复提交。<a :href="href('/sku/'+state.pending.entityKey,{single:state.pending.singleId})">查看 →</a></p>
          <p v-for="row in attention" :key="row.task.taskRef.taskId"><a :href="row.url">{{ row.name }}需要处理 →</a></p>
          <p v-if="!state.pending && !attention.length" class="muted">暂无需要处理的任务异常。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home-title{font-size:16px;margin:8px 0 16px}.home-modules{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.agent-entry{display:flex;align-items:center;gap:18px;padding:22px;color:inherit;text-decoration:none;min-width:0;min-height:156px}.agent-entry:hover{border-color:#0f6b64}.agent-copy{min-width:0}.agent-entry h2{font-size:20px;margin:8px 0;overflow-wrap:anywhere}.agent-entry small{color:var(--muted,#74818c);line-height:1.6}.agent-mark{display:grid;place-items:center;flex:none;width:58px;height:58px;background:#e7f2ef;color:#0f6b64;border-radius:8px;font-size:26px;font-weight:700}.agent-arrow{margin-left:auto;flex:none;color:#0f6b64;font-size:20px}.home-lower{display:grid;grid-template-columns:1.4fr 1fr;gap:24px;margin-top:28px}.task-entry{display:flex;align-items:center;gap:16px;justify-content:space-between;padding:16px 20px;border-top:1px solid #edf0f2;color:inherit;text-decoration:none}.task-entry:hover{background:#f7faf9}.task-entry small{display:block;margin-top:6px;color:#74818c}.home-notes{padding:8px 24px 28px;line-height:1.8}.home-notes p{margin-bottom:24px}@media(max-width:1000px){.home-lower{grid-template-columns:1fr}.agent-entry{padding:20px;gap:14px}}@media(max-width:720px){.home-modules{grid-template-columns:1fr}.agent-entry{min-height:128px}}
</style>
