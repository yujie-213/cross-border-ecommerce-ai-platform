<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { ApiError, errorText, request } from '../api/client'
import type { Report, Requisition } from '../api/types'
import Panel from './Panel.vue'
import Notice from './Notice.vue'
const props = defineProps<{ report: Report; enabled: boolean }>()
const emit = defineEmits<{ denied: [] }>()
const quantity = ref(0), reason = ref(''), acknowledged = ref(false), busy = ref(false), error = ref('')
const result = ref<Requisition | null>(null)
type Pending = { key: string; quantity: number; reason: string }
const pending = ref<Pending | null>(null)
const sourceQuantity = computed(() => Number(props.report.dataReport.supplyDemand.candidates[0]?.quantity || 0))
const eligible = computed(() => props.enabled && props.report.dataReport.existingPurchases?.policyVersion === 's01-approved-purchases-v1' && sourceQuantity.value > 0 && props.report.completeness !== 'BLOCKED')
const storageKey = () => 'xuheng.s01.requisition.' + props.report.reportRef.tenantId + '.' + props.report.reportRef.reportId
const endpoint = () => '/analysis-tasks/' + encodeURIComponent(props.report.taskRef.taskId) + '/requisition'
const validation = computed(() => {
  const c = props.report.dataReport.forecast?.constraints
  if (!c || !Number.isSafeInteger(quantity.value) || quantity.value < Number(c.moq) || quantity.value > 100000 || quantity.value % Number(c.orderMultiple)) return '数量必须满足 MOQ、整数件和整箱倍数。'
  if (quantity.value !== sourceQuantity.value && !reason.value.trim()) return '调整数量时请填写原因。'
  return ''
})
let epoch = 0
function clearPending() { pending.value = null; sessionStorage.removeItem(storageKey()) }
function failed(e: unknown) {
  error.value = errorText(e)
  if (e instanceof ApiError && [401, 403].includes(e.status)) { result.value = null; emit('denied') }
}
async function refresh() {
  if (!props.enabled || busy.value) return
  const current = epoch
  busy.value = true; error.value = ''
  try {
    const value = await request<Requisition | null>(endpoint())
    if (current !== epoch) return
    result.value = value
    if (value && ['SUBMITTED', 'BLOCKED'].includes(value.state)) clearPending()
  } catch (e) { if (current === epoch) failed(e) }
  finally { if (current === epoch) busy.value = false }
}
async function submit() {
  if (!eligible.value || busy.value || (!pending.value && (validation.value || !acknowledged.value))) return
  if (!pending.value) {
    pending.value = { key: crypto.randomUUID(), quantity: quantity.value, reason: reason.value }
    sessionStorage.setItem(storageKey(), JSON.stringify(pending.value))
  }
  const command = pending.value, current = epoch
  sessionStorage.setItem(storageKey(), JSON.stringify(command))
  busy.value = true; error.value = ''
  try {
    const value = await request<Requisition>(endpoint(), { method: 'POST', headers: { 'Idempotency-Key': command.key }, body: JSON.stringify({ finalQuantity: command.quantity, adjustmentReason: command.reason }) })
    if (current !== epoch) return
    result.value = value
    if (['SUBMITTED', 'BLOCKED'].includes(value.state)) clearPending()
  } catch (e) { if (current === epoch) failed(e) }
  finally { if (current === epoch) busy.value = false }
}
function resume() {
  if (!result.value) return
  pending.value = { key: crypto.randomUUID(), quantity: result.value.finalQuantity, reason: result.value.adjustmentReason }
  void submit()
}
watch(() => [props.report.reportRef.tenantId, props.report.reportRef.reportId, props.enabled], () => {
  epoch++; busy.value = false; error.value = ''; result.value = null; pending.value = null
  quantity.value = sourceQuantity.value; reason.value = ''; acknowledged.value = false
  if (!props.enabled) return
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey()) || 'null')
    if (saved && typeof saved.key === 'string' && Number.isSafeInteger(saved.quantity) && typeof saved.reason === 'string') pending.value = saved
  } catch { /* GET still recovers the server operation after corrupt local metadata. */ }
  void refresh()
}, { immediate: true })
onUnmounted(() => { epoch++ })
</script>
<template>
  <Panel title="人工确认与 ERP 请购" note="销售备货 · 教学申请">
    <Notice v-if="!enabled" title="当前未开放请购提交">需要服务端启用教学请购及本范围的提交权限。历史报告仍可查看。</Notice>
    <template v-else>
      <p>中台确认后创建采购申请并提交 ERP 审批。ERP 领导审批、正式下单与收货另行处理。</p>
      <Notice v-if="error" tone="danger" title="操作结果待核对" :alert="true">{{ error }}</Notice>
      <Notice v-if="result" :tone="result.state === 'SUBMITTED' ? 'info' : 'warning'" :title="result.state === 'SUBMITTED' ? '已提交 ERP，待领导审批' : '请购处理状态：' + result.state">
        <dl class="metadata"><dt>ERP 真实单据 ID</dt><dd>{{ result.erpId || '尚未确认' }}</dd><dt>ERP 单号 / 状态</dt><dd>{{ result.erpNumber || '尚未确认' }} / {{ result.erpStatus || '尚未确认' }}</dd><dt>AI 原数量 / 人工最终数量</dt><dd>{{ result.aiQuantity }} / {{ result.finalQuantity }} 件</dd><dt>调整原因</dt><dd>{{ result.adjustmentReason || '原样确认' }}</dd><dt>操作记录</dt><dd class="wrap">{{ result.operationId }}</dd><dt>ERP 查询路径</dt><dd class="wrap">{{ result.queryPath || '尚未生成可查询 ID' }}</dd></dl>
        <p class="micro-note">单据状态来自提交后的独立 ERP 回读，核验时间 {{ result.verifiedAt || '尚未确认' }}；查询按钮读取已保存结果。</p>
        <p v-if="result.errorCode">{{ result.errorCode }}。请保留原操作核对；BLOCKED 时核实原因后重新分析。</p>
      </Notice>
      <form v-if="eligible && !result && !pending" @submit.prevent="submit">
        <p>AI 原建议 {{ sourceQuantity }} 件；原始计算结果将保留。</p>
        <label class="field">确认采购数量 / 件<input v-model.number="quantity" type="number" min="1" max="100000" step="1" required :disabled="busy"></label>
        <label class="field">调整原因（修改数量时必填）<textarea v-model="reason" maxlength="1000" :disabled="busy" /></label>
        <p v-if="validation" class="micro-note">{{ validation }}</p>
        <label><input v-model="acknowledged" type="checkbox" :disabled="busy"> 我已复核数量和教学限制，确认用于销售备货；可售日期及未确认供应未抵扣。</label>
        <button class="button primary" :disabled="busy || !!validation || !acknowledged">{{ busy ? '正在核验并提交…' : '确认并提交 ERP 请购' }}</button>
      </form>
      <p v-if="!eligible && !result" class="micro-note">本报告没有可提交的当前补货候选，请先重新分析。</p>
      <Notice v-if="pending" tone="warning" title="原提交待确认">最终 {{ pending.quantity }} 件。将沿用原幂等操作，不创建新的申请。<button class="button" :disabled="busy" @click="submit">使用原操作核对 / 继续提交</button></Notice>
      <button v-if="result && !['SUBMITTED', 'BLOCKED'].includes(result.state) && !pending" class="button" :disabled="busy" @click="resume">核对原记录并继续</button>
      <button class="button small" :disabled="busy" @click="refresh">查询已保存的请购结果</button>
    </template>
  </Panel>
</template>
