<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { route, navigate, back } from '../router'
import { init, openBatch, openItem, openSingle, createSingle, readRequisition, submitRequisition, replayPending, pendingFor, state, stageOf, STAGE_LABEL, dash, fmt, latestBatchId } from '../s01'
import { quantityError, issueLabel, type PlanPreview } from '../api/v2'
import { request, ApiError, errorText } from '../api/client'
import { displayDate, resultDate, quantityOf, shortageOf, nextAction, confidenceNote, suggestedPurchaseQuantity, purchaseStatusTone } from '../business'
import AiAnalysis from '../components/AiAnalysis.vue'
import BusinessEvidence from '../components/BusinessEvidence.vue'
const quantity = ref(0), reason = ref(''), acknowledged = ref(false)
const arrivalDate = ref(''), dateEditing = ref(false), mounted = ref(false)
const plan = ref<PlanPreview | null>(null), planLoading = ref(false), planError = ref('')
let planTimer: ReturnType<typeof setTimeout> | undefined, planController: AbortController | undefined, planSequence = 0
const item = computed(() => state.item)
const running = computed(() => state.singleLoading || state.singlePolling || ['QUEUED','RUNNING'].includes(state.singleTask?.state || ''))
const scopes = computed(() => {
  if (!item.value) return []
  const all = item.value.relatedScopes?.length ? item.value.relatedScopes : [item.value]
  return all.map(row => row.entityKey === item.value!.entityKey ? item.value! : row)
})
const baselineSeries = computed(() => item.value?.decision?.baseline?.series || [])
const dateMin = computed(() => baselineSeries.value[0]?.day || '')
const dateMax = computed(() => baselineSeries.value.at(-1)?.day || '')
const defaultArrival = computed(() => {
  const candidate = (item.value?.ruleResult?.supplyDemand as { candidates?: { availableDate: string }[] } | undefined)?.candidates?.[0]
  if (candidate) return candidate.availableDate
  const lead = item.value?.decision?.leadDays
  if (lead == null || !dateMin.value) return ''
  const day = new Date(dateMin.value + 'T00:00:00Z')
  day.setUTCDate(day.getUTCDate() + Math.max(1,lead) - 1)
  return day.toISOString().slice(0,10)
})
const assumedArrival = computed(() => !defaultArrival.value || arrivalDate.value !== defaultArrival.value)
const sourceTaskId = computed(() => state.singleReport ? state.singleId : state.batchId)
const single = computed(() => state.singleReport)
const history = computed(() => state.singleHistory.filter(row => row.entityKey === item.value?.entityKey))
const recentAI = computed(() => history.value.find(row => row.aiStatus === 'AVAILABLE' && row.taskRef.taskId !== state.singleId))
const constraints = computed(() => item.value?.constraints)
const suggestedQuantity = computed(() => item.value ? suggestedPurchaseQuantity(item.value) : null)
const adjusted = computed(() => suggestedQuantity.value !== null && Number(quantity.value) !== suggestedQuantity.value)
const blocks = computed(() => item.value?.procurementEligibility?.hardBlocks || [])
const requisition = computed(() => state.requisition)
const pending = computed(() => pendingFor(state.singleId))
const pendingBusiness = computed(() => state.pending?.entityKey === item.value?.entityKey ? state.pending : null)
const canSubmit = computed(() => !!single.value && item.value?.procurementEligibility?.eligible === true && item.value.procurementEligibility.scopeAuthorized === true && state.options?.canSubmit === true && !requisition.value && !pendingBusiness.value && state.requisitionReadState === 'ready' && !state.requisitionLoading)
const validation = computed(() => item.value ? quantityError(item.value, quantity.value, reason.value) : '数量不可用')
const purchaseReason = computed(() => requisition.value ? '本商品已有本平台请购，请核对原单' : blocks.value.length ? issueLabel(blocks.value[0]) : !state.options?.canSubmit ? '采购提交未启用' : !single.value ? '先更新当前店仓分析，再确认采购条件' : '核对数量与已有采购')
async function generate(ai = false) {
  const entity = item.value?.entityKey
  const id = await createSingle(ai)
  if (id && entity && route.value.path === '/sku/' + entity && state.itemKey === entity) navigate('/sku/' + entity, { batch:state.batchId,single:id })
}
async function load() {
  await init()
  const key = route.value.segments[1], batch = route.value.query.batch || state.batchId || latestBatchId(), selected = route.value.query.single
  if (batch && batch !== state.batchId) await openBatch(batch)
  if (key && (key !== state.itemKey || (selected || '') !== state.singleId || !state.item)) await openItem(key, selected)
  quantity.value = state.item ? suggestedPurchaseQuantity(state.item) ?? 0 : 0; reason.value = ''; acknowledged.value = false; arrivalDate.value = defaultArrival.value; dateEditing.value = false
}
onMounted(async () => { await load(); mounted.value = true })
onBeforeUnmount(() => { clearTimeout(planTimer); planController?.abort(); planSequence++ })
watch(() => [route.value.path,route.value.query.batch,route.value.query.single], () => { if (route.value.path.startsWith('/sku/')) void load() })
watch(() => [item.value?.entityKey,item.value?.observedAt,suggestedQuantity.value], () => { quantity.value = suggestedQuantity.value ?? 0; reason.value = ''; acknowledged.value = false; arrivalDate.value = defaultArrival.value; dateEditing.value = false })
watch(quantity, () => { acknowledged.value = false; if (!adjusted.value) reason.value = '' })
watch(arrivalDate, () => { acknowledged.value = false })
function refreshPlan() {
  clearTimeout(planTimer); planController?.abort(); const sequence = ++planSequence
  plan.value = null; planError.value = ''; planLoading.value = false
  const current = item.value, source = sourceTaskId.value, count = Number(quantity.value), arrival = arrivalDate.value
  if (!mounted.value || running.value || !current || !source || !baselineSeries.value.length || route.value.path !== '/sku/' + current.entityKey) return
  if (!Number.isInteger(count) || count < 1 || count > 100000) { planError.value = '请输入 1 至 100000 的整数数量'; return }
  if (!arrival) return
  if (arrival < dateMin.value || arrival > dateMax.value) { planError.value = '到货日期须在 ' + dateMin.value.slice(5) + ' 至 ' + dateMax.value.slice(5) + ' 之间'; return }
  planLoading.value = true
  planTimer = setTimeout(async () => {
    const controller = new AbortController(); planController = controller
    try {
      const result = await request<PlanPreview>('/s01/v2/batches/' + encodeURIComponent(source) + '/items/' + current.entityKey + '/plan-preview', { method:'POST', body:JSON.stringify({quantity:count,availableDate:arrival}) }, controller.signal)
      if (sequence !== planSequence || controller.signal.aborted) return
      if (result.entityKey !== current.entityKey || result.sourceTaskId !== source || result.observedAt !== current.observedAt || result.quantity !== count || result.availableDate !== arrival) throw new Error('PLAN_CONTEXT_MISMATCH')
      plan.value = result
    } catch (error) {
      if (sequence !== planSequence || controller.signal.aborted) return
      planError.value = error instanceof ApiError ? issueLabel(error.code) : error instanceof Error && error.message === 'PLAN_CONTEXT_MISMATCH' ? '计划结果与当前商品不一致，请重试' : errorText(error)
    } finally { if (sequence === planSequence) planLoading.value = false }
  },180)
}
watch(() => [mounted.value,running.value,item.value?.entityKey,item.value?.observedAt,sourceTaskId.value,quantity.value,arrivalDate.value,route.value.path], refreshPlan)
function restoreArrival() { arrivalDate.value = defaultArrival.value; dateEditing.value = false }
async function submit() { if (canSubmit.value && !validation.value && acknowledged.value && !state.busy) await submitRequisition(quantity.value,reason.value.trim()) }
</script>
<template>
  <div class="page procurement-detail">
    <a class="back-link" href="#/suggestions" @click.prevent="back('/suggestions')">← 返回商品列表</a>
    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>
    <div v-if="!item" class="panel empty-state"><h2>{{ state.itemLoading ? '正在读取商品…' : '暂时找不到这份商品分析' }}</h2><p>请选择已登记商品，或返回商品列表重新打开。</p><a class="button" href="#/suggestions">返回商品列表</a></div>
    <template v-else>
      <header class="product-header"><div><h1>{{ item.name || item.sku }}</h1><p><span class="mono">{{ item.sku }}</span><span> · {{ scopes.length }} 个店仓 · 更新于 {{ resultDate(item.observedAt) }}</span></p></div><div class="product-actions"><button class="button primary" :disabled="running || state.busy || !item.identityVerified" @click="generate(true)">{{ running ? '正在更新分析与 AI…' : '更新补货分析' }}</button><small v-if="!item.identityVerified">商品店仓归属待核实，暂不能分析</small></div></header>
      <section class="warehouse-section" aria-label="各仓补货判断"><div class="section-title"><h2>各仓补货建议</h2></div><div class="warehouse-options"><button v-for="row in scopes" :key="row.entityKey" class="warehouse-choice" :class="{selected:row.entityKey === item.entityKey}" :aria-pressed="row.entityKey === item.entityKey" @click="row.entityKey !== item.entityKey && navigate('/sku/'+row.entityKey,{batch:state.batchId})"><span class="warehouse-top"><b>{{ row.warehouseName || '仓库待核实' }}</b><span class="chip" :class="stageOf(row)">{{ STAGE_LABEL[stageOf(row)] }}</span></span><small>{{ row.storeName }}</small><div class="warehouse-quantity"><span>参考补充库存</span><strong>{{ dash(quantityOf(row)) }}<small>件</small></strong></div><span class="warehouse-foot">库存 {{ dash(row.inventory?.available) }} 件 <em>{{ shortageOf(row) ? displayDate(shortageOf(row))+' 起有缺货风险' : row.decision?.status === 'NO_REPLENISHMENT' ? '规划期内库存充足' : '缺货日期待核实' }}</em></span></button></div></section>
      <div class="decision-layout"><div class="decision-main">
        <div class="decision-caption"><span class="chip" :class="stageOf(item)">{{ STAGE_LABEL[stageOf(item)] }}</span><strong>{{ nextAction(item) }}</strong><span>{{ item.warehouseName }}</span></div>
        <AiAnalysis :ai="single?.analysisReport.ai || null" :task-state="state.singleTask?.state" :loading="running" :error="state.singleError" :error-code="state.singleTask?.errorCode" :enabled="state.options?.singleAIEnabled" :analysis-only="state.singleMode === 'analysis'" :context="item.sku+' · '+item.warehouseName+' · '+resultDate(item.observedAt)" @generate="generate(true)" @refresh="state.singleId && openSingle(state.singleId,state.singleMode)" />
        <p v-if="recentAI && !running && single?.analysisReport.ai.status !== 'AVAILABLE'" class="advice-history-link">历史 AI 建议：<a :href="'#/sku/'+item.entityKey+'?batch='+state.batchId+'&single='+recentAI.taskRef.taskId">查看 {{ resultDate(recentAI.observedAt) }} 的建议 →</a></p>
        <BusinessEvidence :item="item" :plan="plan" :plan-loading="planLoading" :plan-error="planError" :assumed-arrival="assumedArrival" :arrival-date="arrivalDate" @retry="refreshPlan" />
        <details class="panel secondary-details"><summary>数据可信度与分析假设 <span>{{ confidenceNote(item) }}</span></summary><div class="details-content"><p v-for="line in item.decision?.assumptions || []" :key="line">{{ line }}</p><p v-for="hint in item.recoveryHints || []" :key="hint.code">{{ hint.message }}</p><small>数据快照 {{ item.snapshotRef || '未形成' }}</small></div></details>
        <details class="panel secondary-details"><summary>查看该店仓的历史分析 <span>{{ history.length }} 次</span></summary><div class="details-content"><a v-for="row in history" :key="row.taskRef.taskId" class="history-entry" :href="'#/sku/'+item.entityKey+'?batch='+state.batchId+'&single='+row.taskRef.taskId"><span>{{ resultDate(row.observedAt || row.createdAt) }}</span><b>{{ row.state === 'SUCCEEDED' ? '查看分析结果' : row.state === 'FAILED' ? '分析失败，查看原因' : '处理中' }}</b></a><p v-if="!history.length">暂无该店仓的单品分析。</p></div></details>
      </div><aside class="purchase-rail" aria-label="人工采购决策"><section class="panel purchase-panel"><h2>采购确认</h2><div class="quantity-bridge"><div><span>参考补充</span><strong>{{ dash(quantityOf(item)) }}<small>件</small></strong></div><span>→</span><div><span>采购候选</span><strong>{{ dash(item.decision?.purchasableQuantity ?? item.quantity) }}<small v-if="item.quantity != null">件</small></strong></div></div><div class="purchase-state" :class="{blocked:!canSubmit}"><b>{{ canSubmit ? '待人工确认' : '采购条件待补齐' }}</b><p>{{ purchaseReason }}</p></div><details v-if="blocks.length > 1"><summary>查看全部待办条件（{{ blocks.length }}）</summary><ul><li v-for="code in blocks" :key="code">{{ issueLabel(code) }}</li></ul></details><dl class="purchase-facts"><dt>供应商</dt><dd>{{ constraints?.supplierName || '未确认' }}</dd><dt>MOQ / 整箱</dt><dd>{{ dash(constraints?.moq) }} / {{ dash(constraints?.orderMultiple) }} 件</dd><dt>采购单价</dt><dd>{{ dash(constraints?.unitPrice) }} {{ constraints?.currency }}</dd><dt>规划交期</dt><dd>{{ item.decision?.leadDays != null ? item.decision.leadDays+' 天' : '未确认' }}</dd></dl>
        <div v-if="pending" class="banner danger"><b>原请购结果未确认</b><p>请使用原命令核对，不要重复提交。</p><button class="button" :disabled="state.busy" @click="replayPending">使用原命令核对</button></div><div v-else-if="pendingBusiness" class="banner warning">同商品已有操作待确认，请返回原分析核对。</div><div v-else-if="requisition" class="saved-purchase"><b>{{ requisition.erpNumber || '已有请购记录' }}</b><p><span class="chip" :class="purchaseStatusTone(requisition.erpStatus)">{{ requisition.erpStatus || '状态待核对' }}</span></p><a href="#/requisitions">查看 ERP 最新状态 →</a></div>
        <template v-else><div class="purchase-plan-fields"><label class="field">拟采购数量<input v-model.number="quantity" aria-label="最终采购数量" type="number" min="1" step="1" max="100000" :disabled="state.busy || running" /></label><div class="field arrival-field"><span class="arrival-label">{{ assumedArrival ? '假设到货日' : '预计到货日' }}<button v-if="defaultArrival && dateEditing" class="text-action" @click="restoreArrival">恢复</button><button v-else-if="defaultArrival" class="text-action" @click="dateEditing = true">调整</button></span><input v-if="dateEditing || !defaultArrival" v-model="arrivalDate" aria-label="假设到货日" type="date" :min="dateMin" :max="dateMax" :disabled="state.busy || running || !baselineSeries.length" /><div v-else class="arrival-value">{{ displayDate(arrivalDate) }}</div></div></div><p v-if="planError" class="plan-field-error" role="alert">{{ planError }}</p><label v-if="adjusted" class="field adjustment-reason" aria-live="polite">调整原因（必填）<input v-model="reason" aria-label="调整原因" maxlength="1000" :disabled="state.busy || running" /></label><label class="check purchase-check"><input v-model="acknowledged" type="checkbox" :disabled="state.busy || running">已核对当前店仓、数量、已有采购和来源限制</label><p v-if="canSubmit && validation" class="small danger">{{ validation }}</p><button class="button primary full-button" :disabled="!canSubmit || !!validation || !acknowledged || state.busy" @click="submit">{{ state.busy ? '正在提交…' : '确认并提交' }}</button></template>
        <details class="existing-purchases"><summary>已有采购（分析时快照，{{ (item.formalPurchases?.length || 0)+(item.pendingPurchases?.length || 0) }} 条）</summary><div v-for="po in [...(item.pendingPurchases || []),...(item.formalPurchases || [])]" :key="po.erpId"><b>{{ po.erpNumber }}</b><span class="chip" :class="purchaseStatusTone(po.status)">{{ po.status }}</span></div><a href="#/requisitions">进入请购管理核对最新状态 →</a></details>
      </section></aside></div>
      <p v-if="state.note" role="status" class="banner plain">{{ state.note }}</p>
    </template>
  </div>
</template>
