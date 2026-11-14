<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { route, navigate, setQuery } from '../router'
import { init, openBatch, loadList, startBatch, state, summary, stageOf, latestBatchId, STAGE_LABEL, unitOf } from '../s01'

const q = ref(''), store = ref(''), warehouse = ref(''), source = ref(''), stateFilter = ref(''), decision = ref('')
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
  textTimer = setTimeout(() => apply({ q: q.value }), 320)
}

function clearAll() { apply({ q: '', store: '', warehouse: '', source: '', state: '', decision: '' }) }

const page = () => Math.floor(state.offset / state.limit) + 1
const pages = () => Math.max(1, Math.ceil(state.list.total / state.limit))

onMounted(async () => {
  await init()
  readQuery()
  const batch = route.value.query.batch || latestBatchId()
  if (!batch) { await loadList(); return }
  // One list request per entry, already carrying the URL filters and offset.
  if (batch !== state.batchId || !state.progress) await openBatch(batch)
  else await loadList()
  if (route.value.path === '/suggestions' && route.value.query.batch !== batch) navigate('/suggestions', { batch, ...route.value.query })
})

watch(() => route.value.query, (query, previous) => {
  if (route.value.path !== '/suggestions') return
  if (JSON.stringify(query) === JSON.stringify(previous)) return
  if (sameAsState()) return
  void syncFromRoute()
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>商品与补货建议</h1>
        <p class="page-sub">当前检查仅登记自有商品；进入商品查看全部获准店仓，各店仓独立判断</p>
      </div>
      <div class="head-actions">
        <label class="select-wrap">
          <span class="sr-only">检查批次</span>
          <select :value="state.batchId" @change="navigate('/suggestions', { batch: ($event.target as HTMLSelectElement).value })">
            <option v-for="task in state.batches" :key="task.taskRef.taskId" :value="task.taskRef.taskId">
              {{ new Date(task.deadline).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }} · {{ task.state === 'SUCCEEDED' ? '已完成' : '进行中' }}
            </option>
          </select>
        </label>
        <button class="button" :disabled="state.busy" @click="startBatch().then(id => id && navigate('/suggestions', { batch: id }))">重新检查</button>
      </div>
    </header>

    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>

    <section class="panel filters-panel">
      <div class="filters">
        <label class="field"><span>业务判断</span><select :value="decision" @change="apply({ decision: ($event.target as HTMLSelectElement).value })"><option value="">全部判断</option><option value="REPLENISH">建议补货</option><option value="NO_REPLENISHMENT">暂不补货</option><option value="NEEDS_REVIEW">依据不足</option><option value="RISK">缺货风险</option><option value="DIFFERENCE">ERP 明显差异</option></select></label>
        <label class="field grow">
          <span>SKU / 商品</span>
          <input v-model="q" type="search" placeholder="搜索 SKU 或商品名称" @input="onText" @keyup.enter="apply({ q })">
        </label>
        <label class="field">
          <span>店铺</span>
          <select :value="store" @change="apply({ store: ($event.target as HTMLSelectElement).value })">
            <option value="">全部店铺</option>
            <option v-for="row in state.list.stores" :key="row[0]" :value="row[0]">{{ row[1] || '归属待核实' }}</option>
          </select>
        </label>
        <label class="field">
          <span>仓库</span>
          <select :value="warehouse" @change="apply({ warehouse: ($event.target as HTMLSelectElement).value })">
            <option value="">全部仓库</option>
            <option v-for="row in state.list.warehouses" :key="row[0]" :value="row[0]">{{ row[1] || '归属待核实' }}</option>
          </select>
        </label>
        <label class="field">
          <span>来源</span>
          <select :value="source" @change="apply({ source: ($event.target as HTMLSelectElement).value })">
            <option value="">全部来源</option>
            <option v-for="value in SOURCES" :key="value" :value="value">{{ sourceName[value] }}</option>
          </select>
        </label>
        <label class="field">
          <span>状态</span>
          <select :value="stateFilter" @change="apply({ state: ($event.target as HTMLSelectElement).value })">
            <option value="">全部状态</option>
            <option v-for="value in STATES" :key="value" :value="value">{{ stateName[value] }}</option>
          </select>
        </label>
        <button class="button small ghost" @click="clearAll">清空</button>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>结果</h2>
        <small>{{ state.list.total }} 个不同 SKU{{ state.listLoading ? ' · 读取中…' : '' }}</small>
        <span v-if="summary" class="head-note">目录 {{ summary.discoveredSkuCount }} SKU / {{ summary.scopeObjectCount }} 店仓 · 需补 {{ summary.replenishScopeCount ?? summary.ruleCalculated }} 店仓</span>
      </div>
      <div class="table-scroll">
        <table class="ltable">
          <thead>
            <tr><th>商品 / SKU</th><th>业务范围</th><th>需求依据</th><th>补货判断</th><th class="r">库存概况</th><th class="r">各仓参考计划合计</th><th>最早缺货</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="item in state.list.items" :key="item.entityKey" @click="navigate('/sku/' + item.entityKey, { batch: state.batchId })">
              <td><span class="cell-title">{{ item.name || item.sku }}</span><small class="mono">{{ item.sku }}</small></td>
              <td><span class="cell-title">{{ item.productSummary?.storeCount || 0 }} 店铺 / {{ item.productSummary?.warehouseCount || 0 }} 仓库</span><small>{{ item.productSummary?.scopeCount || 1 }} 个店仓 · 进入逐仓查看</small></td>
              <td><span class="chip plain">{{ item.decision?.forecast.available ? '可信历史独立预测' : sourceName[item.sourceGrade] || item.sourceGrade }}</span><small v-if="item.decision?.forecast.available">{{ item.decision.forecast.observedDays }} 有记录日 / {{ item.decision.forecast.spanDays }} 天跨度</small></td>
              <td><span class="chip" :class="stageOf(item)">{{ STAGE_LABEL[stageOf(item)] }}</span></td>
              <td class="r num">{{ (item.productSummary?.scopeCount || 1) > 1 ? '按仓查看' : item.inventory?.available ?? '—' }}</td>
              <td class="r num strong">{{ item.productSummary?.referencePlanTotal ?? item.decision?.referenceReplenishmentQuantity ?? item.quantity ?? '—' }}<small v-if="item.quantity"> {{ unitOf(item) }}</small></td>
              <td class="num">{{ item.riskDate ? item.riskDate.slice(5) : '—' }}</td>
              <td class="r"><a class="button small" :href="'#/sku/' + item.entityKey + '?batch=' + state.batchId" @click.stop>查看</a></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!state.list.items.length && !state.listLoading" class="empty-inline">
        {{ state.batchId ? '没有符合筛选条件的对象。' : '请选择或新建一个检查批次。' }}
      </div>
      <footer class="table-foot">
        <span>第 {{ page() }} / {{ pages() }} 页 · 每页 {{ state.limit }}</span>
        <div class="pager">
          <button class="button small" :disabled="state.offset === 0" @click="setQuery({ offset: state.offset - state.limit || undefined })">上一页</button>
          <button class="button small" :disabled="state.offset + state.limit >= state.list.total"
                  @click="setQuery({ offset: state.offset + state.limit })">下一页</button>
        </div>
      </footer>
    </section>
  </div>
</template>
