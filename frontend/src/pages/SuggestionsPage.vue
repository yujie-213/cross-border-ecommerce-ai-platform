<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { route, navigate, setQuery } from '../router'
import { init, openBatch, loadList, startBatch, state, summary, stageOf, latestBatchId, STAGE_LABEL, unitOf, fmt } from '../s01'

const q = ref(''), store = ref(''), warehouse = ref(''), source = ref(''), stateFilter = ref(''), decision = ref('')
const initializing = ref(true)
let textTimer: ReturnType<typeof setTimeout> | undefined

const SOURCES = ['PLATFORM_REFERENCE', 'DEMAND_REFERENCE', 'RULE_CALCULATED', 'REFERENCE_ONLY', 'HISTORICAL_REFERENCE', 'UNVERIFIED', 'UNAVAILABLE']
const STATES = ['ANALYZED', 'ERP_REFERENCE', 'HISTORICAL_REFERENCE', 'NO_REPLENISHMENT', 'NEEDS_REVIEW', 'UNANALYZABLE', 'FAILED', 'PENDING']
const sourceName: Record<string, string> = {
  PLATFORM_REFERENCE: '平台独立试算', DEMAND_REFERENCE: '独立需求预测', RULE_CALCULATED: '规则计算', REFERENCE_ONLY: 'ERP 参考建议', HISTORICAL_REFERENCE: '历史销量参考',
  USABLE_FALLBACK: '已核验降级来源', UNVERIFIED: '来源待核实', UNAVAILABLE: '无可用来源'
}
const stateName: Record<string, string> = {
  ANALYZED: '建议补货', ERP_REFERENCE: 'ERP 参考建议', HISTORICAL_REFERENCE: '历史参考分析', NO_REPLENISHMENT: '无需补货',
  NEEDS_REVIEW: '需要核实', UNANALYZABLE: '无法分析', FAILED: '分析失败', PENDING: '等待处理'
}

/** URL is the single source of truth for filters and paging. */
function readQuery() {
  const query = route.value.query
  q.value = query.q || ''
  store.value = query.store || ''
  warehouse.value = query.warehouse || ''
  source.value = query.source || ''
  stateFilter.value = query.state || ''
  decision.value = query.decision || ''
  state.filters = { q: q.value, store: store.value, warehouse: warehouse.value, source: source.value, state: stateFilter.value, decision: decision.value }
  state.offset = Math.max(0, Number(query.offset || 0) || 0)
}

const sameAsState = () => {
  const query = route.value.query
  return (query.batch || '') === state.batchId &&
    (query.q || '') === state.filters.q && (query.store || '') === state.filters.store &&
    (query.warehouse || '') === state.filters.warehouse && (query.source || '') === state.filters.source &&
    (query.state || '') === state.filters.state && (query.decision || '') === state.filters.decision && (Number(query.offset || 0) || 0) === state.offset
}

/** Uses the already-open batch when possible; the list still reloads for the new query. */
async function loadForRoute() {
  const batch = route.value.query.batch
  if (batch && (batch !== state.batchId || !state.progress)) await openBatch(batch)
  else await loadList()
}

async function syncFromRoute() {
  readQuery()
  await loadForRoute()
}

function apply(patch: Record<string, string>) {
  navigate('/suggestions', { batch: state.batchId, ...route.value.query, ...patch, offset: undefined })
}

function onText() {
  clearTimeout(textTimer)
  state.listLoading = true
  textTimer = setTimeout(() => { if (route.value.path === '/suggestions') apply({ q: q.value }) }, 320)
}
onUnmounted(() => clearTimeout(textTimer))

function clearAll() { apply({ q: '', store: '', warehouse: '', source: '', state: '', decision: '' }) }

const page = () => Math.floor(state.offset / state.limit) + 1
const pages = () => Math.max(1, Math.ceil(state.list.total / state.limit))

onMounted(async () => {
  await init()
  readQuery()
  const batch = route.value.query.batch || latestBatchId()
  if (!batch) { await loadList(); initializing.value = false; return }
  // One list request per entry, already carrying the URL filters and offset.
  if (batch !== state.batchId || !state.progress) await openBatch(batch)
  else await loadList()
  if (route.value.path === '/suggestions' && route.value.query.batch !== batch) navigate('/suggestions', { batch, ...route.value.query })
  initializing.value = false
})

watch(() => route.value.query, (query, previous) => {
  if (route.value.path !== '/suggestions') return
  if (JSON.stringify(query) === JSON.stringify(previous)) return
  if (sameAsState()) return
  void syncFromRoute()
})
</script>

