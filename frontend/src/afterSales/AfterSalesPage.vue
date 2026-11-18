<script setup lang="ts">
import CaseWorkspace from './CaseWorkspace.vue'
import ServiceDesk from './ServiceDesk.vue'
import ReturnAnalysis from './ReturnAnalysis.vue'
import { adviceResult, reviewData, storeLabel } from './presentation'
import Modal from '../components/Modal.vue'
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { route, navigate, href } from '../router'
import { request, errorText, ApiError } from '../api/client'
import { workspace, workbench as all, details, loadIndex, remember, tasks, taskKey, taskRunning, followTask, restoreTasks, pending, opening, sources, sessionEpoch, loadPage, resultPage } from './session'
import { get, post, stateNames, effectiveState, type Asset, type Workbench, type Workspace, type Index } from './api'

const current = ref<Asset>(), busy = ref(false), loading = ref(false), error = ref(''), note = ref('')
const currentTasks=computed(()=>Object.values(tasks).filter(t=>t.assetId===current.value?.id || t.investigationId && t.investigationId===investigationId.value).sort((a,b)=>(a.startedAt || 0)-(b.startedAt || 0)))
const caseBusy=computed(()=>busy.value || !!opening[route.value.query.record || ''] || currentTasks.value.some(taskRunning))
const section = computed(() => route.value.segments[1] || 'workbench')
const tabs = [{ key:'workbench',name:'售后工作台' },{key:'cases',name:'售后处理'},{key:'experience',name:'退货与商品分析'},{key:'risks',name:'调查与质量风险'},{key:'materials',name:'知识与政策'}]
const starterScope=ref(route.value.query.scope || 'TEACHING')
const policySearch=ref(''),policyManage=ref(false),policyCategoryFilter=ref('ALL'),policyStatusFilter=ref('ALL'),selectedPolicy=ref(''),manualEvidence=ref(''),manualEvidenceSource=ref(''),draftCaseId=ref(''),draftBaseline=ref('')
const visiblePolicies=computed(()=>(all.value?.policy.items || []).filter(p=>(policyCategoryFilter.value==='ALL' || p.body.category===policyCategoryFilter.value) && (policyStatusFilter.value==='ALL' || p.state===policyStatusFilter.value) && (!policySearch.value || [p.body.title,...p.body.sections.map((s:any)=>s.text)].some(t=>t.includes(policySearch.value)))))
const title = computed(() => current.value?.kind==='CASE'?'售后处理':section.value==='experience'?'退货与商品分析':tabs.find(t => t.key === section.value)?.name || '售后工作台')
const activeTask=ref<any>(),riskView=ref('CURRENT')
const filteredRisks=computed(()=>scopedRisks.value.filter(a=>riskView.value==='ALL' || riskView.value==='CURRENT' && ['SUSPECTED','CONFIRMED'].includes(effectiveState(a)) || riskView.value==='HISTORY' && !['SUSPECTED','CONFIRMED'].includes(effectiveState(a))))
const scopedCases=computed(()=>assets.value)
const scopedRisks=computed(()=>risks.value)
const scopedInvestigations=computed(()=>all.value?.investigation.items || [])
const investigationOpen=ref(false), riskRegister=ref(false)
const investigationOrigin=ref<Asset>()
const investigationAssist=computed(()=>investigationOrigin.value?.body.investigationAssists?.filter((a:any)=>a.investigationId===activeInvestigation.value?.id).at(-1))
const activeInvestigation=computed(()=>all.value?.investigation.items.find(a=>a.id===investigationId.value))
function showHistory(){const el=document.getElementById('case-history');if(el instanceof HTMLDetailsElement)el.open=true;el?.scrollIntoView({behavior:'smooth'})}

