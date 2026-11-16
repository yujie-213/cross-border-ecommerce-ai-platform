<script setup lang="ts">
import { computed, ref } from 'vue'
import ModelUsage from '../components/ModelUsage.vue'
import type { Asset } from './api'
import { adviceReason, storeLabel } from './presentation'
const props=defineProps<{asset:Asset; busy:boolean; modelEnabled:boolean; draft:string; message:string; attachments:string; reason:string}>()
const emit=defineEmits<{
  'update:draft':[value:string]; 'update:message':[value:string]; 'update:attachments':[value:string]; 'update:reason':[value:string];
  generate:[]; evidence:[]; append:[]; save:[decision:string]; link:[lineId:string,reason:string]; investigate:[]; history:[]
}>()
const body=computed(()=>props.asset.body), advice=computed(()=>body.value.advice?.at(-1))
const candidates=computed(()=>body.value.evidence?.identityCandidates || [])
const line=ref(''),linkReason=ref(''),moreActions=ref(false)
const currentAdvice=computed(()=>advice.value?.ai.status==='AVAILABLE' && advice.value.caseRevision===props.asset.revision)
const date=(v:any)=>v?new Date(v).toLocaleString('zh-CN',{hour12:false}):'待核实'
const factNames:Record<string,string>={TICKET:'问题标题',PAYMENT:'付款',SHIPMENT:'发货',WAREHOUSE:'发货仓库',payment_status:'付款状态',fulfillment_status:'履约状态',refund_status:'退款状态',order:'订单',shipment:'发货',return:'退货'}
function factText(f:any) {
  const v=f.value ?? f.record
  if(f.text)return f.text
  if(typeof v==='string')return v
  if(f.domain==='PAYMENT')return `${v.amount} ${v.currency || ''} · ${date(v.at)}`
  if(f.domain==='WAREHOUSE')return '仓库 '+v.warehouseId
  if(f.domain==='SHIPMENT')return v.map((s:any)=>'已发货 · '+date(s.at)).join('；')
  if(v?.type==='shipment')return `实际发货 ${v.quantity} 件 · ${date(v.at)}`
  if(v?.type==='return')return `${({draft:'退货草稿',requested:'申请退货',authorized:'已授权退货',received:'已实收',refunded:'已退款',cancelled:'已取消'} as Record<string,string>)[v.stage] || v.stage} ${v.quantity} 件`
  if(v?.type==='order')return v.paid?'已记录付款':'付款待核实'
  return '查看来源明细'
}
</script>
<template>
  <div class="case-layout">
    <div class="case-main">
      <section class="panel conversation"><div class="section-title"><h2>客户会话</h2><button class="b-text-button" @click="emit('history')">处理历史</button></div>
        <article v-for="(m,i) in body.messages" :key="i" class="message"><div class="message-meta"><b>{{m.role==='CUSTOMER'?'客户':'客服'}}</b><time>{{date(m.at)}}</time><small v-if="m.source==='CLAIM'">客服补录</small></div><p>{{m.text}}</p></article>
        <div v-if="!body.messages.length" class="empty-message"><p>{{body.title}}</p><button class="b-text-button" @click="($refs.messageEntry as HTMLDetailsElement).open=true">补充客户消息</button></div>
        <details ref="messageEntry"><summary>补充客户消息</summary><form @submit.prevent="emit('append')"><label>客户消息<textarea :value="message" @input="emit('update:message',($event.target as HTMLTextAreaElement).value)" required maxlength="6000"></textarea></label><label>附件线索（可选）<input :value="attachments" @input="emit('update:attachments',($event.target as HTMLInputElement).value)"></label><button class="button small" :disabled="busy || !message.trim()">保存消息</button></form></details>
      </section>
      <section class="panel composer"><div class="section-title"><h2>回复客户</h2><button class="button" :disabled="busy || !body.identity || !body.evidence || !modelEnabled" @click="emit('generate')">{{busy?'正在处理…':advice?'重新生成 AI 回复':'生成 AI 回复'}}</button></div>
        <p v-if="!modelEnabled" class="muted">AI 暂不可用，请先人工填写回复。</p>
        <p v-else-if="advice && advice.ai.status!=='AVAILABLE'" class="reply-status" role="status">{{adviceReason(advice.ai.reason)}}</p>
        <p v-if="advice?.ai.status==='AVAILABLE' && !currentAdvice && asset.state!=='HANDLED'" class="reply-status">资料已有更新，请重新生成后再采纳 AI 回复；也可保存人工回复。</p>
        <label class="reply-label">回复稿<textarea :value="draft" @input="emit('update:draft',($event.target as HTMLTextAreaElement).value)" maxlength="6000" placeholder="填写回复，或生成 AI 回复后核对修改。"></textarea></label>
        <div class="compose-actions"><button class="button primary" :disabled="busy || !draft.trim()" @click="emit('save','SAVE')">保存处理</button><button class="b-text-button" @click="moreActions=!moreActions">更多处理</button><span>保存为内部处理记录</span></div>
        <div v-if="moreActions" class="more-actions"><label>处理原因<input :value="reason" @input="emit('update:reason',($event.target as HTMLInputElement).value)" maxlength="1000"></label><div class="button-row"><button class="button small" :disabled="busy || !reason.trim() || !draft.trim()" @click="emit('save','ESCALATE')">升级处理</button><button class="button small" :disabled="busy || !reason.trim() || !draft.trim()" @click="emit('save','RETURN')">退回修改</button><button class="button small" :disabled="busy" @click="emit('investigate')">发起商品调查</button></div></div>
        <button v-if="currentAdvice && draft!==advice.ai.output.replyDraft" class="b-text-button" @click="emit('update:draft',advice.ai.output.replyDraft)">使用新草稿</button><details v-if="advice"><summary>AI 原稿与依据</summary><p v-if="advice.ai.output">{{advice.ai.output.replyDraft}}</p><article v-for="p in advice.policies" :key="p.policyId+p.sectionId"><b>{{p.title}}</b><p>{{p.text}}</p></article><p v-for="g in advice.ai.output?.missingEvidence || []" :key="g">{{g}}</p><ModelUsage :ai="advice.ai" /></details>
        <details v-if="advice?.feedbackAI?.analysis.status==='AVAILABLE'"><summary>客户反馈分析</summary><p v-for="p in advice.feedbackAI.analysis.output.hypotheses" :key="p">{{p}}</p><p v-for="p in advice.feedbackAI.analysis.output.nextSteps" :key="p">{{p}}</p></details>
      </section>
    </div>
    <aside class="panel order-summary"><div class="section-title"><h2>订单摘要</h2><button class="b-text-button" :disabled="busy" @click="emit('evidence')">更新</button></div>
      <template v-if="body.identity"><h3>{{body.identity.name}}</h3><p class="sku">{{body.identity.sku}}</p><dl><div><dt>订单</dt><dd>{{body.identity.orderId==='UNKNOWN'?'待核实':body.identity.orderNumber || body.identity.orderId}}</dd></div><div><dt>店铺</dt><dd>{{storeLabel(body.erpStoreName)}}</dd></div><div v-if="body.businessDate"><dt>问题日期</dt><dd>{{date(body.businessDate)}}</dd></div></dl></template>
      <p v-else class="reply-status">请选择本次问题对应的商品。</p>
      <form v-if="!body.identity && candidates.length" @submit.prevent="emit('link',line,'')"><label>选择本订单受影响商品<select v-model="line" required><option value="">请选择</option><option v-for="c in candidates" :key="c.lineId" :value="c.lineId">{{c.name}} · {{c.sku}}</option></select></label><button class="button small" :disabled="busy || !line">确认商品</button></form>
      <div class="order-facts"><article v-for="f in (body.evidence?.facts || []).filter((f:any)=>!['TICKET','feedback','WAREHOUSE','CUSTOMER_STATEMENT'].includes(f.domain))" :key="f.id"><small>{{factNames[f.domain] || '业务记录'}}</small><p>{{factText(f)}}</p></article></div>
      <details v-if="body.evidence?.missing?.length"><summary>待核实事项（{{body.evidence.missing.length}}）</summary><p v-for="m in body.evidence.missing" :key="m" class="muted">{{m}}</p></details>
      <button class="button small investigate" :disabled="busy || !body.evidence?.facts?.length" @click="emit('investigate')">发起商品调查</button>
      <details v-if="body.identity && candidates.length"><summary>更正关联商品</summary><form @submit.prevent="emit('link',line,linkReason)"><label>本单商品<select v-model="line" required><option value="">请选择</option><option v-for="c in candidates" :key="c.lineId" :value="c.lineId">{{c.name}}</option></select></label><label>更正原因<input v-model="linkReason" required></label><button class="button small" :disabled="busy">保存更正</button></form></details>
      <details><summary>来源与内部编号</summary><p>ERP 工单 {{body.erpTicketId || body.erpVoiceId || '—'}}</p><p>店铺 {{body.erpStoreName || '独立教学资料'}}</p><p>明细 {{body.identity?.lineId || '—'}} · 仓库 {{body.identity?.warehouseId || '—'}}</p><p v-for="f in body.evidence?.facts || []" :key="f.id">{{f.sourceRef}} · {{date(f.observedAt)}}</p><p v-for="(m,i) in body.messages" :key="i">{{m.source==='CLAIM'?'人工补录':m.source==='SIMULATED'?'仿真客户陈述补充':'ERP读取'}} {{m.sourceRef || m.attachmentRefs?.join('、')}}</p></details>
    </aside>
  </div>
