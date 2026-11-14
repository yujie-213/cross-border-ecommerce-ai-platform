<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { route, navigate, back } from '../router'
import {
  init, openBatch, openItem, openSingle, createSingle, readRequisition, submitRequisition, replayPending, pendingFor,
  state, summary, stageOf, STAGE_LABEL, unitOf, dash, fmt, latestBatchId
} from '../s01'
import { quantityError, issueLabel } from '../api/v2'
import ProductDecision from '../components/ProductDecision.vue'
import AiAnalysis from '../components/AiAnalysis.vue'
import BalanceChart from '../components/charts/BalanceChart.vue'
import SalesBars from '../components/charts/SalesBars.vue'

const tab = ref<'conditions' | 'quality' | 'history'>('conditions')
const quantity = ref(0)
const reason = ref('')
const acknowledged = ref(false)

const item = computed(() => state.item)
const baseline = computed(() => item.value?.ruleResult?.supplyDemand?.baseline || null)
const forecast = computed(() => item.value?.ruleResult?.forecast || null)
const series = computed(() => baseline.value?.series || [])
const sales = computed(() => forecast.value?.dailySales || [])
const stage = computed(() => (item.value ? stageOf(item.value) : 'review'))
const single = computed(() => state.singleReport)
const ai = computed(() => single.value?.analysisReport?.ai || null)
const requisition = computed(() => state.requisition)
/** Unknown outcome for THIS analysis: blocks any new submission until replayed. */
const pendingHere = computed(() => pendingFor(state.singleId))
const pendingElsewhere = computed(() => (state.pending && state.pending.singleId !== state.singleId) ? state.pending : null)
const unresolvedState = computed(() => ['SUBMIT_UNKNOWN', 'CREATE_UNKNOWN'].includes(requisition.value?.state || ''))
const constraints = computed(() => item.value?.constraints || null)
const eligibility = computed(() => item.value?.procurementEligibility || null)
const quality = computed(() => item.value?.dataQuality || null)
const qualityEntries = computed(() => {
  const value = quality.value
  if (!value) return [] as { name: string; status: string; reasons: string[] }[]
  return (['identity', 'demand', 'inventory', 'procurement'] as const)
    .filter(name => !!value[name])
    .map(name => ({ name, status: value[name].status, reasons: value[name].reasons || [] }))
})
const capabilities = computed(() => item.value?.capabilities || null)
const hints = computed(() => item.value?.recoveryHints || [])
const uniqueHints = computed(() => {
  // Several codes share a generic message; show each distinct explanation once.
  const seen = new Set<string>()
  return hints.value.filter(hint => {
    const key = hint.code + '|' + hint.message
    if (seen.has(key)) return false
    seen.add(key)
    return true
  }).filter((hint, index, list) => list.findIndex(other => other.message === hint.message) === index)
})
const window = computed(() => item.value?.demandWindow || null)

const target = computed(() => baseline.value?.targetQuantity ?? null)
const firstShortage = computed(() => baseline.value?.firstShortageDate || item.value?.riskDate || null)
const coverage = computed(() => baseline.value?.coverageDays ?? null)
const lead = computed(() => forecast.value?.leadDays ?? null)

const blocked = computed(() => {
  const blocks = eligibility.value?.hardBlocks || []
  return blocks.filter(code => !(requisition.value && ['KNOWN_FORMAL_PURCHASE_FOR_SOURCE_PLAN'].includes(code)))
})

const canSubmit = computed(() =>
  !!single.value && !!eligibility.value?.eligible && eligibility.value.scopeAuthorized === true &&
  state.options?.canSubmit === true && !requisition.value)

const validation = computed(() => (item.value ? quantityError(item.value, quantity.value, reason.value) : '数量不可用'))
const submitDisabled = computed(() => !canSubmit.value || !!validation.value || !acknowledged.value || state.busy)

const historyRows = computed(() => state.singleHistory.filter(row => row.entityKey === item.value?.entityKey))

const tabs = [
  { key: 'conditions' as const, label: '采购条件' },
  { key: 'quality' as const, label: '依据与限制' },
  { key: 'history' as const, label: '历史分析', count: () => historyRows.value.length }
]