const message=ref(''), humanText=ref(''), reviewReason=ref('')
const investigationText=ref(''), investigationId=ref(''), conclusion=ref('OPEN')
const riskReason=ref(''), limitations=ref('问题原因及影响范围仍待核实'), riskDecisionReason=ref('')
const validUntil=ref(new Date(Date.now()+29*86400000).toISOString())
const riskOptions = ref<{name:string;identity:Record<string,any>}[]>([]), riskOption = ref('')
const backgroundTasks=ref<any[]>([]), policyRevisionText=ref(''), editingPolicy=ref(''), investigationEvidence=ref<any[]>([]), chosenEvidence=ref<string[]>([])
const policyTitle = ref(''), policyText = ref(''), policyCategory = ref('APPAREL'), policyRegion = ref('CN'), policyPlatform = ref('TEACHING'), policyLanguage = ref('zh'), policyTopic = ref('REPLY')
const policyTopics = [
  ['REPLY', '回复与补证'], ['SIZE', '尺码与规格'], ['DESCRIPTION', '描述核实'], ['LOGISTICS', '发货与物流'],
  ['NOT_RECEIVED', '未收到商品'], ['ORDER_CHANGE', '修改或取消订单'], ['PRODUCT_INFO', '商品使用与保养'],
  ['COMPATIBILITY', '商品兼容性'], ['FUNCTION', '商品故障'], ['ITEM_ISSUE', '破损、错发或漏发'],
  ['PAYMENT', '支付、发票与优惠'], ['RETURN', '退换与退款'],
]
const attachments=ref('')
const taskId = ref(''), alive = ref(true)
let sequence = 0
const assets = computed(() => all.value?.case.items || [])
const risks = computed(() => all.value?.risk.items || [])
const returnTo = computed(() => { const value = route.value.query.returnTo; return value?.startsWith('/') && !value.startsWith('//') ? value : '' })
const identityCandidates = computed(() => current.value?.body.evidence?.identityCandidates || [])
const lastAdvice = computed(() => current.value?.body.advice?.at(-1))
function link(page:string,id?:string) { return href('/after-sales/'+page,{id,returnTo:returnTo.value || undefined}) }
function open(page:string,id:string) { navigate('/after-sales/'+page,{id,returnTo:returnTo.value || undefined}) }
function collection() { return section.value }
function status(a:Asset) { return stateNames[effectiveState(a)] || a.state }
function pretty(v:unknown) { return typeof v === 'string' ? v : JSON.stringify(v,null,2) }
const stages:Record<string,string>={draft:'草稿',requested:'申请',authorized:'曾授权',authorizedValid:'有效授权',received:'实收',refunded:'实际退款',cancelled:'取消'}
const aiReason=(reason:string)=>({INVALID_OUTPUT:'模型结果未通过证据校验，可先继续人工调查',B_MODEL_AUTHORIZATION_REQUIRED:'模型尚未启用',B_MODEL_ALLOWANCE_UNAVAILABLE:'本次模型额度不足，已保留原有事实',TIMEOUT:'模型响应超时，正在保留原始依据'} as Record<string,string>)[reason] || '本次模型结果不可用，已有事实保留'
const factNames:Record<string,string>={TICKET:'工单标题（不是完整会话）',ORDER:'关联订单',PAYMENT:'已核付款记录',SHIPMENT:'已核发货记录',feedback:'客户反馈原文',payment_status:'订单付款状态',fulfillment_status:'订单履约状态',refund_status:'订单退款状态'}
function factText(f:any) {
  const r=f.value ?? f.record ?? f
  if(r.type==='shipment')return `实际发货 ${r.quantity} 件，时间 ${formatDate(r.at)}`
  if(r.type==='return')return `${stages[r.stage] || r.stage} ${r.quantity} 件，时间 ${formatDate(r.at)}`+(r.amount!=null?`；退款 ${r.amount} ${r.currency}`:'')
  if(r.type==='order')return `订单${r.paid===true?'已记录支付':'支付状态待核实'}；业务时间 ${formatDate(r.paidAt)}`
  if(r.type==='feedback')return r.text
  if(f.text)return f.text
  if(f.domain==='PAYMENT')return `已记录支付 ${r.amount} ${r.currency || ''}，时间 ${formatDate(r.at)}`
  if(typeof r==='string')return r
  if(Array.isArray(r))return r.map(x=>`时间 ${formatDate(x.at)}；明细见证据来源`).join('；')
  return Object.entries(r).filter(([,v])=>typeof v!=='object').map(([k,v])=>`${factNames[k] || k}：${v}`).join('；')
}
watch(investigationOrigin,origin=>{
  riskOptions.value=[];riskOption.value=''
  if(origin?.body.identity){const p=origin.body.identity;const common={sourceTenant:origin.scope.sourceTenant,productId:p.productId,sku:p.sku,storeId:p.storeId};riskOptions.value=[...(p.warehouseId && p.warehouseId!=='UNKNOWN'?[{name:p.name+' · 本仓',identity:{...common,warehouseMode:'EXPLICIT_IDS',warehouseIds:[p.warehouseId]}}]:[]),{name:p.name+' · 本店所有仓',identity:{...common,warehouseMode:'ALL_STORE_WAREHOUSES',warehouseIds:[]}}]}
})
function setCurrent(a:Asset){
  current.value=a
  if(a.kind==='CASE' && draftCaseId.value!==a.id){draftCaseId.value=a.id;humanText.value=a.body.reviews.at(-1)?.text || (a.body.advice.at(-1)?.ai.status==='AVAILABLE'?a.body.advice.at(-1).ai.output.replyDraft:'');draftBaseline.value=a.body.reviews.at(-1)?.text || ''}
  const confirmation=a.body.confirmation
  if(confirmation && ['PREPARED','SENDING','PENDING'].includes(confirmation.status)){pending.value={path:'/cases/'+a.id+'/reviews',key:confirmation.key};sessionStorage.setItem('b-pending-command',JSON.stringify(pending.value))}
}
function previewSource(key:string){
  const r=sources[key];if(!r)return
  setCurrent({id:'preview:'+key,kind:'CASE',revision:0,state:'OPEN',sourceNature:'TEACHING_ERP_OBSERVED',scope:{},body:{title:r.title,erpStoreName:r.storeName,identity:r.identity,messages:[{role:'CUSTOMER',text:r.text || r.title,at:r.businessDate}],reviews:[],advice:[]}})
}
async function refresh(force=true) {
  const run=++sequence;loading.value=true;error.value=''
  const id=route.value.query.id
  if(id){const cached=details[id] || [...(all.value?.case.items || []),...(all.value?.risk.items || [])].find(a=>a.id===id);if(cached)setCurrent(cached)}
  else if(route.value.query.record)previewSource(route.value.query.record)
  else current.value=undefined
  try {
    await loadIndex(force)
    if(run!==sequence || !alive.value)return
    if(id && ['cases','risks'].includes(section.value)) {
      const a=!force && details[id]?details[id]:!force && current.value?.id===id?current.value:await get<Asset>('/'+collection()+'/'+encodeURIComponent(id))
      if(run!==sequence || !alive.value)return
      remember(a);setCurrent(a)
    }
    if(section.value==='risks' && route.value.query.investigation){
      let inv=all.value?.investigation.items.find(a=>a.id===route.value.query.investigation)
      if(!inv){inv=await get<Asset>('/investigations/'+encodeURIComponent(route.value.query.investigation));if(run!==sequence)return;remember(inv)}
      await chooseInvestigation(inv)
    }
  } catch(e){if(run===sequence)error.value=errorText(e)}
  finally{if(run===sequence)loading.value=false}
}
watch(()=>currentTasks.value.map(t=>t.id+':'+t.state+':'+t.error).join('|'),()=>{
  const finished=currentTasks.value.at(-1);if(!finished)return
  activeTask.value=finished;taskId.value=finished.id
  if(finished.error){note.value='';error.value=finished.error;return}
  if(finished.state!=='SUCCEEDED'){note.value=finished.action==='advice-jobs'?'正在生成 AI 回复…':finished.action==='investigation-jobs'?'正在分析调查证据…':'正在更新订单资料…';return}
  const a=details[finished.assetId];if(!a)return
  if(current.value?.id===a.id){const previous=current.value;setCurrent(a);if(finished.action==='advice-jobs'){
    note.value=adviceResult(a)
    if(a.body.advice.at(-1)?.ai.status==='AVAILABLE'){
      if(!humanText.value || humanText.value===previous.body.advice.at(-1)?.ai.output?.replyDraft)humanText.value=a.body.advice.at(-1).ai.output.replyDraft
      else note.value='AI 回复已生成，当前编辑稿已保留，可查看并使用新草稿。'
    }
  }else note.value=a.body.evidence?.latestUnverified?'订单资料未更新成功，请稍后重试。':'订单资料已更新。'}
  if(finished.action==='investigation-jobs' && finished.investigationId===investigationId.value){investigationOrigin.value=a;note.value=finished.report?.analysisReport?.modelStatus==='AVAILABLE'?'AI 调查分析已生成。':'AI 调查分析未生成，可重试或继续人工调查。'}
},{immediate:true})
async function command<T>(path:string,body:unknown):Promise<T> {
  if(pending.value)throw new Error('PENDING_COMMAND')
  const own=sessionEpoch(),value={path,body,key:crypto.randomUUID()};pending.value=value
  sessionStorage.setItem('b-pending-command',JSON.stringify({path:value.path,key:value.key}))
  try{const result=await post<T>(path,body,value.key);if(own!==sessionEpoch())throw new Error('SESSION_ENDED');if((result as any)?.handlingStatus!=='PENDING'){pending.value=undefined;sessionStorage.removeItem('b-pending-command')}return result}
  catch(e){if(own===sessionEpoch() && e instanceof ApiError){pending.value=undefined;sessionStorage.removeItem('b-pending-command')}throw e}
}
async function perform(action:()=>Promise<void>) {
  if(busy.value)return
  busy.value=true;error.value='';note.value=''
  try{await action()}catch(e){note.value='';error.value=e instanceof Error && !(e instanceof ApiError) && e.message==='PENDING_COMMAND'?'请先核对上一笔结果不确定的操作。':e instanceof Error && !(e instanceof ApiError) && e.message.startsWith('TASK:')?'任务未完成：'+e.message.slice(5)+'，已保留已有事实和记录。':errorText(e)}finally{busy.value=false}
}
async function retry() {if(!pending.value)return;await perform(async()=>{
  const p=pending.value!,result=await request<any>('/commands/'+p.key,{},undefined,60000,'/api/b/v1')
  if(result.result?.handlingStatus!=='PENDING'){pending.value=undefined;sessionStorage.removeItem('b-pending-command')}
  const restored=result.result?.taskRef
  if(restored){
    const match=p.path.match(/^\/cases\/([^/]+)\/(evidence-jobs|advice-jobs|investigation-jobs)$/)
    if(match){const key=taskKey(match[1],match[2]);tasks[key]={id:restored.taskId,assetId:match[1],action:match[2],startedAt:Date.now(),state:'QUEUED',error:''};followTask(key)}
    taskId.value=restored.taskId
  }
  if(route.value.query.record && result.result?.kind==='CASE' && result.result?.id){const saved=await get<Asset>('/cases/'+result.result.id);remember(saved);open('cases',saved.id)}
  await refresh();note.value=result.result?.handlingStatus==='PENDING'?'ERP 保存结果仍待核验。':result.result?.handlingStatus==='REJECTED'?'ERP 未接受本次处理，请更新记录后重新确认。':'处理结果已核对。'
})}
async function saveReply(decision:string){await perform(async()=>{
  const result=await mutate('cases',current.value!,'reviews',reviewData(current.value!,humanText.value,decision,reviewReason.value))
  if(result.handlingStatus==='PENDING'){note.value='ERP 保存结果待核验，请核对处理结果。';return}
  if(result.handlingStatus==='REJECTED'){note.value='ERP 未接受本次处理，请更新记录后重新确认。';return}
  draftBaseline.value=humanText.value;reviewReason.value=''
  note.value=result.state==='HANDLED'?'已确认保存，记录已处理。':'处理记录已保存。'
})}
async function mutate(collection:string,asset:Asset,action:string,data:unknown) {
  const result=await command<any>('/'+collection+'/'+asset.id+'/'+action,{expectedRevision:asset.revision,data});await refresh();return result
}
async function job(asset:Asset,collection:string,action:string,data:any={}) {
  const key=taskKey(asset.id,action,data.investigationId),existing=tasks[key]
  if(taskRunning(existing)){followTask(key);return}
  const accepted=await command<{taskRef:{taskId:string}}>('/'+collection+'/'+asset.id+'/'+action,{expectedRevision:asset.revision,data})
  tasks[key]={id:accepted.taskRef.taskId,assetId:asset.id,action,investigationId:data.investigationId,startedAt:Date.now(),state:'QUEUED',error:''}
  taskId.value=accepted.taskRef.taskId;followTask(key)
}
async function openSource(record:any){
  const erpTicketId=record.kind==='tickets'?record.ticketId:null,erpVoiceId=record.kind==='tickets'?null:record.recordId
  const existing=assets.value.find(a=>a.body.erpStoreName===record.storeName && (erpTicketId?a.body.erpTicketId===erpTicketId:a.body.erpVoiceId===erpVoiceId && a.body.erpVoiceKind===record.kind))
  if(existing){remember(existing);open('cases',existing.id);return}
  const key=[record.storeName,record.kind,erpTicketId || erpVoiceId].join(':')
  sources[key]=record;navigate('/after-sales/cases',{record:key});previewSource(key)
  if(opening[key])return
  opening[key]=true;const own=sessionEpoch()
  try {
    const created=await command<Asset>('/cases',{title:record.title || '客户反馈',message:'',region:'UNKNOWN',platform:'UNKNOWN',language:'zh',erpStoreName:record.storeName,erpTicketId,erpVoiceId,erpVoiceKind:erpVoiceId?record.kind:null})
    const saved=await get<Asset>('/cases/'+created.id)
    if(own!==sessionEpoch())return
    remember(saved)
    if(alive.value && route.value.query.record===key){open('cases',saved.id)}
  }catch(e){if(own===sessionEpoch() && alive.value && route.value.query.record===key)error.value=errorText(e)}
  finally{if(own===sessionEpoch())delete opening[key]}
}
function formatDate(value:any){return value?new Date(value).toLocaleString('zh-CN',{hour12:false}):'未提供'}
function prepareInvestigation(){investigationOpen.value=true;investigationText.value=(lastAdvice.value?.feedbackAI?.analysis.output?.hypotheses || []).join('；')}
async function more(key:keyof Workbench,path:string){await perform(async()=>{const old=all.value?.[key];if(!old?.nextCursor)return;const next=await get<Index>('/'+path+'?limit=100&before='+old.nextCursor);old.items.push(...next.items);old.nextCursor=next.nextCursor})}
async function editPolicy(p:Asset){await perform(()=>mutate('policies',p,'new-version',{policy:{...Object.fromEntries(Object.entries(p.body).filter(([k])=>!k.startsWith('_') && !['publishedBy','publishedAt','publishReason','revocationReason'].includes(k))),sections:[{id:'s1',text:policyRevisionText.value}]}}));editingPolicy.value=''}
const availableEvidence=computed(()=>current.value?.body.evidence?.facts.map((f:any)=>({id:f.id,text:factText(f)})) || [])
async function chooseInvestigation(a:Asset){
  investigationId.value=a.id;conclusion.value='OPEN';investigationText.value='';limitations.value='问题原因及影响范围仍待核实'
  const key='investigation:'+a.id+':'+a.revision
  await loadPage(key,async()=>{const [origin,proof]=await Promise.all([get<Asset>('/cases/'+a.body.origin.id),get<any>('/investigations/'+a.id+'/facts')]);return {origin,proof}})
  if(investigationId.value!==a.id || !alive.value)return
  const result=resultPage(key);if(result.error){error.value=result.error;return}
  investigationOrigin.value=details[a.body.origin.id] || result.data.origin
  investigationEvidence.value=result.data.proof.items.map((f:any)=>({id:f.id,text:factText(f)}));chosenEvidence.value=(a.body.entries.at(-1)?.evidenceRefs || []).filter((id:string)=>investigationEvidence.value.some(f=>f.id===id))
}
async function assistInvestigation(){const origin=details[activeInvestigation.value!.body.origin.id] || await get<Asset>('/cases/'+activeInvestigation.value!.body.origin.id);await job(origin,'cases','investigation-jobs',{investigationId:activeInvestigation.value!.id})}
async function startSourceInvestigation(kind:'return'|'monitor',body:any){
  const key=[kind,body.store,body.returnId || body.sku,body.sku].join(':');if(opening[key])return
  const own=sessionEpoch(),ownRoute=location.hash;opening[key]=true;error.value=''
  try{
    const result=await command<any>(kind==='return'?'/return-cases':'/monitor-cases',body)
    if(own!==sessionEpoch())return
    const origin=await get<Asset>('/cases/'+result.id)
    if(own!==sessionEpoch())return
    const inv=await command<any>('/investigations',{kind:'CASE',id:origin.id,text:origin.body.title,evidenceRefs:(origin.body.evidence?.facts || []).slice(0,100).map((f:any)=>f.id)})
    if(own!==sessionEpoch())return
    remember(origin);await loadIndex(true)
    if(alive.value && location.hash===ownRoute)viewInvestigation(inv.id)
  }catch(e){if(own===sessionEpoch() && alive.value && location.hash===ownRoute)error.value=errorText(e)}
  finally{if(own===sessionEpoch())delete opening[key]}
}
async function addInvestigationEvidence(){await perform(async()=>{await mutate('investigations',activeInvestigation.value!,'evidence',{text:manualEvidence.value,sourceRef:manualEvidenceSource.value});manualEvidence.value='';manualEvidenceSource.value=''})}
async function importPolicyDrafts() {await perform(async()=>{const path='/policy-starters'+(starterScope.value==='AMAZON'?'?region=US&platform=Amazon':'');for(const p of await get<any[]>(path)){if(!all.value?.policy.items.some(a=>a.body.title===p.title && a.body.region===p.region && a.body.platform===p.platform && JSON.stringify(a.body.sections)===JSON.stringify(p.sections)))await command('/policies',p)}await refresh();note.value='政策草稿已准备。'})}
async function createPolicy() {await perform(async()=>{
  await command('/policies',{title:policyTitle.value,category:policyCategory.value,topics:[policyTopic.value],sections:[{id:'s1',text:policyText.value}],region:policyRegion.value,platform:policyPlatform.value,language:policyLanguage.value,
    effectiveFrom:'2026-01-01T00:00:00Z',effectiveUntil:'2027-01-01T00:00:00Z',source:'本机人工录入政策，待人工发布',terms:['CLARIFY','MANUAL_REVIEW']});await refresh();policyTitle.value='';policyText.value=''
})}
async function openNewPolicy(){policyManage.value=true;await nextTick();{const form=document.getElementById('new-policy');if(form instanceof HTMLDetailsElement){form.open=true;form.scrollIntoView({behavior:'smooth',block:'center'})}}}
function viewInvestigation(id:string){navigate('/after-sales/risks',{investigation:id})}
async function investigate(origin:Asset) {await perform(async()=>{const result=await command<Asset>('/investigations',{kind:origin.kind,id:origin.id,text:investigationText.value,evidenceRefs:chosenEvidence.value});investigationText.value='';investigationOpen.value=false;viewInvestigation(result.id);note.value='调查已建立，请核实证据并记录人工结论。'})}

