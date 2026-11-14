<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { route, navigate } from '../router'
import { init, openBatch, startBatch, cancelBatch, state, summary, grouped, stageOf, latestBatchId, STAGE_LABEL, unitOf, PRIORITY_LIMIT } from '../s01'
import DonutChart from '../components/charts/DonutChart.vue'

const batches = computed(() => state.batches)
const current = computed(() => summary.value)
const loading = computed(() => !current.value && (state.progressLoading || !!state.batchId))
const running = computed(() => !!state.progress && !['SUCCEEDED', 'FAILED', 'CANCELLED'].includes(state.progress.task.state))

const kpis = computed(() => {
  const s = current.value
  if (s?.judgedScopeCount !== undefined) return [
    { label: '不同 SKU', value: s.discoveredSkuCount, filter: {} },
    { label: '已预测 SKU', value: s.analyzedSkuCount || 0, filter: { decision: 'FORECAST' } },
    { label: '需补货 SKU', value: s.replenishSkuCount || 0, filter: { decision: 'REPLENISH' } },
    { label: '暂不补货 SKU', value: s.noReplenishmentSkuCount || 0, filter: { decision: 'NO_REPLENISHMENT' } },
    { label: '缺货风险 SKU', value: s.riskSkuCount || 0, filter: { decision: 'RISK' } }
  ]
  return [
    { label: '规则建议', value: s?.ruleCalculated ?? 0, filter: { state: 'ANALYZED' } },
    { label: 'ERP 参考', value: s?.erpReference ?? 0, filter: { state: 'ERP_REFERENCE' } },
    { label: '需核实', value: s?.unanalyzable ?? 0, filter: { state: 'NEEDS_REVIEW' } },
    { label: '历史参考', value: s?.historicalReference ?? 0, filter: { state: 'HISTORICAL_REFERENCE' } },
    { label: '无需补货', value: s?.noReplenishment ?? 0, filter: { state: 'NO_REPLENISHMENT' } }
  ]
})

// Owned dataset: the batch's own priority order, never the list page's filtered query.
const queue = computed(() => state.priority
  .filter(item => !['none', 'pending', 'history'].includes(stageOf(item)))
  .slice(0, 6))

const sourceRows = computed(() => {
  const s = current.value
  if (!s) return []
  const total = Math.max(1, s.scopeObjectCount)
  if (s.forecastScopeCount !== undefined) return [
    { label: '独立需求预测', count: s.forecastScopeCount, color: '#0f6b64' },
    { label: '尚无可信需求样本', count: s.scopeObjectCount - s.forecastScopeCount, color: '#c9812f' }
  ].filter(r => r.count > 0).map(r => ({ ...r, percent: Math.round(r.count / total * 100) }))
  const uncovered = Math.max(0, s.scopeObjectCount - s.ruleCalculated - s.erpReference - (s.historicalReference || 0) - s.noReplenishment)
  return [
    { label: '规则计算', count: s.ruleCalculated, color: '#0f6b64' },
    { label: 'ERP 参考', count: s.erpReference, color: '#c9812f' },
    { label: '历史参考', count: s.historicalReference || 0, color: '#7a8fa6' },
    { label: '无可提交来源', count: uncovered, color: '#a8382f' }
  ].filter(row => row.count > 0).map(row => ({ ...row, percent: Math.round(row.count / total * 100) }))
})

const shortest = computed(() => state.priority
  .filter(item => item.riskDate && !['none', 'pending'].includes(stageOf(item)))
  .slice()
  .sort((a, b) => String(a.riskDate).localeCompare(String(b.riskDate)))
  .slice(0, 4))

const incomplete = computed(() => Object.entries(state.progress?.sourceLimits || {}).filter(([, value]) => !value.complete))

async function open(id: string) {
  await openBatch(id)
  // The user may have navigated away while the batch was loading; never steal their route.
  if (route.value.path === '/workbench' && route.value.query.batch !== id) navigate('/workbench', { batch: id })
}

onMounted(async () => {
  await init()
  const id = route.value.query.batch || latestBatchId()
  if (id) await open(id)
})

watch(() => route.value.query.batch, async id => { if (id && id !== state.batchId) await openBatch(id) })

async function rerun() {
  const id = await startBatch()
  if (id && route.value.path === '/workbench') navigate('/workbench', { batch: id })
}