function step(delta: number) {
  const multiple = constraints.value?.orderMultiple || 1
  const moq = constraints.value?.moq || 1
  const next = Math.max(moq, quantity.value + delta * multiple)
  quantity.value = next
}

async function generate(withAI = true) {
  const key = item.value?.entityKey || state.itemKey
  await createSingle(withAI)
  const singleId = state.singleId
  if (!singleId) return
  // Keep the URL authoritative so refresh / back / forward restore this exact analysis.
  if (route.value.query.single !== singleId) navigate(`/sku/${key}`, { batch: state.batchId, single: singleId })
  quantity.value = item.value?.quantity || 0
  reason.value = ''
  acknowledged.value = false
}

async function submit() {
  if (submitDisabled.value) return
  await submitRequisition(quantity.value, reason.value.trim())
}

onMounted(async () => {
  await init()
  const key = route.value.segments[1]
  const batch = route.value.query.batch || state.batchId || latestBatchId()
  if (batch && batch !== state.batchId) await openBatch(batch)
  if (key) {
    await openItem(key, route.value.query.single)
    quantity.value = state.item?.quantity || 0
  }
})

watch(
  [() => route.value.path, () => route.value.query.single || '', () => route.value.query.batch || ''],
  async ([path]) => {
    if (!path.startsWith('/sku/')) return
    const key = route.value.segments[1]
    if (!key) return
    const batch = route.value.query.batch
    const single = route.value.query.single
    if (batch && batch !== state.batchId) await openBatch(batch)
    // A single analysis and the batch conclusion are two different datasets:
    // switching between them (either direction) must refetch, not reuse stale state.
    if (key !== state.itemKey || (single || '') !== state.singleId) {
      await openItem(key, single)
      quantity.value = state.item?.quantity || 0
      reason.value = ''
      acknowledged.value = false
    }
  }
)

watch(() => item.value?.quantity, value => { if (value !== null && value !== undefined) quantity.value = value })
</script>