async function createRisk() {await perform(async()=>{const identity=riskOptions.value[Number(riskOption.value)]?.identity;if(!identity)throw new Error('RISK_SCOPE_REQUIRED');const result=await command<Asset>('/investigations/'+investigationId.value+'/confirm-risk',{expectedRevision:activeInvestigation.value!.revision,data:{reason:riskReason.value,limitations:limitations.value,identity,validUntil:validUntil.value}});riskRegister.value=false;investigationId.value='';open('risks',result.id);await refresh()})}
function warnDraft(event:BeforeUnloadEvent){if((humanText.value && humanText.value!==draftBaseline.value) || message.value){event.preventDefault();event.returnValue=''}}
function guardDraft(event:MouseEvent){const anchor=(event.target as Element)?.closest('a');if(anchor && anchor.hash!==location.hash && ((humanText.value && humanText.value!==draftBaseline.value) || message.value) && !confirm('人工处理稿或补充消息尚未保存。确认离开并放弃未保存内容？')){event.preventDefault();event.stopImmediatePropagation()}}
onMounted(()=>{window.addEventListener('beforeunload',warnDraft);document.addEventListener('click',guardDraft,true)})
onBeforeUnmount(()=>{window.removeEventListener('beforeunload',warnDraft);document.removeEventListener('click',guardDraft,true)})
watch(()=>[route.value.query.id,route.value.query.record].join(':'),(id,previous)=>{if(id!==previous){draftCaseId.value='';humanText.value='';reviewReason.value='';message.value='';attachments.value=''}})
onMounted(()=>{restoreTasks();Object.keys(tasks).forEach(followTask);try{const saved=sessionStorage.getItem('b-pending-command');if(saved)pending.value=JSON.parse(saved)}catch{};void refresh(false)})
onBeforeUnmount(()=>{alive.value=false;sequence++})
watch(()=>[route.value.path,route.value.query.id,route.value.query.investigation,route.value.query.record],()=>{investigationOpen.value=false;riskRegister.value=false;investigationId.value='';riskDecisionReason.value='';note.value='';error.value='';void refresh(false)})
</script>