</template>
<style scoped>
label{display:grid;gap:8px;margin:14px 0;font-size:13px;color:#425f70}input,select,textarea{display:block;border:1px solid #cbd7de;border-radius:6px;width:100%;min-width:0;padding:11px 12px;font:inherit;color:#243b4b;background:#fff;box-sizing:border-box}textarea{resize:vertical;min-height:100px}textarea:focus,input:focus,select:focus{outline:2px solid #a7d0c8;outline-offset:1px}.b-text-button{border:0;background:none;padding:5px 0;color:#176f69;font:inherit;font-size:13px;cursor:pointer}.b-text-button:disabled{opacity:.5;cursor:default}details{margin:18px 0}summary{font-size:12px;color:#37666c;cursor:pointer}.muted{font-size:13px;color:#71818b}.button-row{display:flex;gap:10px;flex-wrap:wrap}
.case-layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:22px;align-items:start}.case-main{min-width:0;display:grid;gap:20px}.conversation,.composer,.order-summary{padding:24px}.section-title{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:20px}.section-title h2{margin:0;font-size:17px}.message{margin:0 0 18px;padding:16px 18px;background:#f5f8f9;border-radius:8px;overflow-wrap:anywhere}.message-meta{display:flex;align-items:center;gap:12px;font-size:12px;color:#71818b}.message-meta b{color:#36525f}.message p{white-space:pre-wrap;font-size:14px;line-height:1.85;margin:10px 0 0}.reply-label textarea{min-height:200px;line-height:1.8}.compose-actions{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.compose-actions span{font-size:12px;color:#71818b}.more-actions{border-top:1px solid #e4ebef;margin-top:18px}.reply-status{font-size:13px;color:#88652e}.sku{font-size:12px!important;color:#71818b;overflow-wrap:anywhere}.order-summary h3{margin:0;font-size:15px;line-height:1.7}.order-summary dl{font-size:12px;margin:18px 0}.order-summary dl>div{display:flex;justify-content:space-between;gap:16px;padding:10px 0}.order-summary dt{color:#71818b;flex-shrink:0}.order-summary dd{margin:0;text-align:right;overflow-wrap:anywhere}.order-facts{border-block:1px solid #e3e9ed;padding:8px 0}.order-facts article{padding:6px 0}.order-facts p{font-size:13px;margin:4px 0}.investigate{width:100%;margin:12px 0}.empty-message p{line-height:1.8}.order-summary details p{font-size:12px;overflow-wrap:anywhere}@media(max-width:1000px){.case-layout{grid-template-columns:minmax(0,1fr) 270px;gap:16px}.conversation,.composer,.order-summary{padding:18px}}@media(max-width:760px){.case-layout{grid-template-columns:1fr}.order-summary{grid-row:2}.reply-label textarea{min-height:180px}}
</style>
