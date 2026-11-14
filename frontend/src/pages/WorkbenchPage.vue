<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { route, navigate } from '../router'
import { init, openBatch, startBatch, cancelBatch, state, summary, stageOf, latestBatchId, STAGE_LABEL } from '../s01'
import { displayDate, resultDate, quantityOf, nextAction } from '../business'
const current = computed(() => summary.value)
const running = computed(() => !!state.progress && !['SUCCEEDED','FAILED','CANCELLED'].includes(state.progress.task.state))
const queue = computed(() => state.priority.filter(i => !['none','pending','history'].includes(stageOf(i))).slice(0,8))
const counts = computed(() => current.value ? [{key:'REPLENISH',label:'需要补货',value:current.value.replenishSkuCount ?? current.value.ruleCalculated,tone:'primary'},{key:'NO_REPLENISHMENT',label:'暂不补货',value:current.value.noReplenishmentSkuCount ?? current.value.noReplenishment,tone:'neutral'},{key:'NEEDS_REVIEW',label:'需要核实',value:Math.max(0,current.value.discoveredSkuCount-(current.value.replenishSkuCount ?? current.value.ruleCalculated)-(current.value.noReplenishmentSkuCount ?? current.value.noReplenishment)),tone:'warning'}] : [])
async function open(id:string){await openBatch(id);if(route.value.path==='/workbench')navigate('/workbench',{batch:id})}
async function rerun(){const id=await startBatch();if(id && route.value.path==='/workbench')navigate('/workbench',{batch:id})}
onMounted(async()=>{await init();const id=route.value.query.batch || latestBatchId();if(id)await open(id)})
watch(()=>route.value.query.batch,async id=>{if(id && id!==state.batchId)await openBatch(id)})
</script>
<template>
  <div class="page buyer-workbench">
    <header class="page-head"><div><span class="eyebrow">采购工作区</span><h1>今天，先处理这些商品</h1></div><div class="head-actions"><span class="check-time" v-if="state.batches.length">上次检查 {{ resultDate(state.batches[0]?.createdAt) }}</span><button class="button primary" :disabled="state.busy || running" @click="rerun">{{ state.busy || running ? '正在检查商品…' : '检查自有商品' }}</button></div></header>
    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>
    <div v-if="running" class="run-strip" role="status"><span class="spinner" /><div><b>正在读取销量、库存与采购事实</b><small>{{ current?.processedCount || 0 }} / {{ current?.scopeObjectCount || '待确认' }} 个店仓已处理</small></div><button class="button small" :disabled="state.busy" @click="cancelBatch">停止本次检查</button></div>
    <section v-if="!state.batchId" class="panel empty-state"><h2>从一次商品检查开始</h2><button class="button primary" :disabled="state.busy" @click="rerun">开始检查商品</button></section>
    <section v-else-if="!current" class="panel empty-state"><p>{{ state.progressLoading ? '正在读取上次检查…' : '结果暂时无法读取，可重新检查。' }}</p></section>
    <template v-else>
      <div class="attention-summary"><div class="summary-title"><span class="eyebrow">本次检查</span><b>{{ current.discoveredSkuCount }} 款商品</b><small>{{ current.scopeObjectCount }} 个店仓</small></div><button v-for="row in counts" :key="row.key" :class="row.tone" @click="navigate('/suggestions',{batch:state.batchId,decision:row.key})"><strong>{{ row.value }}</strong><span>{{ row.label }}</span><i>↗</i></button></div>
      <p v-if="['FAILED','CANCELLED'].includes(state.progress?.task.state || '')" class="banner warning">本次检查未完成。已取得的结果仍可查看，未处理商品不代表无风险。<button class="button small" @click="rerun">重新检查</button></p>
      <section class="panel attention-queue"><div class="panel-head"><div><span class="eyebrow">优先处理</span><h2>从风险最高的店仓开始</h2></div><a :href="'#/suggestions?batch='+state.batchId">查看全部商品 →</a></div><a v-for="(item,index) in queue" :key="item.entityKey" class="attention-row" :href="'#/sku/'+item.entityKey+'?batch='+state.batchId"><span class="queue-number">{{ String(index+1).padStart(2,'0') }}</span><div class="attention-product"><b>{{ item.name || item.sku }}</b><small>{{ item.sku }} · {{ item.warehouseName }}</small></div><div class="attention-verdict"><span class="chip" :class="stageOf(item)">{{ STAGE_LABEL[stageOf(item)] }}</span><small>{{ item.riskDate ? displayDate(item.riskDate)+' 起有缺货风险' : '需要核实业务依据' }}</small></div><div class="attention-quantity"><b>{{ quantityOf(item) ?? '—' }} <small>件</small></b><span>参考补充库存</span></div><div class="attention-next"><span>{{ nextAction(item) }}</span><b>分析商品 →</b></div></a><p v-if="!queue.length" class="empty-inline">{{ state.priorityLoading ? '正在读取关注商品…' : '当前没有需要优先处理的商品。' }}</p></section>
      <div class="workbench-bottom"><details class="check-history"><summary>查看以往检查</summary><button v-for="task in state.batches" :key="task.taskRef.taskId" @click="open(task.taskRef.taskId)">{{ resultDate(task.createdAt) }} · {{ task.state==='SUCCEEDED' ? '检查完成' : task.state==='FAILED' ? '检查失败' : task.state==='CANCELLED' ? '已停止' : '处理中' }}</button></details></div>
    </template>
  </div>
</template>