<template>
  <div class="b-page">
    <a v-if="current?.kind==='CASE'" class="back" :href="link('workbench')">← 返回工作台</a>
    <a v-if="returnTo" class="back" :href="'#'+returnTo">← 返回原补货页面</a>
    <header class="page-head"><div><h1>{{title}}</h1></div><button v-if="current?.state!=='HANDLED' && !pending && (current || !['workbench','cases','experience'].includes(section))" class="button small" :disabled="caseBusy || loading || current?.revision===0" @click="current?.kind==='CASE'?perform(()=>job(current!,'cases','evidence-jobs')):refresh()">更新记录</button></header>
    <p v-if="error" class="banner danger" role="alert">{{error}}</p><p v-if="note" class="banner" role="status">{{note}}</p>
    <p v-if="current?.revision===0 && caseBusy" class="banner" role="status">正在准备处理记录…</p><button v-if="current?.revision===0 && !caseBusy && !pending" class="button small" @click="openSource(sources[route.query.record])">重试</button><p v-for="t in currentTasks.filter(t=>t.error && taskRunning(t))" :key="t.id" class="banner warning">任务结果待查询。<button class="button small" @click="followTask(taskKey(t.assetId,t.action,t.investigationId))">继续查询</button></p>
    <p v-if="pending && !busy && !Object.values(opening).some(Boolean)" class="banner warning">保存结果待核验。<button class="button small" @click="retry">核对处理结果</button></p>
    <p v-if="loading && !current && !all" role="status">正在读取当前记录…</p>


    <template v-if="['workbench','cases'].includes(section) && !current && !route.query.id">
      <ServiceDesk v-if="workspace" :workspace="workspace" :cases="scopedCases.filter(c=>!c.body.erpReturnId && !c.body.erpMonitorSku)" :cases-complete="!all?.case.nextCursor" :disabled="busy" @more="more('case','cases')" @open="openSource" @case="id=>open('cases',id)" />

    </template>

    <template v-if="current?.kind==='CASE'">
      <div class="b-case-meta"><span class="chip" :class="current.state==='ESCALATED'?'danger':'plain'">{{status(current)}}</span><span>{{storeLabel(current.body.erpStoreName)}}</span></div>
      <p v-if="current.state==='ESCALATED'" class="banner danger">请优先核实安全问题并跟进处理。</p>
      <CaseWorkspace :asset="current" :busy="caseBusy || current.revision===0" :model-enabled="!!workspace?.modelEnabled" v-model:draft="humanText" v-model:message="message" v-model:attachments="attachments" v-model:reason="reviewReason"
        @generate="perform(()=>job(current!,'cases','advice-jobs'))" @evidence="perform(()=>job(current!,'cases','evidence-jobs'))" @history="showHistory" @investigate="prepareInvestigation()"
        @append="perform(async()=>{await mutate('cases',current!,'messages',{text:message,attachmentRefs:attachments.split(',').map(x=>x.trim()).filter(Boolean)});message='';attachments=''})"
        @link="(selected:string,reason:string)=>perform(async()=>{await mutate('cases',current!,'links',{lineId:selected,reason});await job(current!,'cases','evidence-jobs')})"
        @save="saveReply" />
      <details id="case-history" class="panel b-panel"><summary>消息、关联与处理历史</summary><article v-for="(r,i) in current.body.reviews" :key="i" class="b-fact"><b>人工处理 · {{formatDate(r.at)}}</b><p>{{r.text}}</p><small>依据：{{r.reason}} · {{r.actor}}</small></article><article v-for="v in current.history" :key="v.version"><p>版本 {{v.version}} · {{formatDate(v.createdAt)}} · {{stateNames[v.body._state] || v.body._state}}</p><small v-if="v.body.linkHistory?.length">关联变更：{{v.body.linkHistory.at(-1).reason || '首次必要确认'}}</small></article></details>
    </template>

    <template v-if="section==='experience'">
      <ReturnAnalysis v-if="workspace" :workspace="workspace" :cases="scopedCases" :investigations="scopedInvestigations" :disabled="busy" @open-investigation="viewInvestigation" @investigate-return="body=>startSourceInvestigation('return',body)" @investigate-sku="body=>startSourceInvestigation('monitor',body)" />
    </template>

    <template v-if="section==='risks'">
      <template v-if="current?.kind==='RISK'"><a :href="link('risks')" class="back">← 返回调查与风险</a><section class="panel b-panel"><div class="b-row"><h2>{{current.body.reason}}</h2><span class="chip warning">{{status(current)}}</span></div><p>{{current.body.limitations}}</p><dl class="b-fact-list"><div><dt>适用商品</dt><dd>{{current.body.identity.sku}}</dd></div><div><dt>适用店仓</dt><dd>{{current.body.identity.storeId}} / {{current.body.identity.warehouseMode==='ALL_STORE_WAREHOUSES'?'本店所有仓':current.body.identity.warehouseIds.join('、')}}</dd></div><div><dt>有效至</dt><dd>{{current.body.validUntil?formatDate(current.body.validUntil):'尚未人工确认'}}</dd></div></dl><div v-if="current.state==='SUSPECTED' || effectiveState(current)==='CONFIRMED'" class="b-risk-decision"><h3>{{current.state==='SUSPECTED'?'人工核实后确认提醒':'管理当前风险提醒'}}</h3><label>决定理由<input v-model="riskDecisionReason" required placeholder="记录核实依据或关闭、撤销原因"></label><label v-if="current.state==='SUSPECTED'">提醒有效至<input type="datetime-local" :value="new Date(validUntil).toLocaleString('sv-SE').slice(0,16).replace(' ','T')" @change="validUntil=new Date(($event.target as HTMLInputElement).value).toISOString()"></label><div class="button-row"><button v-for="d in (current.state==='SUSPECTED'?[{key:'CONFIRM',name:'确认风险并启用提醒'},{key:'REJECT',name:'驳回'}]:[{key:'CLOSE',name:'关闭'},{key:'REVOKE',name:'撤销'}])" :key="d.key" class="button" :class="{primary:d.key==='CONFIRM'}" :disabled="busy || !riskDecisionReason" @click="perform(()=>mutate('risks',current!,'decisions',{decision:d.key,reason:riskDecisionReason,validUntil:d.key==='CONFIRM'?validUntil:null}))">{{d.name}}</button></div></div><details open><summary>调查来源与决定历史</summary><p v-for="entry in all?.investigation.items.find(a=>a.id===current!.body.investigationId)?.body.entries || []" :key="entry.at">{{entry.text}}</p><blockquote v-for="(d,i) in current.body.decisions" :key="i">{{d.reason}}<small>{{d.actor}} · {{formatDate(d.at)}}</small></blockquote><button class="button small" @click="perform(async()=>{const a=all!.investigation.items.find(a=>a.id===current!.body.investigationId);if(a){viewInvestigation(a.id)}})">查看关联调查</button></details></section></template>
      <template v-else><section v-if="activeInvestigation" class="panel b-panel"><div class="b-row"><h2>AI 调查分析</h2><button class="button" :disabled="busy || currentTasks.some(taskRunning) || !workspace?.modelEnabled" @click="perform(assistInvestigation)">{{currentTasks.some(taskRunning)?'正在分析…':'AI 辅助调查'}}</button></div><template v-if="investigationAssist"><article v-for="a in [investigationAssist]" :key="a.at"><div v-if="a.ai.output"><p v-if="a.investigationRevision!==activeInvestigation.revision" class="muted">证据已更新，可重新分析。</p><h3>待核实线索</h3><p v-for="x in a.ai.output.hypotheses" :key="x">{{x}}</p><h3>其他可能</h3><p v-for="x in a.ai.output.alternativeExplanations" :key="x">{{x}}</p><h3>建议补充</h3><p v-for="x in a.ai.output.missingEvidence" :key="x">{{x}}</p><h3>下一步</h3><p v-for="x in a.ai.output.nextSteps" :key="x">{{x}}</p></div><p v-else class="muted">AI 暂不可用，可继续人工调查。</p></article></template><p v-else class="muted">暂无 AI 调查分析</p></section><template v-if="!activeInvestigation"><div class="b-risk-summary"><span>待跟进 <b>{{scopedInvestigations.filter(a=>['OPEN','NEEDS_EVIDENCE'].includes(a.state)).length}}</b></span><span>待确认 <b>{{scopedRisks.filter(r=>r.state==='SUSPECTED').length}}</b></span><span>有效提醒 <b>{{scopedRisks.filter(r=>effectiveState(r)==='CONFIRMED').length}}</b></span></div>
        <section class="panel b-panel"><h2>待跟进调查</h2><p v-if="!scopedInvestigations.some(a=>['OPEN','NEEDS_EVIDENCE'].includes(a.state))" class="muted">暂无调查。</p><article v-for="a in scopedInvestigations.filter(a=>['OPEN','NEEDS_EVIDENCE'].includes(a.state))" :key="a.id" class="b-fact"><div class="b-row"><div><b>{{a.body.entries[0].text}}</b><small>{{status(a)}} · {{formatDate(a.body.entries.at(-1).at)}}</small></div><button class="button small" :disabled="busy" @click="viewInvestigation(a.id)">继续调查</button></div></article><details v-if="scopedInvestigations.some(a=>!['OPEN','NEEDS_EVIDENCE'].includes(a.state))"><summary>已记录结论的调查</summary><a v-for="a in scopedInvestigations.filter(a=>!['OPEN','NEEDS_EVIDENCE'].includes(a.state))" :key="a.id" class="b-list-row" :href="href('/after-sales/risks',{investigation:a.id})"><span>{{a.body.entries[0].text}}</span><span>{{status(a)}}</span></a></details></section>
