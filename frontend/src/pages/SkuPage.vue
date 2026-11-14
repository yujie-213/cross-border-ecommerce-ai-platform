<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { route, navigate, back } from '../router'
import { init, openBatch, openItem, openSingle, createSingle, readRequisition, submitRequisition, replayPending, pendingFor, state, stageOf, STAGE_LABEL, dash, fmt, latestBatchId } from '../s01'
import { quantityError, issueLabel } from '../api/v2'
import { displayDate, resultDate, quantityOf, shortageOf, nextAction, confidenceNote } from '../business'
import AiAnalysis from '../components/AiAnalysis.vue'
import BusinessEvidence from '../components/BusinessEvidence.vue'
const quantity = ref(0), reason = ref(''), acknowledged = ref(false)
const item = computed(() => state.item)
const running = computed(() => state.singleLoading || state.singlePolling || ['QUEUED','RUNNING'].includes(state.singleTask?.state || ''))
const scopes = computed(() => {
  if (!item.value) return []
  const all = item.value.relatedScopes?.length ? item.value.relatedScopes : [item.value]
  return all.map(row => row.entityKey === item.value!.entityKey ? item.value! : row)
})
const single = computed(() => state.singleReport)
const history = computed(() => state.singleHistory.filter(row => row.entityKey === item.value?.entityKey))
const recentAI = computed(() => history.value.find(row => row.aiStatus === 'AVAILABLE' && row.taskRef.taskId !== state.singleId))
const constraints = computed(() => item.value?.constraints)
const blocks = computed(() => item.value?.procurementEligibility?.hardBlocks || [])
const requisition = computed(() => state.requisition)
const pending = computed(() => pendingFor(state.singleId))
const pendingBusiness = computed(() => state.pending?.entityKey === item.value?.entityKey ? state.pending : null)
const canSubmit = computed(() => !!single.value && item.value?.procurementEligibility?.eligible === true && item.value.procurementEligibility.scopeAuthorized === true && state.options?.canSubmit === true && !requisition.value && !pendingBusiness.value && state.requisitionReadState === 'ready' && !state.requisitionLoading)
const validation = computed(() => item.value ? quantityError(item.value, quantity.value, reason.value) : '数量不可用')
const purchaseReason = computed(() => requisition.value ? '本商品已有本平台请购，请核对原单' : blocks.value.length ? issueLabel(blocks.value[0]) : !state.options?.canSubmit ? '本次体验为只读，采购提交未开放' : !single.value ? '先更新当前店仓分析，再确认采购条件' : '核对数量与已有采购，确认后提交 ERP 审批')
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
  quantity.value = state.item?.quantity || 0; reason.value = ''; acknowledged.value = false
}
onMounted(load)
watch(() => [route.value.path,route.value.query.batch,route.value.query.single], () => { if (route.value.path.startsWith('/sku/')) void load() })
watch(() => item.value?.quantity, value => { quantity.value = value || 0; acknowledged.value = false })
async function submit() { if (canSubmit.value && !validation.value && acknowledged.value && !state.busy) await submitRequisition(quantity.value,reason.value.trim()) }
</script>
<template>
  <div class="page procurement-detail">
    <a class="back-link" href="#/suggestions" @click.prevent="back('/suggestions')">← 返回商品列表</a>
    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>
    <div v-if="!item" class="panel empty-state"><h2>{{ state.itemLoading ? '正在读取商品…' : '暂时找不到这份商品分析' }}</h2><p>请选择已登记商品，或返回商品列表重新打开。</p><a class="button" href="#/suggestions">返回商品列表</a></div>
    <template v-else>
      <header class="product-header"><div><span class="eyebrow">智能补货 / 商品分析</span><h1>{{ item.name || item.sku }}</h1><p><span class="mono">{{ item.sku }}</span><span> · {{ scopes.length }} 个店仓 · 更新于 {{ resultDate(item.observedAt) }}</span></p></div><div class="product-actions"><button class="button primary" :disabled="running || state.busy || !item.identityVerified" @click="generate(false)">{{ running && state.singleMode === 'analysis' ? '正在更新分析…' : '更新补货分析' }}</button><small>{{ item.identityVerified ? '读取最新业务数据，不调用 AI' : '商品店仓归属待核实，暂不能分析' }}</small></div></header>
      <section class="warehouse-section" aria-label="各仓补货判断"><div class="section-title"><h2>先看各仓，需要补多少</h2><span class="small muted">选择店仓，查看对应分析与建议</span></div><div class="warehouse-options"><button v-for="row in scopes" :key="row.entityKey" class="warehouse-choice" :class="{selected:row.entityKey === item.entityKey}" :aria-pressed="row.entityKey === item.entityKey" @click="row.entityKey !== item.entityKey && navigate('/sku/'+row.entityKey,{batch:state.batchId})"><span class="warehouse-top"><b>{{ row.warehouseName || '仓库待核实' }}</b><span class="chip" :class="stageOf(row)">{{ STAGE_LABEL[stageOf(row)] }}</span></span><small>{{ row.storeName }}</small><div class="warehouse-quantity"><span>参考补充库存</span><strong>{{ dash(quantityOf(row)) }}<small>件</small></strong></div><span class="warehouse-foot">库存 {{ dash(row.inventory?.available) }} 件 <em>{{ shortageOf(row) ? displayDate(shortageOf(row))+' 起有缺货风险' : row.decision?.status === 'NO_REPLENISHMENT' ? '规划期内库存充足' : '缺货日期待核实' }}</em></span></button></div></section>
      <div class="decision-layout"><div class="decision-main">
        <div class="decision-caption"><span class="chip" :class="stageOf(item)">{{ STAGE_LABEL[stageOf(item)] }}</span><strong>{{ nextAction(item) }}</strong><span>{{ item.warehouseName }}</span></div>
        <AiAnalysis :ai="single?.analysisReport.ai || null" :task-state="state.singleTask?.state" :loading="running" :error="state.singleError" :error-code="state.singleTask?.errorCode" :enabled="state.options?.singleAIEnabled" :analysis-only="state.singleMode === 'analysis'" :context="item.sku+' · '+item.warehouseName+' · '+resultDate(item.observedAt)" @generate="generate(true)" @refresh="state.singleId && openSingle(state.singleId,state.singleMode)" />
        <p v-if="recentAI && !running && single?.analysisReport.ai.status !== 'AVAILABLE'" class="advice-history-link">本仓已有一份 AI 建议：<a :href="'#/sku/'+item.entityKey+'?batch='+state.batchId+'&single='+recentAI.taskRef.taskId">查看 {{ resultDate(recentAI.observedAt) }} 的建议 →</a><span>基于当时数据，点击后切换至该次分析</span></p>
        <BusinessEvidence :item="item" />
        <details class="panel secondary-details"><summary>数据可信度与分析假设 <span>{{ confidenceNote(item) }}</span></summary><div class="details-content"><p v-for="line in item.decision?.assumptions || []" :key="line">{{ line }}</p><p v-for="hint in item.recoveryHints || []" :key="hint.code">{{ hint.message }}</p><small>数据快照 {{ item.snapshotRef || '未形成' }} · 当前只分析已登记店仓</small></div></details>
        <details class="panel secondary-details"><summary>查看该店仓的历史分析 <span>{{ history.length }} 次</span></summary><div class="details-content"><a v-for="row in history" :key="row.taskRef.taskId" class="history-entry" :href="'#/sku/'+item.entityKey+'?batch='+state.batchId+'&single='+row.taskRef.taskId"><span>{{ resultDate(row.observedAt || row.createdAt) }}</span><b>{{ row.state === 'SUCCEEDED' ? '查看分析结果' : row.state === 'FAILED' ? '分析失败，查看原因' : '处理中' }}</b></a><p v-if="!history.length">暂无该店仓的单品分析。</p></div></details>
      </div><aside class="purchase-rail" aria-label="人工采购决策"><section class="panel purchase-panel"><span class="eyebrow">最后一步 · 人工决策</span><h2>采购前再核实</h2><div class="quantity-bridge"><div><span>参考补充库存</span><strong>{{ dash(quantityOf(item)) }}<small>件</small></strong></div><span>→</span><div><span>满足采购约束的候选</span><strong>{{ dash(item.decision?.purchasableQuantity ?? item.quantity) }}<small v-if="item.quantity != null">件</small></strong></div></div><p class="purchase-hint">参考补充量是库存需求；采购候选还需满足有效报价、MOQ 与整箱。</p><div class="purchase-state" :class="{blocked:!canSubmit}"><b>{{ canSubmit ? '可继续人工确认' : '提交前仍需核实' }}</b><p>{{ purchaseReason }}</p></div><details v-if="blocks.length > 1"><summary>查看全部待办条件（{{ blocks.length }}）</summary><ul><li v-for="code in blocks" :key="code">{{ issueLabel(code) }}</li></ul></details><dl class="purchase-facts"><dt>供应商</dt><dd>{{ constraints?.supplierName || '未确认' }}</dd><dt>MOQ / 整箱</dt><dd>{{ dash(constraints?.moq) }} / {{ dash(constraints?.orderMultiple) }} 件</dd><dt>采购单价</dt><dd>{{ dash(constraints?.unitPrice) }} {{ constraints?.currency }}</dd><dt>规划交期</dt><dd>{{ item.decision?.leadDays != null ? item.decision.leadDays+' 天' : '未确认' }}</dd></dl>
        <div v-if="pending" class="banner danger"><b>原请购结果未确认</b><p>请使用原命令核对，不要重复提交。</p><button class="button" :disabled="state.busy" @click="replayPending">使用原命令核对</button></div><div v-else-if="pendingBusiness" class="banner warning">同商品已有操作待确认，请返回原分析核对。</div><div v-else-if="requisition" class="saved-purchase"><b>{{ requisition.erpNumber || '已有请购记录' }}</b><p>{{ requisition.erpStatus || '状态待核对' }}</p><a href="#/requisitions">查看 ERP 最新状态 →</a></div>
        <template v-else><label class="field">最终采购数量<input v-model.number="quantity" aria-label="最终采购数量" type="number" :min="constraints?.moq || 1" :step="constraints?.orderMultiple || 1" :disabled="!canSubmit || state.busy" /></label><label v-if="item.quantity !== null && quantity !== item.quantity" class="field">调整原因<input v-model="reason" aria-label="调整原因" maxlength="1000" :disabled="!canSubmit || state.busy" /></label><label class="check purchase-check"><input v-model="acknowledged" type="checkbox" :disabled="!canSubmit || state.busy">已核对当前店仓、数量、已有采购和来源限制</label><p v-if="canSubmit && validation" class="small danger">{{ validation }}</p><button class="button primary full-button" :disabled="!canSubmit || !!validation || !acknowledged || state.busy" @click="submit">{{ state.busy ? '正在提交…' : '人工确认并提交请购' }}</button><p class="small muted">提交后进入 ERP 审批，不代表已下单或已到货。</p></template>
        <details class="existing-purchases"><summary>已有采购（分析时快照，{{ (item.formalPurchases?.length || 0)+(item.pendingPurchases?.length || 0) }} 条）</summary><div v-for="po in [...(item.pendingPurchases || []),...(item.formalPurchases || [])]" :key="po.erpId"><b>{{ po.erpNumber }}</b><span>{{ po.status }}</span></div><a href="#/requisitions">进入请购管理核对最新状态 →</a></details>
      </section></aside></div>
      <p v-if="state.note" role="status" class="banner plain">{{ state.note }}</p>
    </template>
  </div>
</template>
