<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { route, navigate, setQuery } from '../router'
import { init, openBatch, loadList, setFilters, setOffset, startBatch, state, summary, stageOf, latestBatchId, STAGE_LABEL, unitOf } from '../s01'

const q = ref(''), store = ref(''), warehouse = ref(''), source = ref(''), stateFilter = ref('')
let textTimer: ReturnType<typeof setTimeout> | undefined

const SOURCES = ['RULE_CALCULATED', 'REFERENCE_ONLY', 'HISTORICAL_REFERENCE', 'UNVERIFIED', 'UNAVAILABLE']
const STATES = ['ANALYZED', 'ERP_REFERENCE', 'HISTORICAL_REFERENCE', 'NO_REPLENISHMENT', 'NEEDS_REVIEW', 'UNANALYZABLE', 'FAILED', 'PENDING']
const sourceName: Record<string, string> = {
  RULE_CALCULATED: '规则计算', REFERENCE_ONLY: 'ERP 参考建议', HISTORICAL_REFERENCE: '历史销量参考',
  USABLE_FALLBACK: '已核验降级来源', UNVERIFIED: '来源待核实', UNAVAILABLE: '无可用来源'
}
const stateName: Record<string, string> = {
  ANALYZED: '规则建议', ERP_REFERENCE: 'ERP 参考建议', HISTORICAL_REFERENCE: '历史参考分析', NO_REPLENISHMENT: '无需补货',
  NEEDS_REVIEW: '需要核实', UNANALYZABLE: '无法分析', FAILED: '分析失败', PENDING: '等待处理'
}

function syncFromRoute() {
  const query = route.value.query
  q.value = query.q || ''
  store.value = query.store || ''
  warehouse.value = query.warehouse || ''
  source.value = query.source || ''
  stateFilter.value = query.state || ''
  void setFilters({ q: q.value, store: store.value, warehouse: warehouse.value, source: source.value, state: stateFilter.value })
  const offset = Number(query.offset || 0)
  if (offset !== state.offset) void setOffset(offset)
}

function apply(patch: Record<string, string>) {
  navigate('/suggestions', { batch: state.batchId, ...route.value.query, ...patch, offset: undefined })
}

function onText() {
  clearTimeout(textTimer)
  textTimer = setTimeout(() => apply({ q: q.value }), 320)
}

function clearAll() { apply({ q: '', store: '', warehouse: '', source: '', state: '' }) }

const page = () => Math.floor(state.offset / state.limit) + 1
const pages = () => Math.max(1, Math.ceil(state.list.total / state.limit))

onMounted(async () => {
  await init()
  // Apply the URL filters before the first list request so a page entry costs one round trip, not two.
  const query = route.value.query
  q.value = query.q || ''; store.value = query.store || ''; warehouse.value = query.warehouse || ''
  source.value = query.source || ''; stateFilter.value = query.state || ''
  state.filters = { q: query.q || '', store: query.store || '', warehouse: query.warehouse || '', source: query.source || '', state: query.state || '' }
  state.offset = Number(query.offset || 0)
  const id = query.batch || latestBatchId()
  if (!id) return
  await openBatch(id)
  if (query.batch !== id) navigate('/suggestions', { batch: id, ...query })
})

watch(() => route.value.query.batch, async id => { if (id && id !== state.batchId) { await openBatch(id); syncFromRoute() } })
watch(() => route.value.query, (query, prev) => {
  if (route.value.path !== '/suggestions') return
  if (JSON.stringify(query) !== JSON.stringify(prev)) syncFromRoute()
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>补货建议</h1>
        <p class="page-sub">同 SKU 的不同店仓分开展示；来源与状态分别标注，不合并计算</p>
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
        <small>{{ state.list.total }} 个店仓对象{{ state.listLoading ? ' · 读取中…' : '' }}</small>
        <span v-if="summary" class="head-note">规则 {{ summary.ruleCalculated }} · ERP 参考 {{ summary.erpReference }} · 历史参考 {{ summary.historicalReference || 0 }}</span>
      </div>
      <div class="table-scroll">
        <table class="ltable">
          <thead>
            <tr><th>商品 / SKU</th><th>店铺 / 仓库</th><th>来源</th><th>状态</th><th class="r">可用</th><th class="r">建议</th><th>缺货日</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="item in state.list.items" :key="item.entityKey" @click="navigate('/sku/' + item.entityKey, { batch: state.batchId })">
              <td><span class="cell-title">{{ item.name || item.sku }}</span><small class="mono">{{ item.sku }}</small></td>
              <td><span class="cell-title">{{ item.storeName || '店铺待核实' }}</span><small>{{ item.warehouseName || '仓库待核实' }}</small></td>
              <td><span class="chip plain">{{ sourceName[item.sourceGrade] || item.sourceGrade }}</span></td>
              <td><span class="chip" :class="stageOf(item)">{{ STAGE_LABEL[stageOf(item)] }}</span></td>
              <td class="r num">{{ item.inventory?.available ?? '—' }}</td>
              <td class="r num strong">{{ item.quantity ?? '—' }}<small v-if="item.quantity"> {{ unitOf(item) }}</small></td>
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