<section class="panel b-panel"><div class="b-queue-tabs"><button v-for="q in [{key:'CURRENT',name:'风险提醒'},{key:'HISTORY',name:'历史记录'},{key:'ALL',name:'全部'}]" :key="q.key" :class="{active:riskView===q.key}" @click="riskView=q.key">{{q.name}}</button></div><a v-for="a in filteredRisks" :key="a.id" class="b-list-row" :href="link('risks',a.id)"><div><b>{{a.body.reason}}</b><small>{{a.body.identity.sku}}</small></div><span class="chip warning">{{status(a)}}</span></a><p v-if="!filteredRisks.length" class="muted">暂无风险提醒。</p></section></template><a v-else class="back" :href="link('risks')">← 返回调查与风险</a>
        <section v-if="activeInvestigation" class="panel b-panel"><h2>{{activeInvestigation.body.entries[0].text}}</h2><a :href="link('cases',activeInvestigation.body.origin.id)">查看来源问题与证据 →</a><details><summary>调查记录</summary><p v-for="(e,i) in activeInvestigation.body.entries" :key="i">{{e.text}} · {{formatDate(e.at)}}</p></details><details><summary>添加证据</summary><form class="b-form" @submit.prevent="addInvestigationEvidence"><label>核实内容<textarea v-model="manualEvidence" required placeholder="检验结果、客户描述或现场记录"></textarea></label><label>证据来源<input v-model="manualEvidenceSource" required placeholder="照片位置、检验单号或记录链接"></label><button class="button" :disabled="busy">保存证据</button></form></details><form class="b-form" @submit.prevent="perform(()=>mutate('investigations',activeInvestigation!,'entries',{text:investigationText,evidenceRefs:chosenEvidence,conclusion}))"><label>本次核实情况<textarea v-model="investigationText" required placeholder="记录已核事实、补证及下一步"></textarea></label><details><summary>选择可追溯证据（已选 {{chosenEvidence.length}} 条）</summary><label v-for="f in investigationEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></details><label>人工结论<select v-model="conclusion" aria-label="人工结论"><option value="OPEN">继续调查</option><option value="SUPPORTED">证据支持风险</option><option value="REJECTED">证据不支持</option><option value="NEEDS_EVIDENCE">需进一步补证</option></select></label><button class="button primary" :disabled="busy || (conclusion==='SUPPORTED' && !chosenEvidence.length)">保存调查结论</button></form><button v-if="activeInvestigation.state==='SUPPORTED' && !risks.some(r=>r.body.investigationId===activeInvestigation!.id)" class="button" :disabled="busy" @click="riskRegister=true;riskReason=activeInvestigation.body.entries[0].text">确认质量风险</button><p v-else class="muted">{{risks.some(r=>r.body.investigationId===activeInvestigation!.id)?'此调查已有关联风险。':'请先保存人工调查结论。'}}</p></section>
        <form v-if="riskRegister && activeInvestigation" class="panel b-panel b-form" @submit.prevent="createRisk"><h2>确认质量风险</h2><label>问题与依据<textarea v-model="riskReason" required></textarea></label><label>尚未确认的事项<textarea v-model="limitations" required></textarea></label><label>本次涉及商品<select v-model="riskOption" required aria-label="本次涉及商品"><option value="">选择调查内已核实商品</option><option v-for="(p,i) in riskOptions" :key="i" :value="String(i)">{{p.name}}</option></select></label><p v-if="!riskOptions.length" class="b-gap">来源尚缺明确商品或仓库，先回到案件核实。</p><button class="button primary" :disabled="busy || !riskOptions.length">确认并提醒补货</button></form>
      </template>
    </template>
    <template v-if="section==='materials'">
      <div class="policy-actions"><button v-if="workspace?.capabilities?.policyWrite || workspace?.capabilities?.policyPublish" class="button" :class="{primary:!policyManage}" @click="policyManage=!policyManage">{{policyManage?'完成维护':'维护政策'}}</button><button v-if="workspace?.capabilities?.policyWrite" class="button primary" :disabled="busy" @click="openNewPolicy">新增政策</button></div>
      <section class="panel b-panel"><div class="b-row"><h2>售后政策</h2><button v-if="policyManage && workspace?.capabilities?.policyWrite" class="button" :disabled="busy" @click="importPolicyDrafts">准备政策草稿</button></div><label v-if="policyManage">适用范围<select v-model="starterScope"><option value="TEACHING">中国站</option><option value="AMAZON">Amazon · 美国</option></select></label><div class="policy-filters"><label>搜索政策<input v-model="policySearch" placeholder="政策名称或关键词"></label><label>类目<select v-model="policyCategoryFilter"><option value="ALL">全部类目</option><option value="APPAREL">服装</option><option value="ELECTRONICS">电子产品</option></select></label><label>状态<select v-model="policyStatusFilter"><option value="ALL">全部状态</option><option value="PUBLISHED">已发布</option><option value="DRAFT">草稿</option><option value="IN_REVIEW">待发布</option><option value="REVOKED">已撤销</option></select></label></div><article v-for="p in visiblePolicies.filter(p=>policyManage || p.state==='PUBLISHED')" :key="p.id" class="b-fact"><div class="b-row"><button class="policy-title" :aria-expanded="selectedPolicy===p.id" @click="selectedPolicy=selectedPolicy===p.id?'':p.id">{{p.body.title}} <span>{{selectedPolicy===p.id?'⌃':'⌄'}}</span></button><span class="chip plain">{{status(p)}}</span></div><div v-if="selectedPolicy===p.id" class="policy-body"><p v-for="s in p.body.sections" :key="s.id">{{s.text}}</p><small>{{p.body.source}}</small></div><p class="muted">{{p.body.category==='ALL'?'通用':p.body.category==='APPAREL'?'服装':'电子产品'}} / {{p.body.region}} / {{p.body.platform}} / {{p.body.language}} · {{p.body.effectiveFrom}} — {{p.body.effectiveUntil}}</p><div v-if="policyManage" class="button-row"><button v-if="workspace?.capabilities?.policyWrite && p.state==='DRAFT'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'submit-review',{}))">提交政策审核</button><button v-if="workspace?.capabilities?.policyPublish && p.state==='IN_REVIEW'" class="button primary" :disabled="busy" @click="perform(()=>mutate('policies',p,'publish',{reason:'本人核对政策正文及适用范围后明确发布'}))">确认并发布此政策</button><button v-if="workspace?.capabilities?.policyPublish && p.state==='PUBLISHED'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'revoke',{reason:'本人明确撤销此政策的后续使用'}))">撤销政策</button><button v-if="workspace?.capabilities?.policyWrite" class="button" :disabled="busy" @click="editingPolicy=p.id;policyRevisionText=p.body.sections.map((s:any)=>s.text).join('\n\n')">修订并新建草稿版本</button></div><form v-if="editingPolicy===p.id" @submit.prevent="editPolicy(p)"><label>修订正文<textarea v-model="policyRevisionText" required maxlength="4000"></textarea></label><p>原版本及引用保留，新版本须重新审核发布。</p><button class="button" :disabled="busy">保存新版本</button></form></article><details id="new-policy" v-if="policyManage && workspace?.capabilities?.policyWrite"><summary>录入新政策</summary><form class="b-form" @submit.prevent="createPolicy"><label>政策标题<input v-model="policyTitle" required></label><label>正文<textarea v-model="policyText" required></textarea></label><div class="b-grid"><label>适用话题<select v-model="policyTopic"><option v-for="[value,label] in policyTopics" :key="value" :value="value">{{label}}</option></select></label><label>类目<select v-model="policyCategory"><option value="APPAREL">服装</option><option value="ELECTRONICS">电子产品</option><option value="ALL">通用</option></select></label><label>地区<input v-model="policyRegion" required></label><label>平台<input v-model="policyPlatform" required></label><label>语言<input v-model="policyLanguage" required></label></div><button class="button" :disabled="busy">保存待审核草稿</button></form></details><p v-if="!visiblePolicies.some(p=>policyManage || p.state==='PUBLISHED')" class="muted">暂无可查看的政策。</p></section>
    </template>

    <Modal v-if="investigationOpen" title="发起人工调查" @close="investigationOpen=false"><form class="b-form" @submit.prevent="investigate(current!)"><label>需要调查的问题<textarea v-model="investigationText" required></textarea></label><fieldset><legend>本次调查依据</legend><label v-for="f in availableEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></fieldset><button class="button primary" :disabled="busy || !chosenEvidence.length">保存调查</button></form></Modal>
    <section v-if="all && ['workbench','cases','experience','risks'].includes(section)" class="b-tasks"><details><summary>后台任务与恢复</summary><p v-if="taskId">当前任务 {{taskId}}</p><div v-for="(t,key) in tasks" :key="t.id" class="b-list-row"><span>{{t.action==='advice-jobs'?'AI 回复':t.action==='investigation-jobs'?'调查分析':'资料更新'}} · {{t.state==='SUCCEEDED'?'已完成':t.state==='FAILED'?'未完成':'处理中'}}</span><button class="button small" @click="open('cases',t.assetId);followTask(key)">{{t.error?'继续查询':'查看'}}</button></div><button class="button" :disabled="busy" @click="perform(async()=>{const tasks=await get<any>('/tasks?workspaceId=after-sales-v1');backgroundTasks=tasks.items.filter((t:any)=>['B_CASE_EVIDENCE_V1','B_CASE_ADVICE_V1','B_INVESTIGATION_ASSIST_V1'].includes(t.scenarioId))})">查询任务历史</button><div v-for="t in backgroundTasks" :key="t.taskRef.taskId" class="b-list-row"><span>{{'售后处理'}} · {{t.state==='SUCCEEDED'?'已完成':t.state==='FAILED'?'需处理':t.state==='RUNNING'?'处理中':'等待处理'}}</span><button v-if="t.state==='SUCCEEDED'" class="button small" :disabled="busy" @click="perform(async()=>{const r=await request<any>('/analysis-tasks/'+t.taskRef.taskId+'/report');if(r.analysisReport.domainKind==='CASE')open('cases',r.analysisReport.domainRef.id)})">查看结果</button><span v-if="t.errorCode">{{t.errorCode}}</span></div></details></section>
  </div>
