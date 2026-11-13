<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { request, errorText, ApiError } from '../api/client'
import type { Task } from '../api/types'
import type { V2Options, V2Item, V2Progress, V2Summary, V2List, V2Single, PendingV2, V2Requisition } from '../api/v2'
import { sourceLabel, stateLabel, quantityError, issueLabel, unitLabel } from '../api/v2'
import { terminal, shown } from '../domain'
import Panel from './Panel.vue'
import Notice from './Notice.vue'
import StatusBadge from './StatusBadge.vue'
const emit = defineEmits<{ denied: [] }>()
const options = ref<V2Options | null>(null), progress = ref<V2Progress | null>(null), listing = ref<V2List | null>(null)
const selected = ref<V2Item | null>(null), single = ref<V2Single | null>(null), requisition = ref<V2Requisition | null>(null)
const history = ref<Task[]>([]), historyCursor = ref<string | null>(null), singleHistory = ref<(Task & { sku?: string; sourceGrade?: string })[]>([])
const error = ref(''), busy = ref(false), pending = ref<PendingV2 | null>(null), note = ref('')
const q = ref(''), store = ref(''), warehouse = ref(''), state = ref(''), source = ref(''), risk = ref(''), offset = ref(0)
const quantity = ref(0), reason = ref(''), acknowledged = ref(false), evidence = ref(false)
let storage = '', batchId = '', singleId = '', epoch = 0, listEpoch = 0, detailEpoch = 0, timer: ReturnType<typeof setTimeout> | undefined
let controller = new AbortController()
let singleTimer: ReturnType<typeof setTimeout> | undefined
const summary = computed<V2Summary | null>(() => progress.value?.summary || null)
const current = computed(() => single.value?.report?.dataReport.item || selected.value)
const validation = computed(() => current.value ? quantityError(current.value, quantity.value, reason.value) : '')
const canSubmit = computed(() => !!current.value?.procurementEligibility?.eligible && current.value.procurementEligibility.scopeAuthorized === true && options.value?.canSubmit === true && !!single.value?.report)
function persist() { if (storage) sessionStorage.setItem(storage, JSON.stringify({ batchId, singleId, pending: pending.value })) }
function stop() { clearTimeout(timer); clearTimeout(singleTimer); epoch++; controller.abort(); controller = new AbortController() }
function fail(e: unknown) {
  error.value = errorText(e)
  if (e instanceof ApiError && [401, 403].includes(e.status)) { stop(); listing.value = null; selected.value = null; single.value = null; progress.value = null; requisition.value = null; history.value = []; singleHistory.value = []; emit('denied') }
}
async function loadHistory(before?: string) {
  try { const params = before ? '?before=' + encodeURIComponent(before) : ''; const data = await request<{ items: Task[]; nextCursor: string | null }>('/s01/v2/batches' + params, {}, controller.signal); history.value = data.items; historyCursor.value = data.nextCursor }
  catch (e) { if (!controller.signal.aborted) fail(e) }
}
async function loadList() {
  if (!batchId) return
  const mine = ++listEpoch, id = batchId
  const params = new URLSearchParams({ limit: '50', offset: String(offset.value), q: q.value, store: store.value, warehouse: warehouse.value, state: state.value, source: source.value, risk: risk.value })
  try { const data = await request<V2List>(`/s01/v2/batches/${id}/items?${params}`, {}, controller.signal); if (mine === listEpoch && id === batchId) listing.value = data }
  catch (e) { if (mine === listEpoch && !controller.signal.aborted) fail(e) }
}
async function poll(mine: number, count = 0) {
  if (mine !== epoch || !batchId) return
  try {
    const data = await request<V2Progress>(`/s01/v2/batches/${batchId}`, {}, controller.signal)
    if (mine !== epoch) return
    progress.value = data; await loadList()
    if (!terminal(data.task.state) && count < 300) timer = setTimeout(() => void poll(mine, count + 1), 2000)
    else { note.value = terminal(data.task.state) ? '' : '自动查询已到上限，可手动刷新实际状态。'; await loadHistory() }
  } catch (e) { if (mine === epoch && !controller.signal.aborted) fail(e) }
}
async function openBatch(id: string) {
  stop(); detailEpoch++; batchId = id; singleId = ''; single.value = null; selected.value = null; requisition.value = null; evidence.value = false
  progress.value = null; listing.value = null; error.value = ''; offset.value = 0; persist(); await poll(epoch)
}
async function openItem(item: V2Item) {
  clearTimeout(singleTimer)
  const mine = ++detailEpoch; singleId = ''; single.value = null; requisition.value = null; selected.value = null; evidence.value = false; acknowledged.value = false; error.value = ''; persist()
  try { const value = await request<V2Item>(`/s01/v2/batches/${batchId}/items/${item.entityKey}`, {}, controller.signal); if (mine === detailEpoch) selected.value = value }
  catch (e) { if (mine === detailEpoch) fail(e) }
}
async function pollSingle(id: string, mine: number, count = 0) {
  try {
    const data = await request<V2Single>(`/s01/v2/singles/${id}`, {}, controller.signal)
    if (mine !== detailEpoch || id !== singleId) return
    single.value = data
    if (data.report) { selected.value = data.report.dataReport.item; quantity.value = selected.value.quantity || 0; reason.value = ''; acknowledged.value = false; await readRequisition(); await loadSingleHistory() }
    else if (!terminal(data.task.state) && count < 300) singleTimer = setTimeout(() => void pollSingle(id, mine, count + 1), 2000)
  } catch (e) { if (mine === detailEpoch) fail(e) }
}
async function loadSingleHistory() {
  try { singleHistory.value = (await request<{ items: (Task & { sku?: string; sourceGrade?: string })[] }>('/s01/v2/singles', {}, controller.signal)).items }
  catch (e) { fail(e) }
}
async function openSingle(id: string) { clearTimeout(singleTimer); singleId = id; detailEpoch++; single.value = null; selected.value = null; requisition.value = null; persist(); await pollSingle(id, detailEpoch) }
async function readRequisition() {
  if (!singleId || !options.value?.canSubmit) return
  const id = singleId, mine = detailEpoch
  try { const value = await request<V2Requisition | null>(`/s01/v2/singles/${id}/requisition`, {}, controller.signal); if (mine === detailEpoch && id === singleId) requisition.value = value }
  catch (e) { if (mine === detailEpoch) fail(e) }
}
async function send(command: PendingV2) {
  if (busy.value) return
  pending.value = command; busy.value = true; error.value = ''; persist()
  const actionEpoch = epoch, actionDetail = detailEpoch
  const requisitionTarget = command.path.match(/\/singles\/([^/]+)\/requisition/)?.[1]
  try {
    const value = await request<Task | V2Requisition>(command.path, { method: 'POST', headers: { 'Idempotency-Key': command.key }, body: JSON.stringify(command.body) }, undefined, command.kind === 'requisition' ? 90000 : 15000)
    pending.value = null; persist()
    if (command.kind === 'batch') { if (actionEpoch === epoch) await openBatch((value as Task).taskRef.taskId); else { await loadHistory(); note.value = '新批次已受理，可从历史打开。' } }
    else if (command.kind === 'single') { if (actionDetail === detailEpoch) await openSingle((value as Task).taskRef.taskId); else { await loadSingleHistory(); note.value = '单品分析已受理，可从单品历史打开。' } }
    else if (command.kind === 'requisition') { if (actionDetail === detailEpoch && requisitionTarget === singleId) requisition.value = value as V2Requisition; else note.value = '原单品请购结果已保存，请从对应单品历史核对。' }
    else if (batchId) await poll(epoch)
  } catch (e) { if (e instanceof ApiError && e.status >= 400 && e.status < 500) { pending.value = null; persist() }; fail(e) }
  finally { busy.value = false }
}
function command(kind: PendingV2['kind'], path: string, body: object) { if (!pending.value) void send({ kind, path, body, key: crypto.randomUUID(), createdAt: new Date().toISOString(), displayHint: current.value?.sku }) }
function startAll() { command('batch', '/s01/v2/batches', {}) }
function newSingle() { const basis = single.value?.report ? singleId : batchId; if (selected.value && basis) command('single', '/s01/v2/singles', { batchId: basis, entityKey: selected.value.entityKey }) }
function submit() { if (canSubmit.value && !validation.value && acknowledged.value) command('requisition', `/s01/v2/singles/${singleId}/requisition`, { finalQuantity: quantity.value, adjustmentReason: reason.value, sourceAcknowledged: true }) }
function resumeRequisition() { if (requisition.value) command('requisition', `/s01/v2/singles/${singleId}/requisition`, { finalQuantity: requisition.value.finalQuantity, adjustmentReason: requisition.value.adjustmentReason, sourceAcknowledged: true }) }
watch([q, store, warehouse, state, source, risk], () => { offset.value = 0; void loadList() })
watch(offset, () => void loadList())
onMounted(async () => {
  try {
    options.value = await request<V2Options>('/s01/v2/options')
    storage = 'xuheng.s01.v2.' + options.value.principalRef.tenantId + '.' + options.value.principalRef.principalId
    let saved: { batchId?: string; singleId?: string; pending?: PendingV2 } = {}
    try { saved = JSON.parse(sessionStorage.getItem(storage) || '{}') } catch { /* authoritative history remains available */ }
    pending.value = saved.pending || null; await loadHistory(); await loadSingleHistory()
    if (saved.batchId) { await openBatch(saved.batchId); if (saved.singleId) await openSingle(saved.singleId) }
  } catch (e) { fail(e) }
})
onUnmounted(() => { stop(); detailEpoch++; listEpoch++ })
</script>
<template>
  <section class="v2-workbench" aria-label="S01 V2 补货工作台">
    <div class="page-head"><div><div class="eyebrow">S01 / REPLENISHMENT V2</div><h1>全量补货工作台</h1><p class="subtitle">先检查全部授权商品，再按需深入分析与人工请购。</p></div><button class="button primary" :disabled="busy || !!pending || !options" @click="startAll">分析全部 SKU</button></div>
    <Notice v-if="error" title="操作未完成" tone="danger" :alert="true">{{ error }}</Notice>
    <Notice v-if="pending" title="原命令结果待确认" tone="warning">{{ pending.displayHint || '批量任务' }} · {{ pending.createdAt }}。请求可能已受理；沿用原内容和幂等键核对。<button class="button" :disabled="busy" @click="send(pending!)">使用原命令核对</button></Notice>
    <Notice v-if="single && !single.report" title="单品分析任务" :tone="single.task.state === 'FAILED' ? 'danger' : 'info'"><StatusBadge :value="single.task.state" /><p>{{ single.task.errorCode ? issueLabel(single.task.errorCode) : '正在重新获取最新事实；模型仅在本次主动分析中按需调用。' }}</p></Notice>
    <div class="hero-overview"><div><div class="hero-status"><span class="status-dot" />人工触发 · 全授权范围</div><h2>来源透明，数量由人确认</h2><p class="muted">批量只读，不调用 AI、不创建采购。规则数据不足时显示 ERP 参考建议；采购提交权限与分析范围分开。</p></div><span class="status-badge">教学租户 {{ options?.sourceTenant || '—' }}</span></div>
    <Panel v-if="progress" title="本次批量检查" note="独立 Worker · 已完成结果持续保存"><template #action><div class="button-row"><button class="button small" @click="poll(epoch)">刷新状态</button><button v-if="!terminal(progress.task.state)" class="button danger" :disabled="busy || !!pending" @click="command('cancel', `/s01/v2/batches/${batchId}/cancel`, { expectedRevision: progress!.task.revision })">取消批量任务</button><button v-else class="button" :disabled="busy || !!pending" @click="command('batch', `/s01/v2/batches/${batchId}/retry`, {})">重新检查全部 SKU</button></div></template>
      <div class="section-head"><StatusBadge :value="progress.task.state" /><span class="mono wrap">{{ progress.task.taskRef.taskId }}</span></div>
      <p v-if="!summary?.scopeObjectCount" class="micro-note">正在枚举 ERP 店铺、仓库和商品；尚未形成完整目录，当前不能宣称发现总数。</p>
      <progress v-if="summary?.scopeObjectCount" :value="summary.processedCount" :max="summary.scopeObjectCount" class="v2-progress" :aria-label="`已处理 ${summary.processedCount} / ${summary.scopeObjectCount}`" />
      <div v-if="summary" class="metrics v2-metrics"><div v-for="[label, value] in [[progress.statisticsVersion && progress.statisticsVersion !== 'v2-counts-v2' ? '旧口径商品标识' : '发现 SKU', summary.discoveredSkuCount], ['店仓分析对象', summary.scopeObjectCount], ['规则建议', summary.ruleCalculated], ['ERP 参考建议', summary.erpReference], ['无需补货', summary.noReplenishment], ['无法分析 / 待核实', summary.unanalyzable], ['失败', summary.failed], ['未完成', summary.unfinished]]" :key="String(label)" class="metric"><div class="metric-label">{{ label }}</div><div class="metric-value">{{ value }}</div></div></div>
      <p v-if="summary" class="micro-note">处理 {{ summary.processedCount }}/{{ summary.scopeObjectCount }} · 可分析数据覆盖率 {{ (summary.coverage * 100).toFixed(1) }}% · 批量模型调用 {{ summary.modelCalls }} · 业务写入 {{ summary.businessMutations }}</p>
      <Notice v-if="progress.enumerationComplete === false" title="SKU 枚举不完整" tone="danger">当前结果只覆盖已成功读取的对象，不能视为全部授权 SKU。请核对失败域、请求预算或分页后重新检查。</Notice>
      <Notice v-if="Object.values(progress.sourceLimits || {}).some(x => !x.complete)" title="部分业务事实读取不完整" tone="warning">{{ Object.entries(progress.sourceLimits || {}).filter(([, x]) => !x.complete).map(([name, x]) => name + '：' + (x.error || '分页未完成')).join('；') }}。已发布部分结果，不代表全部业务条件通过。</Notice>
      <Notice v-if="progress.task.errorCode" title="任务未完成" tone="warning">{{ progress.task.errorCode }}。已保存结果保留，未处理对象不视为无需补货。</Notice>
      <p v-if="note" role="status">{{ note }}</p>
    </Panel>
    <Panel title="风险与补货检查结果" note="规则风险 / ERP 源风险 / 优先级待核实分别排序，不伪造统一分数">
      <div class="filters"><label class="field">SKU / 商品搜索<input v-model="q" type="search" placeholder="搜索全部本次结果"></label><label class="field">店铺<select v-model="store"><option value="">全部店铺</option><option v-for="s in listing?.stores" :key="s[0]" :value="s[0]">{{ s[1] || '归属待核实' }}</option></select></label><label class="field">仓库<select v-model="warehouse"><option value="">全部仓库</option><option v-for="w in listing?.warehouses" :key="w[0]" :value="w[0]">{{ w[1] || '归属待核实' }}</option></select></label><label class="field">来源<select v-model="source"><option value="">全部来源</option><option v-for="s in ['RULE_CALCULATED', 'REFERENCE_ONLY', 'UNVERIFIED', 'UNAVAILABLE']" :key="s" :value="s">{{ sourceLabel(s) }}</option></select></label><label class="field">分析状态<select v-model="state"><option value="">全部状态</option><option v-for="s in ['ANALYZED', 'ERP_REFERENCE', 'NO_REPLENISHMENT', 'NEEDS_REVIEW', 'UNANALYZABLE', 'FAILED', 'PENDING']" :key="s" :value="s">{{ stateLabel(s) }}</option></select></label><label class="field">风险口径<select v-model="risk"><option value="">全部风险组</option><option value="RULE_CONFIRMED">规则核验风险</option><option value="ERP_SOURCE">ERP 源风险</option><option value="UNVERIFIED">优先级待核实</option></select></label></div>
      <p class="micro-note">共 {{ listing?.total || 0 }} 个符合条件的店仓对象；同 SKU 的不同店仓分开展示。</p>
      <div class="table-scroll"><table><thead><tr><th>商品 / SKU</th><th>店铺 / 仓库</th><th>来源 / 状态</th><th>可用库存</th><th>建议数量</th><th>风险依据</th><th>操作</th></tr></thead><tbody><tr v-for="item in listing?.items" :key="item.entityKey"><td>{{ item.name }}<small class="mono v2-secondary">{{ item.sku }}</small></td><td>{{ item.storeName || '店铺待核实' }}<small class="v2-secondary">{{ item.warehouseName || '仓库待核实' }}</small></td><td><span class="status-badge">{{ sourceLabel(item.sourceGrade) }}</span><small class="v2-secondary">{{ stateLabel(item.analysisState) }}</small></td><td class="numeric">{{ shown(item.inventory?.available) }} {{ unitLabel(item.unit) }}</td><td class="numeric">{{ shown(item.quantity) }}<small v-if="!item.quantity && item.sourceQuantity === 0" class="v2-secondary">ERP 为 0，原因待核实</small></td><td>{{ item.riskGroup === 'NO_REPLENISHMENT' ? '规则核验无需补货' : item.riskGroup === 'RULE_CONFIRMED' ? '规则核验' : item.riskGroup === 'ERP_SOURCE' ? 'ERP 源紧急度：' + (item.sourceUrgency || '未知') : '优先级待核实' }}<small class="v2-secondary">{{ item.riskDate || '缺货日期未知' }}</small></td><td><button class="button small" @click="openItem(item)">查看详情</button></td></tr></tbody></table></div>
      <div v-if="!listing?.items.length" class="empty compact">{{ batchId ? '当前没有匹配结果；任务可能仍在枚举，也可清空筛选查看。' : '点击“分析全部 SKU”开始真实只读检查，或打开历史批次。' }}</div>
      <div class="button-row"><button class="button small" :disabled="offset === 0" @click="offset = Math.max(0, offset - 50)">上一页</button><span class="micro-note">第 {{ Math.floor(offset / 50) + 1 }} 页 / 每页 50</span><button class="button small" :disabled="offset + 50 >= (listing?.total || 0)" @click="offset += 50">下一页</button></div>
    </Panel>
    <Panel v-if="current" :title="current.name + ' · ' + current.sku" note="打开详情不会调用模型"><template #action><button class="button primary" :disabled="busy || !!pending || !selected?.identityVerified || (!!single && !terminal(single.task.state))" @click="newSingle">新建单品分析</button></template>
      <dl class="metadata"><dt>店铺 / 仓库</dt><dd>{{ current.storeName || '未确认' }} / {{ current.warehouseName || '未确认' }}</dd><dt>分析来源</dt><dd>{{ sourceLabel(current.sourceGrade) }} · {{ stateLabel(current.analysisState) }}</dd><dt>当前可用 / 建议数量</dt><dd>{{ shown(current.inventory?.available) }} / {{ shown(current.quantity) }} {{ unitLabel(current.unit) }}</dd><dt>来源时点 / 快照</dt><dd class="wrap">{{ current.observedAt || '尚未采集' }} / {{ current.snapshotRef || '尚未形成' }}</dd></dl>
      <Notice v-if="current.sourceGrade === 'REFERENCE_ONLY'" title="ERP 参考建议" tone="warning">该补货数量来自 ERP 现有建议记录，部分计算依据未验证。请核对采购条件及已有采购后人工确认。</Notice>
      <Notice v-if="!current.quantity" title="未形成正数量补货依据" tone="warning">ERP 的 0、空集合或接口失败都不自动表示无需补货，请结合事实核实。</Notice>
      <p v-if="current.identityIssues.length">归属问题：{{ current.identityIssues.map(issueLabel).join('；') }}</p><p v-if="current.ruleFailureCodes?.length" class="micro-note">规则通道未通过：{{ current.ruleFailureCodes.map(issueLabel).join('；') }}</p>
      <Panel title="采购条件与已有正式采购" note="待审 / 草稿不作为额外阻断"><dl class="metadata"><dt>MOQ / 整箱倍数</dt><dd>{{ shown(current.constraints?.moq) }} / {{ shown(current.constraints?.orderMultiple) }} {{ unitLabel(current.unit) }}</dd><dt>报价 / 币种</dt><dd>{{ shown(current.constraints?.unitPrice) }} {{ current.constraints?.currency || '币种未确认' }} / {{ unitLabel(current.unit) }}</dd><dt>供应商 / 有效报价</dt><dd>{{ current.constraints?.supplierName || '未确认' }} / {{ current.constraints?.quoteNo || '未确认' }}</dd><dt>报价有效期 / 最低金额</dt><dd>{{ current.constraints?.quoteValidFrom || '未知' }}—{{ current.constraints?.quoteValidTo || '未知' }} / {{ shown(current.constraints?.minimumAmount) }} {{ current.constraints?.currency || '' }}</dd></dl><div class="table-scroll"><table><thead><tr><th>正式单据</th><th>状态</th><th>采购 / 已收 / 待收</th><th>计划到货 / 可售日期</th></tr></thead><tbody><tr v-for="po in current.formalPurchases" :key="po.erpId"><td>{{ po.erpNumber }} / {{ po.erpId }}</td><td>{{ po.status }}<small class="v2-secondary">{{ po.warehouseName || '采购仓待核实' }} · {{ po.warehouseMatch === false ? '其他仓，未计入供给' : '可售日期未核验' }}</small></td><td>{{ shown(po.orderedQuantity) }} / {{ shown(po.receivedQuantity) }} / {{ shown(po.unreceivedQuantity) }}</td><td>{{ po.plannedArrival || '未知' }} / {{ po.sellableDate || 'UNKNOWN，未抵扣' }}</td></tr></tbody></table></div><p v-if="!current.formalPurchases?.length" class="micro-note">本次未取得相关正式采购；完整性和范围限制仍以下方证据为准。</p></Panel>
      <Notice title="仍需核实的事项" tone="warning">{{ current.uncertainties.map(issueLabel).join('；') || '请核对来源和当前采购条件。' }}。来源可信度与采购执行资格分别判断；未知项不冒称已验证。</Notice>
      <Panel v-if="current.ruleResult" title="规则计算与销量依据" note="复用 B01 / B02"><p>最近 {{ current.ruleResult.forecast.observationDays }} 个完整业务日：{{ current.ruleResult.forecast.totalSales }} 件；日均 {{ current.ruleResult.forecast.averageDailyDemand }}。窗口 {{ current.ruleResult.forecast.windowStart }}—{{ current.ruleResult.forecast.windowEnd }}。</p><div class="table-scroll"><table><thead><tr><th>业务日</th><th>已核对销量</th></tr></thead><tbody><tr v-for="d in current.ruleResult.forecast.dailySales" :key="d.day"><td>{{ d.day }}</td><td>{{ d.quantity }} 件</td></tr></tbody></table></div></Panel>
      <Panel title="单品 AI 深度分析" note="仅主动新建时调用；批量和查看详情不调用"><p v-if="!single">点击“新建单品分析”重新获取最新事实并按需解释。{{ options?.singleAIEnabled ? '' : '当前模型未启用，规则结果仍可使用。' }}</p><template v-else><StatusBadge :value="single.task.state" /><p v-if="!single.report">{{ single.task.errorCode || '正在重新采集与分析…' }}</p><template v-else><p>{{ single.report.analysisReport.ai.status === 'AVAILABLE' ? 'AI 解释已生成，最终决定仍由人工做出。' : single.report.analysisReport.ai.status === 'NOT_ATTEMPTED' ? '本次未调用模型，已有事实和规则结果保留。' : 'AI 解释未能生成，已有事实和规则结果保留。' }}</p><div v-for="(items, section) in single.report.analysisReport.ai.explanation || {}" :key="section"><h3>{{ ({ recommendationReasons: '建议依据', keyEvidence: '关键事实', majorRisks: '风险提醒', humanConfirmations: '人工确认' } as Record<string, string>)[section] || section }}</h3><ul><li v-for="(item, i) in items" :key="i">{{ item.text }}<small class="micro-note"> · {{ item.supportRefs.join('、') }}</small></li></ul></div><p class="micro-note">Token {{ shown(single.report.analysisReport.ai.usage?.totalTokens) }} · 费用状态 {{ single.report.analysisReport.ai.costStatus || '尚未调用' }}。AI 失败保留当前分析事实。</p></template></template></Panel>
      <Panel title="人工确认与 ERP 请购" note="只创建并提交申请，待 ERP 领导审批"><Notice v-if="!single?.report" title="先新建单品分析">请先读取本 SKU 的最新事实和采购条件，再确认最终数量。</Notice><Notice v-else-if="!canSubmit" title="当前不可提交请购" tone="warning">{{ current.procurementEligibility?.hardBlocks.map(issueLabel).join('；') || '当前范围没有采购提交授权或教学写入未启用' }}。REFERENCE_ONLY 本身不构成拒绝条件。</Notice>
        <Notice v-if="requisition" :title="requisition.state === 'SUBMITTED' ? '已提交 ERP，待领导审批' : '请购状态：' + requisition.state" :tone="requisition.state === 'SUBMITTED' ? 'info' : 'warning'"><dl class="metadata"><dt>真实 ERP ID / 单号</dt><dd>{{ requisition.erpId || '尚未确认' }} / {{ requisition.erpNumber || '尚未确认' }}</dd><dt>ERP 状态 / 独立回读时间</dt><dd>{{ requisition.erpStatus || '未知' }} / {{ requisition.verifiedAt || '尚未确认' }}</dd><dt>原建议 / 人工最终量</dt><dd>{{ requisition.aiQuantity }} / {{ requisition.finalQuantity }} 件</dd><dt>调整原因</dt><dd>{{ requisition.adjustmentReason || '原样确认' }}</dd></dl><p v-if="requisition.errorCode">{{ requisition.errorCode }}</p><button v-if="!['SUBMITTED', 'BLOCKED'].includes(requisition.state)" class="button" :disabled="busy || !!pending" @click="resumeRequisition">沿原操作核对并继续</button></Notice>
        <p v-if="busy && pending?.kind === 'requisition'" role="status">正在重新核对 ERP 事实并提交申请，请保留页面；网络结果不明时仍沿原操作核对。</p><form v-if="canSubmit && !requisition" @submit.prevent="submit"><label class="field">最终采购数量 / 件<input v-model.number="quantity" type="number" min="1" max="100000" step="1" required :disabled="busy || !!pending"></label><label class="field">调整原因（修改数量时必填）<textarea v-model="reason" maxlength="1000" :disabled="busy || !!pending" /></label><p v-if="validation" class="micro-note">{{ validation }}</p><label><input v-model="acknowledged" type="checkbox" :disabled="busy || !!pending"> 我理解建议来源及未验证事项，已核对已有采购和必要约束，确认最终数量用于销售备货；不将此确认视为 ERP 领导审批。</label><button class="button primary" :disabled="busy || !!pending || !!validation || !acknowledged">确认并提交 ERP 请购</button></form><button v-if="single?.report && options?.canSubmit" class="button small" :disabled="busy" @click="readRequisition">查询已保存请购结果</button>
      </Panel>
      <button class="button small" @click="evidence = !evidence">{{ evidence ? '收起' : '查看' }}事实证据与未知事项</button><pre v-if="evidence" class="evidence-json">{{ JSON.stringify({ snapshot: current.snapshotRef, manifest: current.snapshotManifest, inventory: current.inventory, suggestion: current.sourceSuggestion, sourceSuggestions: current.sourceSuggestions, suggestionCount: current.sourceSuggestionCount, quality: current.ruleFailureCodes, constraints: current.constraints, uncertainties: current.uncertainties }, null, 2) }}</pre>
    </Panel>
    <Panel title="批量任务历史" note="当前授权集合 · 每页 20"><div class="table-scroll"><table><thead><tr><th>任务</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="t in history" :key="t.taskRef.taskId"><td class="mono wrap">{{ t.taskRef.taskId }}</td><td><StatusBadge :value="t.state" /></td><td><button class="button small" @click="openBatch(t.taskRef.taskId)">打开批次</button></td></tr></tbody></table></div><div class="button-row"><button class="button small" @click="loadHistory()">最新历史</button><button class="button small" :disabled="!historyCursor" @click="loadHistory(historyCursor!)">更早一页</button></div></Panel>
    <Panel v-if="singleHistory.length" title="单品分析历史" note="最近 20 条"><div class="table-scroll"><table><thead><tr><th>SKU / 来源</th><th>任务</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="t in singleHistory" :key="t.taskRef.taskId"><td>{{ t.sku || '分析未完成' }} / {{ sourceLabel(t.sourceGrade || 'UNAVAILABLE') }}</td><td class="mono wrap">{{ t.taskRef.taskId }}</td><td><StatusBadge :value="t.state" /></td><td><button class="button small" @click="openSingle(t.taskRef.taskId)">查看单品历史</button></td></tr></tbody></table></div></Panel>
  </section>
</template>
<style scoped>
.v2-workbench { display:grid; gap:20px }.v2-workbench>.page-head { margin-bottom:0 }.v2-metrics { grid-template-columns:repeat(4,minmax(0,1fr));margin:16px 0 }.v2-progress { width:100%;height:10px;accent-color:#126b65;margin-top:16px }.v2-secondary{display:block;margin-top:4px;color:#5c6b79;font-size:11px}.v2-workbench .table-scroll{overflow:auto}.v2-workbench table{min-width:740px;width:100%}.v2-workbench .numeric{text-align:right;white-space:nowrap}.v2-workbench form{display:grid;gap:12px}.v2-workbench progress+div .metric-value{font-size:24px}@media(max-width:640px){.v2-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.v2-workbench .page-head{display:block}.v2-workbench .page-head>.button{margin-top:14px}}
</style>
<style scoped>.v2-workbench,.v2-workbench>section{min-width:0}</style>