<template>
  <div class="page buyer-list">
    <header class="page-head"><div><h1>商品与补货建议</h1></div><div class="head-actions"><button class="button" :disabled="state.busy" @click="startBatch().then(id => id && navigate('/suggestions',{batch:id}))">{{ state.busy ? '正在受理…' : '重新检查商品' }}</button></div></header>
    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>
    <section class="panel buyer-filters"><div class="filters"><label class="field grow"><span>查找商品</span><input v-model="q" :disabled="initializing" type="search" placeholder="商品名称或 SKU" @input="onText" @keyup.enter="apply({q})"></label><label class="field"><span>补货判断</span><select :value="decision" @change="apply({decision:($event.target as HTMLSelectElement).value})"><option value="">全部商品</option><option value="REPLENISH">需要补货</option><option value="NO_REPLENISHMENT">暂不补货</option><option value="NEEDS_REVIEW">需要核实</option><option value="RISK">缺货风险</option><option value="DIFFERENCE">ERP 明显差异</option></select></label><label class="field"><span>仓库</span><select :value="warehouse" @change="apply({warehouse:($event.target as HTMLSelectElement).value})"><option value="">全部仓库</option><option v-for="row in state.list.warehouses" :key="row[0]" :value="row[0]">{{ row[1] }}</option></select></label><button class="button small ghost" @click="clearAll">清空筛选</button></div><details class="advanced-filters"><summary>店铺与历史检查</summary><div class="filters"><label class="field">店铺<select :value="store" @change="apply({store:($event.target as HTMLSelectElement).value})"><option value="">全部店铺</option><option v-for="row in state.list.stores" :key="row[0]" :value="row[0]">{{ row[1] }}</option></select></label><label class="field">检查时间<select :value="state.batchId" @change="navigate('/suggestions',{batch:($event.target as HTMLSelectElement).value})"><option v-for="task in state.batches" :key="task.taskRef.taskId" :value="task.taskRef.taskId">{{ task.createdAt ? new Date(task.createdAt).toLocaleString('zh-CN') : '时间未记录' }}</option></select></label></div></details></section>
    <section class="panel product-table"><div class="panel-head"><h2>{{ decision ? '符合条件的商品' : '登记商品' }} <span class="muted small">{{ state.list.total }} 款</span></h2><span v-if="state.listLoading" role="status">正在读取…</span><span v-else class="small muted">按业务风险排序</span></div><div class="table-scroll"><table class="ltable"><thead><tr><th>商品</th><th>补货判断</th><th>各仓需求</th><th>库存 / 需求摘要</th><th>缺货风险</th><th>操作</th></tr></thead><tbody><tr v-for="item in state.list.items" :key="item.entityKey"><td><span class="cell-title">{{ item.name || item.sku }}</span><small class="mono">{{ item.sku }}</small></td><td><span class="chip" :class="stageOf(item)">{{ STAGE_LABEL[stageOf(item)] }}</span></td><td><b>{{ item.productSummary?.replenishScopeCount || 0 }} / {{ item.productSummary?.scopeCount || 1 }} 个店仓需补</b><small>{{ item.productSummary?.warehouseCount || 1 }} 个仓库</small></td><td><span>{{ (item.productSummary?.scopeCount || 1) > 1 ? '库存按仓查看' : '库存 '+(item.inventory?.available ?? '—')+' 件' }}</span><small>参考补充 {{ item.productSummary?.referencePlanTotal ?? item.decision?.referenceReplenishmentQuantity ?? item.quantity ?? '—' }} 件</small></td><td><b :class="{'danger':!!item.riskDate}">{{ item.riskDate ? item.riskDate.slice(5).replace('-','/')+' 起' : stageOf(item)==='none' ? '规划期内充足' : '日期待核实' }}</b><small>{{ item.decision?.forecast.available ? item.decision.forecast.observedDays+' 个有记录日' : '销量依据待核实' }}</small></td><td><a class="button small" :aria-disabled="state.listLoading || q !== (route.query.q || '')" @click="(state.listLoading || q !== (route.query.q || '')) && $event.preventDefault()" :href="'#/sku/'+item.entityKey+'?batch='+state.batchId">分析商品 →</a></td></tr></tbody></table></div><div v-if="!state.list.items.length && !state.listLoading" class="empty-state"><h3>没有符合条件的商品</h3><p>可清空筛选，或返回工作区检查登记商品。</p><button class="button" @click="clearAll">清空筛选</button></div><div class="table-foot"><span>{{ state.offset+1 }}–{{ Math.min(state.offset+state.limit,state.list.total) }} / {{ state.list.total }}</span><div class="pager"><button class="button small" :disabled="state.offset===0" @click="setQuery({offset:Math.max(0,state.offset-state.limit)})">上一页</button><span>{{ page() }} / {{ pages() }}</span><button class="button small" :disabled="state.offset+state.limit>=state.list.total" @click="setQuery({offset:state.offset+state.limit})">下一页</button></div></div></section>
  </div>
</template>