</template>

<style scoped>
.b-page{max-width:1360px;margin:auto;color:#243b4b}.b-page h1{font-size:27px}.b-page .page-head{margin-bottom:22px}.b-page h2{font-size:17px;margin:0 0 18px}.b-page h3{font-size:14px;margin:20px 0 10px}.b-page p{line-height:1.8;font-size:14px}.b-page small{font-size:12px;color:#71818b;line-height:1.7}.b-panel{padding:21px;margin:20px 0}.b-row{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}.b-row h2{margin:0}.b-queue{overflow:hidden}.b-queue-tabs{display:flex;gap:6px;border-bottom:1px solid #e1e8ec;padding:0 16px;overflow:auto}.b-queue-tabs button{border:0;border-bottom:2px solid transparent;padding:16px 8px;background:none;font:inherit;font-size:13px;white-space:nowrap;color:#71818b;cursor:pointer}.b-queue-tabs button.active{color:#116d66;border-color:#116d66;font-weight:600}.b-queue-tabs small{background:#f0f3f5;padding:1px 4px;margin-left:4px}.b-case-meta{display:flex;align-items:center;gap:10px;font-size:12px;margin:12px 0 22px;flex-wrap:wrap}.b-case-meta>.button{margin-left:auto}.b-fact-list{font-size:12px;margin:16px 0}.b-fact-list>div{display:flex;justify-content:space-between;gap:12px;padding:12px 0;border-bottom:1px solid #e5ebef}.b-fact-list dt{color:#71818b;flex-shrink:0}.b-fact-list dd{margin:0;text-align:right;overflow-wrap:anywhere}.b-fact{padding:12px 0;border-bottom:1px solid #e6ecef;font-size:13px}.b-fact p{font-size:13px;margin:6px 0}.b-fact small,.b-list-row small{display:block}.b-text-button{border:0;background:none;padding:6px 0;font:inherit;font-size:12px;color:#126c66;cursor:pointer}.b-text-button:disabled{opacity:.4}.b-gap{font-size:12px!important;border-left:3px solid #c7a65e;padding-left:10px;color:#82652d}.b-boundary{font-size:12px!important;color:#71818b;margin:18px 0}.b-form{display:grid;gap:12px}.b-page label{display:grid;gap:7px;margin:12px 0;color:#425f70;font-size:13px}.b-page input,.b-page select,.b-page textarea{border:1px solid #cbd7de;border-radius:5px;padding:9px 10px;width:100%;font:inherit;color:#243b4b;background:white;min-width:0}.b-page textarea{resize:vertical;min-height:85px}.b-check{display:flex!important;align-items:center;gap:8px}.b-check input{width:auto}.b-page fieldset{border:1px solid #dce4e9}.b-page summary{cursor:pointer;color:#37666c;font-size:12px}.b-page details{margin:18px 0}.b-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.b-list-row{display:flex;justify-content:space-between;gap:16px;padding:16px 0;border-bottom:1px solid #e5ebef;color:inherit;font-size:13px}.b-risk-summary{display:flex;gap:36px;font-size:13px;color:#71818b;padding:18px 0}.b-risk-summary b{font-size:22px;font-weight:600;color:#243b4b;margin-left:10px}.b-risk-decision{max-width:600px}.b-tasks{font-size:12px;color:#71818b;margin-top:22px}.b-page .banner{font-size:13px;overflow-wrap:anywhere}.b-page .button:disabled{opacity:.5}.b-page .back{font-size:12px;margin-bottom:12px;display:inline-block}

.policy-title{font:inherit;font-size:14px;font-weight:600;border:0;background:none;padding:10px 0;cursor:pointer;color:#254c61;text-align:left}.policy-title span{padding-left:12px;color:#80929c}.policy-body{border-left:3px solid #dce9e5;padding:0 16px}.policy-filters{display:flex;gap:16px;align-items:end;flex-wrap:wrap}.policy-filters label:first-child{flex:1;min-width:180px}.policy-actions{display:flex;justify-content:flex-end;gap:10px;margin:0 0 14px}.policy-actions .button{min-width:120px}.policy-actions+.b-panel>.b-text-button{display:none}@media(max-width:800px){.b-case-meta>.button{margin-left:0}.b-panel{padding:18px}.b-page h1{font-size:23px}.policy-actions{justify-content:flex-start;flex-wrap:wrap}}
</style>
