<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { route, navigate } from '../router'
import { init, openBatch, startBatch, cancelBatch, state, summary, stageOf, latestBatchId, STAGE_LABEL } from '../s01'
import DonutChart from '../components/charts/DonutChart.vue'
const current = computed(() => summary.value)
const running = computed(() => !!state.progress && !['SUCCEEDED','FAILED','CANCELLED'].includes(state.progress.task.state))
const segments = computed(() => {
  const s=current.value
  if (!s) return []
  return [
    {label:'需补货',count:s.replenishSkuCount ?? s.ruleCalculated,color:'#0f6b64',filter:'REPLENISH'},
    {label:'暂不补货',count:s.noReplenishmentSkuCount ?? s.noReplenishment,color:'#8bac9f',filter:'NO_REPLENISHMENT'},
    {label:'待核实',count:Math.max(0,s.discoveredSkuCount-(s.replenishSkuCount ?? s.ruleCalculated)-(s.noReplenishmentSkuCount ?? s.noReplenishment)),color:'#d6a460',filter:'NEEDS_REVIEW'}
  ].filter(r=>r.count>0)
})
const queue=computed(()=>state.priority.filter(i=>!['none','pending','history'].includes(stageOf(i))).slice(0,8))
const incomplete=computed(()=>Object.values(state.progress?.sourceLimits || {}).some(v=>!v.complete))
async function open(id:string){await openBatch(id);if(route.value.path==='/workbench')navigate('/workbench',{batch:id})}
async function rerun(){const id=await startBatch();if(id && route.value.path==='/workbench')navigate('/workbench',{batch:id})}
function filter(decision:string){navigate('/suggestions',{batch:state.batchId,decision})}
onMounted(async()=>{await init();const id=route.value.query.batch || latestBatchId();if(id)await open(id)})
watch(()=>route.value.query.batch,async id=>{if(id && id!==state.batchId)await openBatch(id)})
</script>
<template>
  <div class="page">
    <header class="page-head"><div><h1>智能补货</h1><p class="page-sub">自有商品，按店铺和仓库分别判断。</p></div><div class="head-actions">
      <label><span class="sr-only">检查批次</span><select :value="state.batchId" @change="open(($event.target as HTMLSelectElement).value)"><option v-for="task in state.batches" :key="task.taskRef.taskId" :value="task.taskRef.taskId">{{ new Date(task.deadline).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) }} · {{ task.state==='SUCCEEDED' ? '已完成' : task.state==='CANCELLED' ? '已停止' : task.state==='FAILED' ? '失败' : '处理中' }}</option><option v-if="!state.batches.length" value="">尚无检查</option></select></label>
      <button class="button primary" :disabled="state.busy || running" @click="rerun">{{ running ? '检查中…' : '检查自有商品' }}</button>
    </div></header>
    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>
    <div v-if="running" class="run-strip"><span class="pulse" />正在检查 {{ current?.processedCount || 0 }} / {{ current?.scopeObjectCount || '—' }}<span class="run-note">可以离开，结果会保存</span><button class="button small" :disabled="state.busy" @click="cancelBatch">停止</button></div>
    <section v-if="!state.batchId" class="panel empty-state"><h2>开始检查自有商品</h2><p>读取最新销量和库存，查看各仓的补货建议。</p><button class="button primary" :disabled="state.busy" @click="rerun">开始检查</button></section>
    <section v-else-if="!current" class="panel loading-state"><template v-if="state.progressLoading"><span class="spinner" />正在读取结果…</template><template v-else>本次结果无法读取。可重新检查，历史任务仍保留。<button class="button" :disabled="state.busy" @click="rerun">重新检查</button></template></section>
    <template v-else>
      <p v-if="state.progress?.analysisRange==='LEGACY_SHARED'" class="banner warning">这是历史共享目录结果。重新检查仅覆盖当前登记的自有商品。</p>
      <p v-if="['FAILED','CANCELLED'].includes(state.progress?.task.state || '')" class="banner warning">本次检查未完成，已保存的结果可查看。</p>
      <p v-if="incomplete" class="banner warning">部分资料未读取完整，相关建议需核实。</p>
      <section class="panel overview" aria-label="补货概览">
        <div class="overview-chart"><DonutChart :segments="segments" :total="current.discoveredSkuCount" :size="156" /><span>商品</span></div>
        <div class="overview-legend"><button v-for="row in segments" :key="row.label" @click="filter(row.filter)"><i class="dot" :style="{background:row.color}" /><span>{{ row.label }}</span><b>{{ row.count }}</b></button><small>{{ current.scopeObjectCount }} 个店铺仓库组合，分别计算</small></div>
        <div class="overview-actions"><a class="button" :href="'#/suggestions?batch='+state.batchId">查看全部商品 →</a><button v-if="current.riskSkuCount" class="risk-link" @click="filter('RISK')">{{ current.riskSkuCount }} 款有缺货风险 →</button><button v-if="current.erpDifferenceSkuCount" class="risk-link" @click="filter('DIFFERENCE')">{{ current.erpDifferenceSkuCount }} 款与 ERP 建议差异较大 →</button></div>
      </section>
      <section class="panel"><div class="panel-head"><h2>优先关注</h2><small>缺货风险与待补仓库</small></div>
        <div class="qhead"><span>商品 / 仓库</span><span>判断</span><span class="r">库存</span><span class="r">参考补充</span><span>预计缺货</span></div>
        <a v-for="item in queue" :key="item.entityKey" class="qrow" :href="'#/sku/'+item.entityKey+'?batch='+state.batchId"><div class="qname"><span>{{ item.name || item.sku }}</span><small>{{ item.sku }} · {{ item.storeName }} / {{ item.warehouseName }}</small></div><div><span class="chip" :class="stageOf(item)">{{ STAGE_LABEL[stageOf(item)] }}</span></div><div class="qnum">{{ item.inventory?.available ?? '—' }}</div><div class="qnum strong">{{ item.decision?.referenceReplenishmentQuantity ?? item.quantity ?? '—' }}</div><div class="qdate">{{ item.riskDate?.slice(5) || '—' }}</div></a>
        <p v-if="!queue.length" class="empty-inline">{{ state.priorityLoading ? '正在读取…' : '当前没有需优先处理的商品。' }}</p>
      </section>
      <p class="muted small workspace-footnote">参考建议不等于采购指令。提交前核对已有采购、供应商及整箱条件。</p>
    </template>
  </div>
</template>
<style scoped>
.overview{display:flex;align-items:center;gap:36px;padding:28px 36px;margin-bottom:24px}.overview-chart{display:flex;flex-direction:column;align-items:center;gap:8px;color:#74818c}.overview-legend{min-width:220px;max-width:360px}.overview-legend button{display:flex;align-items:center;gap:12px;width:100%;border:0;background:none;text-align:left;padding:10px 0;color:inherit;cursor:pointer;font:inherit}.overview-legend button b{margin-left:auto;font-size:22px}.overview-legend small{display:block;color:#74818c;margin-top:12px}.overview-actions{margin-left:auto;display:flex;align-items:flex-start;flex-direction:column;gap:18px}.risk-link{border:0;padding:0;background:none;color:#a3651a;cursor:pointer;font:inherit}.workspace-footnote{margin:18px 0}.qname small{line-height:1.6}@media(max-width:1000px){.overview{gap:24px;padding:24px;flex-wrap:wrap}.overview-actions{margin-left:0}.overview-legend{min-width:180px}}
</style>