<template>
  <div class="page detail">
    <nav class="crumb">
      <a href="#" @click.prevent="back('/suggestions')">← 返回补货建议</a>
      <span v-if="summary" class="crumb-note">{{ summary.scopeObjectCount }} 个对象 · 批次 {{ state.batchId.slice(0, 8) }}</span>
    </nav>

    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>
    <div v-if="state.itemLoading && !item" class="panel empty-inline">正在读取该对象的分析结果…</div>
    <div v-else-if="!item" class="panel empty-state">
      <h2>找不到该分析对象</h2>
      <p>它可能属于另一个批次，或当前授权已不包含该店仓。</p>
      <a class="button" href="#/suggestions">返回补货建议</a>
    </div>

    <template v-else>
      <header class="detail-head">
        <div>
          <h1>{{ item.name || item.sku }}</h1>
          <div class="detail-meta">
            <span class="mono">{{ item.sku }}</span><span class="sep">·</span>
            <span>{{ item.storeName || '店铺待核实' }} / {{ item.warehouseName || '仓库待核实' }}</span><span class="sep">·</span>
            <span class="chip" :class="stage">{{ STAGE_LABEL[stage] }}</span>
            <span class="chip plain">{{ unitOf(item) }}</span>
            <span class="muted small">数据时点 {{ item.observedAt?.slice(0, 16).replace('T', ' ') || '未记录' }}</span>
            <span v-if="single" class="chip info">含单品分析结果</span>
          </div>
        </div>
      </header>

      <ProductDecision v-if="item.decision" :item="item" :scopes="state.item?.relatedScopes || []" @select="key => navigate('/sku/' + key, { batch: state.batchId })" />
      <section v-if="!item.decision" class="verdict" aria-label="规则结论">
        <div class="accent">
          <small>{{ stage === 'history' ? '历史参考' : '规则建议' }}</small>
          <b v-if="item.quantity !== null && item.quantity !== undefined && item.sourceGrade !== 'HISTORICAL_REFERENCE'">{{ item.quantity }}<span>{{ unitOf(item) }}</span></b>
          <b v-else class="none">未形成</b>
          <em v-if="item.sourceGrade === 'REFERENCE_ONLY'">来源 ERP 建议</em>
          <em v-else-if="item.sourceGrade === 'HISTORICAL_REFERENCE'">仅历史销量，不作建议</em>
        </div>
        <div><small>可用库存</small><b>{{ dash(item.inventory?.available) }}<span v-if="item.inventory?.available !== null && item.inventory?.available !== undefined">{{ unitOf(item) }}</span></b><em v-if="item.inventoryBasis?.status">{{ item.inventoryBasis.status }}</em></div>
        <div><small>目标库存</small><b>{{ target === null ? '—' : fmt(target, 0) }}</b><em v-if="target === null">规则未计算</em></div>
        <div>
          <small>覆盖天数</small>
          <b>{{ coverage === null ? '—' : fmt(coverage, 1) }}<span v-if="coverage !== null">天</span></b>
          <em v-if="coverage !== null && lead !== null" :class="{ danger: Number(coverage) < lead }">交期 {{ lead }} 天</em>
        </div>
        <div><small>首次短缺</small><b class="date">{{ firstShortage ? firstShortage.slice(5) : '—' }}</b><em>{{ firstShortage ? '按当前需求推算' : '窗口内无短缺' }}</em></div>
      </section>

      <p v-if="single" class="banner plain analysis-note">
        当前显示该对象一次单品分析的结果（{{ item.observedAt?.slice(0, 16).replace('T', ' ') || '时点未知' }}），它重新读取了事实，可能与本批次结论不同。
        <a :href="'#/sku/' + item.entityKey + '?batch=' + state.batchId">只看本批次结论</a>
      </p>

      <p v-if="pendingElsewhere" class="banner plain small">
        另一个 SKU（{{ pendingElsewhere.sku }}）有一笔结果未确认的请购提交，只能在其详情页用原命令核对；本页不会使用该命令。
        <a :href="'#/sku/' + pendingElsewhere.entityKey + '?batch=' + state.batchId + '&single=' + pendingElsewhere.singleId">前往核对</a>
      </p>

      <p v-if="blocked.length && !item.decision" class="banner warning">
        <strong>当前不可提交：</strong>{{ blocked.map(issueLabel).join('；') }}
        <a href="#" @click.prevent="tab = 'quality'">查看依据</a>
      </p>

      <button v-if="item.decision" class="button" :disabled="state.busy || state.singleLoading" @click="generate(false)">刷新当前店仓分析（不调用 AI）</button>
      <AiAnalysis :ai="ai" :task-state="state.singleTask?.state || null" :loading="state.singleLoading"
                  :error-code="state.singleTask?.errorCode || null" @generate="generate(true)" />

      <section v-if="!item.decision && (forecast || series.length)" class="panel">
        <div class="panel-head">
          <h2>库存与销量</h2>
          <small>{{ series.length ? '按当前可用库存与日均需求推算的结存' : '本次没有可用于预测的完整窗口' }}</small>
        </div>
        <div v-if="series.length" class="chart-block">
          <BalanceChart :series="series" />
        </div>
        <div v-else class="chart-fallback">
          <p>本次未能计算结存预测，原因：</p>
          <ul v-if="uniqueHints.length" class="reason-list">
            <li v-for="hint in uniqueHints.slice(0, 3)" :key="hint.code">{{ hint.message }}</li>
          </ul>
          <p v-else>需要完整的业务日销量与库存流水。</p>
        </div>
        <div class="sales-block">
          <div class="sales-head">
            <span>近 {{ sales.length }} 个完整业务日销量</span>
            <span v-if="forecast" class="muted">合计 {{ fmt(forecast.totalSales, 0) }} · 日均 {{ fmt(forecast.averageDailyDemand, 1) }} · 窗口 {{ forecast.windowStart?.slice(5) }} 至 {{ forecast.windowEnd?.slice(5) }}</span>
          </div>
          <SalesBars v-if="sales.length" :days="sales" :average="fmt(forecast?.averageDailyDemand ?? null, 1)" :total="forecast?.totalSales" />
          <p v-else class="muted small">没有可核验的完整业务日销量。</p>
        </div>
      </section>

      <section v-else-if="!item.decision" class="panel">
        <div class="panel-head"><h2>库存与销量</h2><small>缺少可计算依据</small></div>
        <div class="chart-fallback">
          <ul v-if="uniqueHints.length" class="reason-list">
            <li v-for="hint in uniqueHints.slice(0, 3)" :key="hint.code">{{ hint.message }}</li>
          </ul>
          <p v-else>本次没有完整的库存与销量证据，因此不绘制趋势。</p>
        </div>
        <div v-if="window?.observedHistory?.length" class="sample-block">
          <h4>可用的历史销量样本（{{ window.referenceDays }} 天，{{ window.referenceGrade }}）</h4>
          <ul class="sample-list">
            <li v-for="row in window.observedHistory.slice(-10)" :key="row.businessDate">
              <span>{{ row.businessDate.slice(5) }}</span><b>{{ row.quantity }}</b>
            </li>
          </ul>
          <p class="muted small">历史样本仅用于理解需求水平，不构成补货数量建议。</p>
        </div>
      </section>

      <section class="panel">
        <div class="tabs" role="tablist">
          <button v-for="entry in tabs" :key="entry.key" role="tab" :aria-selected="tab === entry.key"
                  :class="{ active: tab === entry.key }" @click="tab = entry.key">
            {{ entry.label }}<span v-if="entry.count?.()" class="tab-count">{{ entry.count() }}</span>
          </button>
        </div>

        <div v-if="tab === 'conditions'" class="tab-body">
          <div class="kv-grid">
            <dl class="kv">
              <dt>MOQ / 整箱倍数</dt><dd>{{ dash(constraints?.moq) }} / {{ dash(constraints?.orderMultiple) }} {{ unitOf(item) }}</dd>
              <dt>报价 / 币种</dt><dd>{{ dash(constraints?.unitPrice) }} {{ constraints?.currency || '币种未确认' }}</dd>
              <dt>最低采购金额</dt><dd>{{ dash(constraints?.minimumAmount) }}</dd>
            </dl>
            <dl class="kv">
              <dt>供应商</dt><dd>{{ constraints?.supplierName || '未确认' }}</dd>
              <dt>有效报价</dt><dd>{{ constraints?.quoteNo || '未确认' }}</dd>
              <dt>报价有效期</dt><dd>{{ constraints?.quoteValidFrom || '未知' }} 至 {{ constraints?.quoteValidTo || '未知' }}</dd>
            </dl>
          </div>
          <h4 class="sub-head">已有正式采购</h4>
          <div class="table-scroll">
            <table class="ltable compact">
              <thead><tr><th>单据</th><th>状态</th><th class="r">采购 / 已收 / 待收</th><th>计划到货</th><th>可售日期</th></tr></thead>
              <tbody>
                <tr v-for="po in item.formalPurchases || []" :key="po.erpId">
                  <td><span class="mono">{{ po.erpNumber }}</span><small>{{ po.warehouseName || '采购仓待核实' }}<template v-if="po.warehouseMatch === false"> · 其他仓，未计入</template></small></td>
                  <td>{{ po.status }}</td>
                  <td class="r num">{{ dash(po.orderedQuantity) }} / {{ dash(po.receivedQuantity) }} / {{ dash(po.unreceivedQuantity) }}</td>
                  <td class="num">{{ po.plannedArrival?.slice(0, 10) || '未知' }}</td>
                  <td class="num">{{ po.sellableDate || '未确认，未抵扣' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="!item.formalPurchases?.length" class="muted small">本次未取得该店仓的正式采购单据。</p>
        </div>

        <div v-else-if="tab === 'quality' && item.decision" class="tab-body">
          <h4>预测依据与采购限制</h4>
          <p class="muted small">需求采用已登记销售记录的首末日期区间参考，不要求连续到昨天。未知日不补零，当前库存独立读取。</p>
          <ul class="reason-list"><li v-for="line in item.decision.assumptions" :key="line">{{ line }}</li><li v-for="code in blocked" :key="code">{{ issueLabel(code) }}</li></ul>
          <p v-if="!blocked.length" class="muted small">当前采购字段校验通过，仍须重新读取事实、人工确认及独立 ERP 审批。</p>
          <dl class="kv"><dt>历史覆盖</dt><dd>{{ item.decision.forecast.observedDays || 0 }} 个有记录日；仅当前登记销售ID</dd><dt>快照</dt><dd class="mono small">{{ item.snapshotRef }}</dd></dl>
        </div>
        <div v-else-if="tab === 'quality'" class="tab-body">
          <div class="quality-grid">
            <div v-for="entry in qualityEntries" :key="entry.name" class="quality-cell">
              <small>{{ ({ identity: '身份', demand: '需求', inventory: '库存', procurement: '采购' } as Record<string, string>)[entry.name] || entry.name }}</small>
              <span class="chip" :class="entry.status === 'VERIFIED' ? 'confirm' : 'review'">{{ entry.status }}</span>
              <p v-if="entry.reasons.length" class="muted small">{{ entry.reasons.slice(0, 2).map(issueLabel).join('；') }}</p>
            </div>
          </div>

          <div class="cap-row">
            <span v-for="(cap, name) in capabilities || {}" :key="name" class="cap" :class="{ off: !(cap as any).enabled }">
              {{ ({ facts: '事实读取', reference: '参考样本', risk: '风险判断', rules: '规则计算', requisition: '采购提交' } as Record<string, string>)[name] || name }}
              <b>{{ (cap as any).enabled ? '可用' : '受限' }}</b>
            </span>
          </div>

          <div v-if="hints.length" class="hint-list">
            <div v-for="hint in uniqueHints" :key="hint.code" class="hint-row">
              <div><strong>{{ hint.message }}</strong><small>{{ hint.action }}</small></div>
              <span class="mono muted">{{ hint.code }}</span>
            </div>
          </div>
          <p v-else class="muted small">本次没有额外的数据限制。</p>

          <dl class="kv">
            <dt>数据窗口</dt><dd>{{ window ? `${window.validDays} 个有效业务日 / 缺 ${window.missingDays} 天 · ${window.windowStart} 至 ${window.windowEnd}` : '未提供' }}</dd>
            <dt>库存基点</dt><dd>{{ item.inventoryBasis?.status || '未提供' }} · 记录于 {{ item.inventoryBasis?.observedAt?.slice(0, 16)?.replace('T', ' ') || '未知' }}</dd>
            <dt>快照</dt><dd class="mono small">{{ item.snapshotRef || '未形成' }}</dd>
          </dl>
        </div>

        <div v-else class="tab-body">
          <div class="table-scroll">
            <table class="ltable compact">
              <thead><tr><th>分析时间</th><th>状态</th><th>来源</th><th>数量</th><th></th></tr></thead>
              <tbody>
                <tr v-for="row in historyRows" :key="row.taskRef.taskId">
                  <td class="mono">{{ row.taskRef.taskId.slice(0, 10) }}</td>
                  <td>{{ row.state }}</td>
                  <td>{{ row.sourceGrade === 'PLATFORM_REFERENCE' ? '独立补货试算' : row.sourceGrade === 'DEMAND_REFERENCE' ? '需求预测' : row.sourceGrade === 'RULE_CALCULATED' ? '规则计算' : row.sourceGrade === 'REFERENCE_ONLY' ? 'ERP 参考' : row.sourceGrade === 'HISTORICAL_REFERENCE' ? '历史参考' : '—' }}</td>
                  <td>{{ row.state === 'SUCCEEDED' ? '已生成报告' : '—' }}</td>
                  <td class="r">
                    <a v-if="row.state === 'SUCCEEDED'" class="button small"
                       :href="'#/sku/' + item.entityKey + '?batch=' + state.batchId + '&single=' + row.taskRef.taskId">打开</a>
                    <span v-else class="muted small">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="!historyRows.length" class="muted small">该 SKU 还没有单品分析记录。生成一次后可在这里回看历史结论。</p>
          <p v-else class="muted small">打开历史分析会显示当时的结论，不会替换本批次结果。</p>
        </div>
      </section>

      <div class="actionbar">
        <template v-if="requisition">
          <span class="chip" :class="requisition.state === 'SUBMITTED' ? 'info' : 'warning'">
            {{ requisition.state === 'SUBMITTED' ? '已提交 · 待 ERP 审批' : requisition.state }}
          </span>
          <span class="ab-meta"><b>{{ requisition.finalQuantity }}</b> {{ unitOf(item) }}<small>原建议 {{ requisition.aiQuantity }}</small></span>
          <span class="ab-meta"><small>ERP 单号</small>{{ requisition.erpNumber || '待回读' }}</span>
          <span class="ab-meta"><small>ERP 状态</small>{{ requisition.erpStatus || '未知' }}</span>
          <span class="grow" />
          <a class="button small" href="#/requisitions">查看请购</a>
          <button v-if="requisition.state !== 'SUBMITTED' && requisition.state !== 'BLOCKED'" class="button small" :disabled="state.busy" @click="readRequisition">核对状态</button>
        </template>

        <template v-else-if="pendingHere">
          <span class="chip danger">上一笔结果未确认</span>
          <span class="ab-note">该分析在 {{ pendingHere.createdAt.slice(11, 16) }} 提交后未收到回执，禁止重复提交</span>
          <span class="grow" />
          <button class="button primary" :disabled="state.busy" @click="replayPending">
            {{ state.busy ? '核对中…' : '使用原命令核对' }}
          </button>
        </template>

        <template v-else-if="unresolvedState">
          <span class="chip danger">提交结果未确认</span>
          <span class="ab-note">ERP 可能已建单，只能核对这张单据，不能再发起提交</span>
          <span class="grow" />
          <a class="button small" href="#/requisitions">查看请购</a>
          <button class="button" :disabled="state.busy" @click="readRequisition">重新核对状态</button>
        </template>

        <template v-else-if="state.singleTask?.state === 'FAILED' && !single">
          <span class="chip danger">单品分析失败</span>
          <span class="ab-note">{{ state.singleTask.errorCode ? issueLabel(state.singleTask.errorCode) : '服务端未返回错误原因' }}</span>
          <span class="grow" />
          <button class="button primary" :disabled="state.busy || state.singleLoading" @click="generate(false)">
            {{ state.singleLoading ? '正在重试…' : '重试单品分析' }}
          </button>
        </template>

        <template v-else-if="!eligibility?.eligible || item.quantity === null">
          <span class="chip danger">暂不可提交</span>
          <span class="ab-note">{{ item.quantity === null ? '该对象没有可提交的补货数量' : (blocked.length ? blocked.slice(0, 2).map(issueLabel).join('；') : '采购资格尚未通过') }}</span>
          <span class="grow" />
          <a class="button small" href="#" @click.prevent="tab = 'quality'">查看依据</a>
        </template>

        <template v-else-if="!single">
          <span class="ab-note">
            {{ item.quantity === null ? '该对象尚未形成可提交的补货数量' : '提交前需先生成单品分析，读取该店仓最新事实与采购条件' }}
          </span>
          <span class="grow" />
          <button class="button primary" :disabled="state.busy || state.singleLoading" @click="generate(false)">
            {{ state.singleLoading ? '正在读取…' : state.singleTask?.state === 'FAILED' ? '重试单品分析' : '生成单品分析' }}
          </button>
        </template>

        <template v-else>
          <span class="chip" :class="item.sourceGrade === 'REFERENCE_ONLY' ? 'review' : 'confirm'">
            {{ item.sourceGrade === 'RULE_CALCULATED' ? '规则建议' : item.sourceGrade === 'REFERENCE_ONLY' ? 'ERP 参考' : '已核验来源' }}
          </span>
          <span class="ab-meta">建议 <b>{{ item.quantity ?? '—' }}</b> {{ unitOf(item) }}</span>
          <div class="stepper">
            <button type="button" :disabled="state.busy" @click="step(-1)">−</button>
            <input v-model.number="quantity" type="number" :min="constraints?.moq || 1" :step="constraints?.orderMultiple || 1"
                   inputmode="numeric" aria-label="最终采购数量" :disabled="state.busy">
            <button type="button" :disabled="state.busy" @click="step(1)">+</button>
          </div>
          <input v-if="item.quantity !== null && Number(quantity) !== Number(item.quantity)" v-model="reason" class="reason-input"
                 maxlength="200" aria-label="调整原因" placeholder="调整原因（必填）" :disabled="state.busy">
          <label class="check"><input v-model="acknowledged" type="checkbox" :disabled="state.busy"> 已核对来源与在途</label>
          <span class="grow" />
          <span class="ab-note small">{{ validation || '提交后进入 ERP 审批' }}</span>
          <button class="button primary" :disabled="submitDisabled" @click="submit">{{ state.busy ? '提交中…' : '提交请购' }}</button>
        </template>
      </div>
      <p v-if="state.note" class="muted small">{{ state.note }}</p>
    </template>
  </div>
</template>