function kpi(filter: Record<string, string | undefined>) { navigate('/suggestions', { batch: state.batchId, ...filter }) }
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>补货决策工作台</h1>
        <p class="page-sub">登记自有商品 · 全部获准店仓分别预测与判断 · 不扫描共享商品</p>
      </div>
      <div class="head-actions">
        <label class="select-wrap">
          <span class="sr-only">检查批次</span>
          <select :value="state.batchId" @change="open(($event.target as HTMLSelectElement).value)">
            <option v-for="task in batches" :key="task.taskRef.taskId" :value="task.taskRef.taskId">
              {{ new Date(task.deadline).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }} · {{ task.state === 'SUCCEEDED' ? '已完成' : task.state === 'RUNNING' ? '进行中' : '未完成' }}
            </option>
            <option v-if="!batches.length" value="">尚无检查批次</option>
          </select>
        </label>
        <button class="button primary" :disabled="state.busy" @click="rerun">{{ state.busy ? '已受理…' : '重新检查自有商品' }}</button>
      </div>
    </header>

    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>

    <section v-if="!state.batchId && !loading" class="panel empty-state">
      <h2>还没有检查批次</h2>
      <p>点击“重新检查自有商品”读取已登记自有商品及店仓的当前事实。批量检查只读，不调用模型，也不创建采购单据。</p>
      <button class="button primary" :disabled="state.busy" @click="rerun">开始首次检查</button>
    </section>

    <section v-else-if="loading" class="panel loading-state">
      <span class="spinner" />正在读取批次结果与对象统计…
    </section>

    <template v-else-if="current">
      <p v-if="state.progress?.analysisRange === 'LEGACY_SHARED'" class="banner warning">当前为历史共享目录批次，保留原始结果。点击重新检查自有商品，生成当前登记范围的分析。</p>
      <div v-if="running" class="run-strip">
        <span class="pulse" />正在检查 · 已处理 {{ current.processedCount }} / {{ current.scopeObjectCount || '—' }}
        <span class="run-note">结果持续保存，可离开本页</span><button class="button small" :disabled="state.busy" @click="cancelBatch">停止本次分析</button>
      </div>
      <p v-if="['CANCELLED', 'FAILED'].includes(state.progress?.task.state || '')" class="banner warning">
        本次分析{{ state.progress?.task.state === 'CANCELLED' ? '已停止' : '失败' }}，不能视为已完成。重新检查将读取当前登记自有商品的最新事实。
      </p>

      <p v-if="current.judgedScopeCount !== undefined" class="banner plain">已识别 <b>{{ current.discoveredSkuCount }}</b> 个自有 SKU、{{ current.scopeObjectCount }} 个店仓对象；可判断 {{ current.judgedSkuCount }} 个 SKU / {{ current.judgedScopeCount }} 个店仓。需补货 {{ current.replenishScopeCount }} 个店仓，ERP 明显差异 {{ current.erpDifferenceSkuCount }} 个 SKU。<br>预测覆盖 {{ ((current.forecastCoverage || 0) * 100).toFixed(1) }}%；无可信销量的对象明确待核实，不拿 ERP 建议冒充独立分析。</p>
      <p v-if="current.erpDifferenceSkuCount" class="banner plain"><a :href="'#/suggestions?batch=' + state.batchId + '&decision=DIFFERENCE'">查看 {{ current.erpDifferenceSkuCount }} 个与 ERP 明显不同的商品</a></p>
      <div class="top-split">
        <section class="panel kpi-panel">
          <div class="kpi-row">
            <button v-for="entry in kpis" :key="entry.label" class="kpi" @click="kpi(entry.filter)">
              <b>{{ entry.value }}</b><span>{{ entry.label }}</span>
            </button>
          </div>
        </section>

        <section class="panel compose-panel">
          <div class="panel-head"><h2>对象构成</h2><small>{{ current.scopeObjectCount }} 个店仓对象</small></div>
          <div class="compose">
            <div class="compose-donut"><DonutChart :segments="grouped" :total="current.scopeObjectCount" :size="124" /></div>
            <div class="compose-list">
              <div v-for="group in grouped" :key="group.key" class="compose-row">
                <i class="dot" :style="{ background: group.color }" /><span>{{ group.label }}</span><b>{{ group.count }}</b>
              </div>
            </div>
          </div>
        </section>
      </div>

      <p v-if="current.failed + current.unfinished > 0" class="banner warning">
        {{ current.failed }} 个对象分析失败、{{ current.unfinished }} 个未完成；这些对象不代表无需补货，需重新检查。
      </p>
      <p v-if="incomplete.length" class="banner warning">
        部分业务事实读取不完整：{{ incomplete.map(([name, value]) => name + '（' + (value.error || '分页未完成') + '）').join('；') }}
      </p>

      <div class="main-split">
        <section class="panel">
          <div class="panel-head">
            <h2>优先处理</h2>
            <small>优先查看缺货风险和需补仓库 · 前 {{ PRIORITY_LIMIT }} 个店仓中的重点</small>
            <a class="button small" :href="'#/suggestions?batch=' + state.batchId">全部 {{ current.scopeObjectCount }} 项</a>
          </div>
          <div class="qhead"><span>商品 / SKU</span><span>来源 · 状态</span><span class="r">可用</span><span class="r">建议</span><span>缺货日</span></div>
          <a v-for="item in queue" :key="item.entityKey" class="qrow" :href="'#/sku/' + item.entityKey + '?batch=' + state.batchId">
            <div class="qname"><span>{{ item.name || item.sku }}</span><small>{{ item.sku }} · {{ item.storeName || '店铺待核实' }} / {{ item.warehouseName || '仓库待核实' }}</small></div>
            <div class="qmid">
              <span class="chip" :class="stageOf(item)">{{ STAGE_LABEL[stageOf(item)] }}</span>
              <small>{{ item.decision ? '平台独立试算' : item.sourceGrade === 'RULE_CALCULATED' ? '平台规则' : item.sourceGrade === 'REFERENCE_ONLY' ? 'ERP 源' : item.sourceGrade === 'HISTORICAL_REFERENCE' ? '历史参考' : '待核实' }}</small>
            </div>
            <div class="qnum">{{ item.inventory?.available ?? '—' }}</div>
            <div class="qnum strong">{{ item.decision?.referenceReplenishmentQuantity ?? item.quantity ?? '—' }}<small v-if="item.quantity">{{ unitOf(item) }}</small></div>
            <div class="qdate">{{ item.riskDate ? item.riskDate.slice(5) : '—' }}</div>
          </a>
          <div v-if="!queue.length && state.priorityLoading" class="empty-inline">正在读取结果…</div>
          <div v-else-if="!queue.length" class="empty-inline">当前批次没有待处理对象。</div>
        </section>

        <div class="side-stack">
          <section class="panel">
            <div class="panel-head"><h2>辅助 · 数据来源</h2><small>占全部对象</small></div>
            <div class="mini">
              <div v-for="row in sourceRows" :key="row.label" class="mini-row">
                <i class="dot" :style="{ background: row.color }" /><span>{{ row.label }}</span><b>{{ row.count }}</b><small>{{ row.percent }}%</small>
              </div>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head"><h2>较早缺货</h2><small>前 {{ PRIORITY_LIMIT }} 项内</small></div>
            <div class="mini">
              <a v-for="item in shortest" :key="item.entityKey" class="mini-row link" :href="'#/sku/' + item.entityKey + '?batch=' + state.batchId">
                <span class="mono">{{ item.sku }}</span><b>{{ item.riskDate?.slice(5) }}</b>
              </a>
              <p v-if="!shortest.length" class="mini-empty">前 {{ PRIORITY_LIMIT }} 项没有可用缺货日期</p>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head"><h2>本次检查</h2><small>{{ running ? '进行中' : state.progress?.task.state === 'SUCCEEDED' ? '已完成' : '未完成' }}</small></div>
            <dl class="kv">
              <dt>对象 / 已处理</dt><dd>{{ current.scopeObjectCount }} / {{ current.processedCount }}</dd>
              <dt>有可查看结论</dt><dd>{{ (current.coverage * 100).toFixed(0) }}%</dd>
              <dt>模型调用 / 业务写入</dt><dd>{{ current.modelCalls }} / {{ current.businessMutations }}</dd>
              <dt>枚举完整</dt><dd>{{ state.progress?.enumerationComplete === true ? '是' : state.progress?.enumerationComplete === false ? '否' : '未知' }}</dd>
              <dt>统计口径</dt><dd>{{ state.progress?.statisticsVersion || '—' }}</dd>
            </dl>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>
