<script setup lang="ts">
import ModelUsage from '../components/ModelUsage.vue'
import StatusBadge from '../components/StatusBadge.vue'
import SourceInbox from './SourceInbox.vue'
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { route, navigate, href } from '../router'
import { request, errorText, ApiError } from '../api/client'
import { get, post, change, stateNames, labelNames, effectiveState, type Asset, type Workbench, type Workspace, type Index } from './api'

const workspace = ref<Workspace>(), all = ref<Workbench>(), current = ref<Asset>(), busy = ref(false), loading = ref(false), error = ref(''), note = ref('')
const section = computed(() => route.value.segments[1] || 'workbench')
const tabs = [{ key:'workbench',name:'售后工作台' },{key:'cases',name:'售后处理'},{key:'experience',name:'客户体验'},{key:'risks',name:'质量风险'},{key:'materials',name:'政策与资料'}]
const title = computed(() => tabs.find(t => t.key === section.value)?.name || '售后工作台')
const activeTask=ref<any>(),riskView=ref('CURRENT')
const filteredRisks=computed(()=>risks.value.filter(a=>riskView.value==='ALL' || riskView.value==='CURRENT' && ['SUSPECTED','CONFIRMED'].includes(effectiveState(a)) || riskView.value==='HISTORY' && !['SUSPECTED','CONFIRMED'].includes(effectiveState(a))))
const queue=ref('TODO'),caseSearch=ref(''),sourceFilter=ref('ALL'),productFilter=ref(''),selectedLabels=ref<string[]>(['UNKNOWN'])
const filteredCases=computed(()=>assets.value.filter(a=>(queue.value==='ALL' || queue.value==='TODO' && a.state!=='HANDLED' || a.state===queue.value) && (sourceFilter.value==='ALL' || (a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'TEACHING':'ERP')===sourceFilter.value) && (!caseSearch.value || [a.body.title,a.body.identity?.name,a.body.identity?.sku,a.body.orderId,a.body.erpTicketId].some(v=>v?.includes(caseSearch.value)))).sort((a,b)=>Number(b.state==='ESCALATED')-Number(a.state==='ESCALATED')))
const newCase = ref(false), customer = ref(''), caseTitle = ref(''), datasetId = ref(''), orderId = ref(''), businessDate = ref('2026-09-05T00:00:00Z')
const source = ref('TEACHING'), erpStore = ref(''), ticketId = ref(''), casePlatform = ref('TEACHING'), caseRegion = ref('CN'), caseLanguage = ref('zh')
const records = ref<Record<string, any>[]>([]), lineId = ref(''), linkReason = ref(''), message = ref(''), humanText = ref(''), reviewReason = ref('')
const selectedDataset = ref(''), reportData = ref<Asset>(), feedbackId = ref(''), labels = ref('UNKNOWN'), span = ref(''), correctionReason = ref('')
const investigationText = ref(''), investigationId = ref(''), evidenceRefs = ref(''), conclusion = ref('OPEN')
const riskReason = ref(''), limitations = ref('仅教学样本，尚未证实企业质量缺陷'), riskDataset = ref(''), riskDecisionReason = ref('')
const validUntil = ref(new Date(Date.now()+29*86400000).toISOString())
const mappingIdentity = ref(''), teachingIdentity = ref(''), bindingDataset = ref('')
const bindingProduct=ref(''),bindingSku=ref(''),mappingOptions=ref<any[]>([]),mappingChoice=ref('')
const bindingProducts=computed(()=>records.value.filter(r=>r.type==='product'))
watch(bindingDataset,id=>{mappingOptions.value=[];bindingProduct.value='';void readRecords(id)})
async function findMapping(){await perform(async()=>{mappingOptions.value=[];const q=new URLSearchParams({datasetId:bindingDataset.value,store:erpStore.value,sku:bindingSku.value});const result=await request<any>('/mapping-options?'+q,{},undefined,60000,'/api/b/v1');mappingOptions.value=result.items;mappingChoice.value='';if(!result.items.length)note.value='未找到可核实的商品店仓关系，请核对 SKU。'})}
const riskOptions = ref<{name:string;identity:Record<string,any>}[]>([]), riskOption = ref('')
const selectedEvidence = ref<any>(), backgroundTasks=ref<any[]>([]), policyRevisionText=ref(''), editingPolicy=ref(''), importFile=ref<File>(), investigationEvidence=ref<any[]>([]), chosenEvidence=ref<string[]>([])
const policyTitle = ref(''), policyText = ref(''), policyCategory = ref('APPAREL'), policyRegion = ref('CN'), policyPlatform = ref('TEACHING'), policyLanguage = ref('zh')
const compareReport=ref(''), attachments=ref('')
const analysisAI = ref(false), windows = ref(''), cutoff = ref(''), observationDays = ref(30), threshold = ref(10)
const pending = ref<{ key:string; path:string; body?:unknown }>(), taskId = ref(''), alive = ref(true)
let sequence = 0
const assets = computed(() => all.value?.case.items || [])
const datasets = computed(() => all.value?.dataset.items || [])
const activeDatasets = computed(() => datasets.value.filter(a => a.state === 'ACTIVE'))
const risks = computed(() => all.value?.risk.items || [])
const returnTo = computed(() => { const value = route.value.query.returnTo; return value?.startsWith('/') && !value.startsWith('//') ? value : '' })
const identityCandidates = computed(() => current.value?.body.evidence?.identityCandidates || [])
const lastAdvice = computed(() => current.value?.body.advice?.at(-1))
const effectiveClassifications = computed(() => {
  const b = reportData.value?.body; if (!b) return []
  return (b.feedback || []).filter((f:any)=>!productFilter.value || f.productId===productFilter.value).map((f: any) => ({...f, classification:[...(b.classificationCorrections || [])].reverse().find((x: any) => x.feedbackId === f.feedbackId) || b.classifications.find((x: any) => x.feedbackId === f.feedbackId)}))
})
const productItems=computed(()=>[...(reportData.value?.body.metrics.items || [])].sort((a:any,b:any)=>Number(b.finding==='NEEDS_INVESTIGATION')-Number(a.finding==='NEEDS_INVESTIGATION')))
const themeCounts = computed(() => { const counts: Record<string,number> = {}; for (const f of effectiveClassifications.value) for (const label of new Set<string>(f.classification?.labels || ['UNKNOWN'])) counts[label] = (counts[label] || 0)+1; return counts })
function link(page:string,id?:string) { return href('/after-sales/'+page,{id,returnTo:returnTo.value || undefined}) }
function open(page:string,id:string) { navigate('/after-sales/'+page,{id,returnTo:returnTo.value || undefined}) }
function collection() { return section.value === 'experience' ? 'analyses' : section.value }
function status(a:Asset) { return stateNames[effectiveState(a)] || a.state }
function pretty(v:unknown) { return typeof v === 'string' ? v : JSON.stringify(v,null,2) }
const stages:Record<string,string>={draft:'草稿',requested:'申请',authorized:'曾授权',authorizedValid:'有效授权',received:'实收',refunded:'实际退款',cancelled:'取消'}
const factNames:Record<string,string>={TICKET:'工单标题（不是完整会话）',ORDER:'关联订单',PAYMENT:'已核付款记录',SHIPMENT:'已核发货记录',feedback:'客户反馈原文',payment_status:'订单付款状态',fulfillment_status:'订单履约状态',refund_status:'订单退款状态'}
function factText(f:any) {
  const r=f.value ?? f.record ?? f
  if(r.type==='shipment')return `实际发货 ${r.quantity} 件，时间 ${r.at}`
  if(r.type==='return')return `${stages[r.stage] || r.stage} ${r.quantity} 件，时间 ${r.at}`+(r.amount!=null?`；退款 ${r.amount} ${r.currency}`:'')
  if(r.type==='order')return `订单${r.paid===true?'已记录支付':'支付状态待核实'}；业务时间 ${r.paidAt || '未提供'}`
  if(r.type==='feedback')return r.text
  if(f.text)return f.text
  if(f.domain==='PAYMENT')return `已记录支付 ${r.amount} ${r.currency || ''}，时间 ${r.at}`
  if(typeof r==='string')return r
  if(Array.isArray(r))return r.map(x=>`时间 ${x.at || '未提供'}；明细见证据来源`).join('；')
  return Object.entries(r).filter(([,v])=>typeof v!=='object').map(([k,v])=>`${factNames[k] || k}：${v}`).join('；')
}
watch([investigationId,all],async([id])=>{
  riskOptions.value=[];riskOption.value='';const inv=all.value?.investigation.items.find(a=>a.id===id);if(!inv)return
  try{
    const origin=await get<Asset>('/'+(inv.body.origin.kind==='REPORT'?'analyses':'cases')+'/'+inv.body.origin.id)
    if(id!==investigationId.value)return
    const dsId=origin.body.datasetId
    riskDataset.value=dsId || ''
    if(dsId){
      const ds=datasets.value.find(d=>d.id===dsId);if(!ds)return
      const items=origin.kind==='REPORT'?origin.body.metrics.items:[origin.body.identity].filter(Boolean)
      riskOptions.value=items.map((p:any)=>({name:p.name+' · '+p.sku,identity:{sourceTenant:ds.scope.sourceTenant,productId:p.productId,sku:p.sku,storeId:p.storeId,warehouseMode:'EXPLICIT_IDS',warehouseIds:origin.body.identity?[origin.body.identity.warehouseId]:ds.body.manifest.warehouseIds}}))
    } else if(origin.body.identity && origin.body.identity.warehouseId!=='UNKNOWN'){const p=origin.body.identity;riskOptions.value=[{name:p.name+' · '+p.sku,identity:{sourceTenant:origin.scope.sourceTenant,productId:p.productId,sku:p.sku,storeId:p.storeId,warehouseMode:'EXPLICIT_IDS',warehouseIds:[p.warehouseId]}}]}
  }catch(e){error.value=errorText(e)}
})
async function refresh() {
  const run=++sequence;loading.value=true;error.value='';current.value=undefined;reportData.value=undefined;selectedEvidence.value=undefined;chosenEvidence.value=[];investigationEvidence.value=[]
  try {
    const [w,index] = await Promise.all([get<Workspace>('/workspace'),get<Workbench>('/workbench')])
    if(run!==sequence || !alive.value)return
    if(!workspace.value)analysisAI.value=w.modelEnabled
    workspace.value=w;all.value=index
    if(!selectedDataset.value) selectedDataset.value=index.dataset.items.find(d => d.state==='ACTIVE')?.id || ''
    if(!erpStore.value)erpStore.value=w.sourceStores[0] || ''
    if(route.value.query.id && ['cases','experience','risks'].includes(section.value)) {
      const a=await get<Asset>('/'+collection()+'/'+encodeURIComponent(route.value.query.id))
      if(run!==sequence || !alive.value)return
      current.value=a
      if(a.kind==='REPORT')reportData.value=a
    }
  } catch(e){if(run===sequence){error.value=errorText(e);all.value=undefined;workspace.value=undefined;records.value=[];backgroundTasks.value=[]}}
  finally{if(run===sequence)loading.value=false}
}
async function command<T>(path:string,body:unknown):Promise<T> {
  if(pending.value)throw new Error('PENDING_COMMAND')
  const value={path,body,key:crypto.randomUUID()};pending.value=value
  sessionStorage.setItem('b-pending-command',JSON.stringify({path:value.path,key:value.key}))
  try{const result=await post<T>(path,body,value.key);pending.value=undefined;sessionStorage.removeItem('b-pending-command');return result}
  catch(e){if(e instanceof ApiError){pending.value=undefined;sessionStorage.removeItem('b-pending-command')}throw e}
}
async function perform(action:()=>Promise<void>) {
  if(busy.value)return
  busy.value=true;error.value='';note.value=''
  try{await action()}catch(e){error.value=e instanceof Error && !(e instanceof ApiError) && e.message==='PENDING_COMMAND'?'请先核对上一笔结果不确定的操作。':e instanceof Error && !(e instanceof ApiError) && e.message.startsWith('TASK:')?'任务未完成：'+e.message.slice(5)+'，已保留已有事实和记录。':errorText(e)}finally{busy.value=false}
}
async function retry() { if(!pending.value)return;await perform(async()=>{const p=pending.value!;const result=await get<any>('/commands/'+p.key);pending.value=undefined;sessionStorage.removeItem('b-pending-command');await refresh();note.value='原命令已找到并核对。';if(result.result?.taskRef)taskId.value=result.result.taskRef.taskId}) }
async function mutate(collection:string,asset:Asset,action:string,data:unknown) {
  await command('/'+collection+'/'+asset.id+'/'+action,{expectedRevision:asset.revision,data});await refresh()
}
async function job(asset:Asset,collection:string,action:string,data:unknown={}) {
  const accepted=await command<{ taskRef:{taskId:string} }>('/'+collection+'/'+asset.id+'/'+action,{expectedRevision:asset.revision,data})
  taskId.value=accepted.taskRef.taskId
  const ownTask=accepted.taskRef.taskId, ownRoute=route.value.path+'?'+(route.value.query.id || '')
  note.value='任务已受理，正在读取和处理…'
  // Task survives leaving this page. Re-open through history to continue reading.
  for(let attempt=0;attempt<300 && alive.value;attempt++) {
    const task=await request<any>('/analysis-tasks/'+ownTask)
    if(ownTask===taskId.value)activeTask.value=task
    if(task.state==='SUCCEEDED') {
      const report=await request<any>('/analysis-tasks/'+ownTask+'/report')
      if(ownRoute!==route.value.path+'?'+(route.value.query.id || ''))return
      note.value='处理完成，已保存到历史。'
      if(report.analysisReport.domainKind==='REPORT')open('experience',report.analysisReport.domainRef.id)
      await refresh();return
    }
    if(['FAILED','CANCELLED'].includes(task.state))throw new Error('TASK:'+(task.errorCode || task.state))
    await new Promise(resolve=>setTimeout(resolve,1000))
  }
  if(alive.value)note.value='任务仍在后台，请稍后从任务历史查看。'
}
async function openSource(record:any){await perform(async()=>{
  const erpTicketId=record.kind==='tickets'?record.ticketId:null
  const erpVoiceId=record.kind==='tickets'?null:record.recordId
  const existing=assets.value.find(a=>a.body.erpStoreName===record.storeName && (erpTicketId?a.body.erpTicketId===erpTicketId:a.body.erpVoiceId===erpVoiceId && a.body.erpVoiceKind===record.kind))
  if(existing){open('cases',existing.id);return}
  const created=await command<Asset>('/cases',{title:record.title || '客户反馈',message:'',region:'UNKNOWN',platform:'UNKNOWN',language:'zh',erpStoreName:record.storeName,erpTicketId,erpVoiceId,erpVoiceKind:erpVoiceId?record.kind:null})
  open('cases',created.id);const saved=await get<Asset>('/cases/'+created.id);await job(saved,'cases','evidence-jobs')
})}
function formatDate(value:any){return value?new Date(value).toLocaleString():'未提供'}
function metricFact(ref:string){const metrics=reportData.value?.body.metrics;if(!ref.startsWith('metric:') || !metrics)return ref;const [,id,index]=ref.split(':');const item=metrics.items.find((p:any)=>p.productId===id);const g=item?.groups[Number(index)];return g?`${item.name} · ${index==='0'?'上期':'本期'}实收退货 ${g.numerator} / 实发 ${g.denominator} 件，退货率 ${g.ratePercent ?? '未知'}%`:ref}
function prepareInvestigation(origin:Asset){investigationText.value=origin.kind==='CASE'?(lastAdvice.value?.feedbackAI?.analysis.output?.hypotheses || []).join('；'):(origin.body.ai.output?.hypotheses || []).join('；');document.getElementById('investigation-start')?.scrollIntoView({behavior:'smooth'})}
function showProduct(id:string){productFilter.value=id;document.getElementById('customer-feedback')?.scrollIntoView({behavior:'smooth'})}
async function createCase() {await perform(async()=>{
  const erp=source.value==='ERP'
  const result=await command<Asset>('/cases',{title:caseTitle.value || (erp?'ERP工单接入':'客户问题'),message:customer.value,region:caseRegion.value,platform:erp?'UNKNOWN':casePlatform.value,language:caseLanguage.value,
    businessDate:erp?null:businessDate.value,datasetId:erp?null:datasetId.value || null,orderId:erp?null:orderId.value || null,erpStoreName:erp?erpStore.value:null,erpTicketId:erp?ticketId.value || null:null})
  newCase.value=false;customer.value='';open('cases',result.id)
  const saved=await get<Asset>('/cases/'+result.id)
  await job(saved,'cases','evidence-jobs')
})}
async function readRecords(id:string) {
  records.value=[];if(!id)return
  let offset=0
  do {const page=await get<{items:Record<string,any>[];nextOffset:number|null}>('/datasets/'+id+'/records?offset='+offset);records.value.push(...page.items);if(page.nextOffset==null)break;offset=page.nextOffset} while(offset<10000)
}
watch(datasetId,id=>{void readRecords(id)})
async function importPackage(custom?:{manifest:any;chunks:any[]}) {await perform(async()=>{
  const pkg=custom || await get<{manifest:any;chunks:any[]}>('/teaching-package')
  const existing=datasets.value.find(d=>d.body.manifest.datasetId===pkg.manifest.datasetId && d.body.manifest.version===pkg.manifest.version)
  if(existing && existing.state!=='DRAFT')throw new Error('此版本已封存，请使用新的资料版本。')
  const created=existing || await command<Asset>('/datasets',{manifest:pkg.manifest})
  let revision=created.revision
  for(let number=0;number<pkg.chunks.length;number++) {
    const saved=await command<Asset>('/datasets/'+created.id+'/chunks',{expectedRevision:revision,number,records:pkg.chunks[number]});revision=saved.revision
  }
  await command('/datasets/'+created.id+'/seal',{expectedRevision:revision,data:{}})
  const sealed=await get<Asset>('/datasets/'+created.id);await job(sealed,'datasets','validation-jobs')
  note.value='资料已导入并校验；请核对后点击“启用资料”。'
})}
async function importLocalPackage(){if(!importFile.value)return;try{await importPackage(JSON.parse(await importFile.value.text()))}catch(e){error.value=errorText(e)}}
async function more(key:keyof Workbench,path:string){await perform(async()=>{const old=all.value?.[key];if(!old?.nextCursor)return;const next=await get<Index>('/'+path+'?limit=100&before='+old.nextCursor);old.items.push(...next.items);old.nextCursor=next.nextCursor})}
async function editPolicy(p:Asset){await perform(()=>mutate('policies',p,'new-version',{policy:{...Object.fromEntries(Object.entries(p.body).filter(([k])=>!k.startsWith('_') && !['publishedBy','publishedAt','publishReason','revocationReason'].includes(k))),sections:[{id:'s1',text:policyRevisionText.value}]}}));editingPolicy.value=''}
const availableEvidence=computed(()=>reportData.value?.body.feedback.map((f:any)=>({id:f.feedbackId,text:f.text})) || current.value?.body.evidence?.facts.map((f:any)=>({id:f.id,text:factText(f)})) || [])
async function chooseInvestigation(a:Asset){investigationId.value=a.id;const o=a.body.origin;const origin=await get<Asset>('/'+(o.kind==='CASE'?'cases':'analyses')+'/'+o.id);limitations.value=origin.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'仅独立教学样本，不代表企业质量缺陷':'来源为教学 ERP 观察；原因与缺陷仍需人工调查，不代表已认证质量结论';investigationEvidence.value=o.kind==='CASE'?(origin.body.evidence?.facts || []).map((f:any)=>({id:f.id,text:factText(f)})):origin.body.feedback.map((f:any)=>({id:f.feedbackId,text:f.text}));chosenEvidence.value=[]}
async function importPolicyDrafts() {await perform(async()=>{for(const p of await get<any[]>('/policy-starters'))await command('/policies',p);await refresh();note.value='四类教学政策已保存为草稿，请逐项审核发布。'})}
async function createPolicy() {await perform(async()=>{
  await command('/policies',{title:policyTitle.value,category:policyCategory.value,topics:['REPLY'],sections:[{id:'s1',text:policyText.value}],region:policyRegion.value,platform:policyPlatform.value,language:policyLanguage.value,
    effectiveFrom:'2026-01-01T00:00:00Z',effectiveUntil:'2027-01-01T00:00:00Z',source:'本机人工录入政策，待人工发布',terms:['CLARIFY','MANUAL_REVIEW']});await refresh();policyTitle.value='';policyText.value=''
})}
async function analyze() {await perform(async()=>{
  const d=datasets.value.find(d=>d.id===selectedDataset.value);if(!d)return
  const rule={version:'return-config-'+crypto.randomUUID().slice(0,8),observationDays:Number(observationDays.value),minOrders:20,minQuantity:20,deltaBasisPoints:Math.round(Number(threshold.value)*100),minReceived:3}
  await job(d,'datasets','analysis-jobs',{ai:analysisAI.value,compareReportId:compareReport.value || undefined,windows:d.body.manifest.windows,asOf:d.body.manifest.asOf,rule})
})}
async function investigate(origin:Asset) {await perform(async()=>{const result=await command<Asset>('/investigations',{kind:origin.kind,id:origin.id,text:investigationText.value,evidenceRefs:chosenEvidence.value});investigationText.value='';open('risks','');await refresh();investigationId.value=result.id;note.value='调查已建立，请在下方补充证据与人工结论。'})}
async function createRisk() {await perform(async()=>{const identity=riskOptions.value[Number(riskOption.value)]?.identity;if(!identity)throw new Error('RISK_SCOPE_REQUIRED');const result=await command<Asset>('/risks',{investigationId:investigationId.value,reason:riskReason.value,limitations:limitations.value,identity,datasetId:riskDataset.value || null});open('risks',result.id);await refresh()})}
async function bind(){await perform(async()=>{
 const ds=datasets.value.find(d=>d.id===bindingDataset.value),product=bindingProducts.value.find(p=>p.id===bindingProduct.value),erpIdentity=mappingOptions.value[Number(mappingChoice.value)]?.identity
 if(!ds || !product || !erpIdentity)return
 const lines=records.value.filter(r=>r.type==='line' && r.productId===product.id),stores=[...new Set(lines.map(l=>l.storeId))]
 if(stores.length!==1)throw new Error('请使用单店教学资料建立精确映射')
 const ti={sourceTenant:ds.scope.sourceTenant,productId:product.id,sku:product.sku,storeId:stores[0],warehouseMode:'EXPLICIT_IDS',warehouseIds:[...new Set(lines.map(l=>l.warehouseId))]}
 await job(ds,'datasets','binding-jobs',{teachingIdentity:ti,erpIdentity,validUntil:validUntil.value})
})}
function warnDraft(event:BeforeUnloadEvent){if(humanText.value || message.value){event.preventDefault();event.returnValue=''}}
function guardDraft(event:MouseEvent){const anchor=(event.target as Element)?.closest('a');if(anchor && anchor.hash!==location.hash && (humanText.value || message.value) && !confirm('人工处理稿或补充消息尚未保存。确认离开并放弃未保存内容？')){event.preventDefault();event.stopImmediatePropagation()}}
onMounted(()=>{window.addEventListener('beforeunload',warnDraft);document.addEventListener('click',guardDraft,true)})
onBeforeUnmount(()=>{window.removeEventListener('beforeunload',warnDraft);document.removeEventListener('click',guardDraft,true)})
watch(()=>route.value.query.id,(id,previous)=>{if(id!==previous){humanText.value='';reviewReason.value='';message.value='';attachments.value='';productFilter.value=''}})
onMounted(()=>{try{const saved=sessionStorage.getItem('b-pending-command');if(saved)pending.value=JSON.parse(saved)}catch{};void refresh()})
onBeforeUnmount(()=>{alive.value=false;sequence++})
watch(()=>[route.value.path,route.value.query.id],()=>{void refresh()})
</script>

<template>
  <div class="b-page">
    <nav class="b-tabs" aria-label="售后业务导航"><a v-for="tab in tabs" :key="tab.key" :href="link(tab.key)" :class="{active:section===tab.key}">{{tab.name}}</a></nav>
    <header class="page-head"><div><span class="eyebrow">智能售后与客户体验</span><h1>{{title}}</h1></div><button class="button" :disabled="busy || loading" @click="refresh">刷新</button></header>
    <a v-if="returnTo" class="back" :href="'#'+returnTo">← 返回原补货页面</a>
    <p v-if="error" class="banner danger" role="alert">{{error}}</p><p v-if="note" class="banner" role="status">{{note}}</p>
    <p v-if="pending" class="banner warning">上一操作结果待核对。<button class="button small" :disabled="busy" @click="retry">核对原命令</button></p>
    <p v-if="loading" role="status">正在读取当前记录…</p><p v-if="activeTask && busy" class="banner" role="status"><StatusBadge :value="activeTask.state" /> {{activeTask.scenarioId.includes('EVIDENCE')?'正在核实 ERP 与商品证据':activeTask.scenarioId.includes('ADVICE')?'正在检索政策并生成建议':'正在处理分析资料'}}；可离开页面，稍后从任务历史继续查看。</p>
    <p v-if="workspace && !workspace.modelEnabled" class="b-model-note">AI 暂未启用：等待本模块独立调用授权。可先核实事实、查看统计并记录人工处理；页面不会显示模拟 AI 结论。</p>

    <template v-if="['workbench','cases'].includes(section)">
      <template v-if="!current">
        <p class="b-intro">从已有客户问题开始，核实商品与证据，审核处理建议。已处理记录可随时回查。</p>
        <SourceInbox v-if="workspace" :stores="workspace?.sourceStores || []" :disabled="busy" @open="openSource" />
        <section class="panel b-panel"><div class="b-row"><h2>我的售后待办</h2><button class="button small" :disabled="busy" @click="newCase=!newCase">人工补充 / 教学体验</button></div>
          <div class="b-inline-form"><label>处理状态<select v-model="queue"><option value="TODO">所有待跟进</option><option value="REVIEW_PENDING">待审核建议</option><option value="EVIDENCE_PENDING">待补证</option><option value="NEEDS_CLARIFICATION">待澄清</option><option value="ESCALATED">优先人工处理</option><option value="HANDLED">内部处理完成</option><option value="ALL">全部历史</option></select></label><label>数据来源<select v-model="sourceFilter"><option value="ALL">全部（逐条标注来源）</option><option value="ERP">教学 ERP 只读</option><option value="TEACHING">中台独立教学</option></select></label><label>查找案件<input v-model="caseSearch" placeholder="问题、商品、SKU 或订单"></label></div>
          <a v-for="a in filteredCases" :key="a.id" class="b-list-row" :href="link('cases',a.id)"><div><b>{{a.body.title}}</b><small>{{a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台独立教学':'教学 ERP 只读'}} · {{a.body.identity?.name || '商品待核实'}}<span v-if="a.body.identity"> · {{a.body.identity.sku}}</span></small><small>{{a.state==='ESCALATED'?'下一步：优先人工核实安全信号':a.state==='REVIEW_PENDING'?'下一步：审核 AI 建议并保存处理':a.state==='HANDLED'?'可查看人工处理及原始依据':!a.body.identity?'下一步：核实受影响商品':'下一步：核实证据、政策并审核处理'}}</small></div><span class="chip" :class="a.state==='ESCALATED'?'danger':'plain'">{{status(a)}}</span></a>
          <p v-if="!filteredCases.length" class="empty-inline">此筛选下没有已接入案件。可打开上方 ERP 记录开始处理，或查看全部历史。</p><p class="muted">此队列仅含已接入中台的授权案件；ERP 来源范围在上方单独说明。</p>
        </section>
        <form v-if="newCase" class="panel b-panel b-form" @submit.prevent="createCase">
          <h2>人工补充与独立教学</h2><label>来源<select v-model="source"><option value="TEACHING">中台教学资料</option><option value="ERP">获准 ERP 工单（只读）</option></select></label>
          <template v-if="source==='ERP'"><label>店铺<select v-model="erpStore" required><option v-for="s in workspace?.sourceStores" :key="s">{{s}}</option></select></label><label>工单 ID（异常补录时使用）<input v-model="ticketId" placeholder="留空可先发现该店工单" pattern="[1-9][0-9]*"></label></template>
          <template v-else><label>教学版本<select v-model="datasetId"><option value="">暂未关联资料</option><option v-for="d in activeDatasets" :value="d.id" :key="d.id">{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</option></select></label><label>订单<select v-model="orderId"><option value="">待补充订单</option><option v-for="o in records.filter(r=>r.type==='order')" :value="o.id" :key="o.id">{{o.orderNumber}}</option></select></label><label>案件业务日期<input v-model="businessDate" required></label></template>
          <label>问题标题<input v-model="caseTitle" maxlength="200" placeholder="概括客户遇到的问题"></label><label>客户原话<textarea v-model="customer" :required="source!=='ERP'" maxlength="6000" placeholder="仅录入实际收到的客户主张；工单标题不会被当作完整会话"></textarea></label>
          <details><summary>适用地区、平台与语言</summary><div class="b-grid"><label>地区<input v-model="caseRegion"></label><label>平台<input v-model="casePlatform"></label><label>语言<input v-model="caseLanguage"></label></div></details><button class="button primary" :disabled="busy">保存并核实事实</button>
        </form>
      </template>
      <template v-if="current?.kind==='CASE'">
        <a class="back" :href="link('cases')">← 返回售后待办</a>
        <section class="panel b-panel"><div class="b-row"><div><h2>{{current.body.title}}</h2><p class="muted">{{current.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台独立教学资料':'教学 ERP 只读观察'}} · {{current.body.erpStoreName || '独立教学店铺'}} · 内部处理记录</p></div><span class="chip warning">{{status(current)}}</span></div>
          <p v-if="current.state==='ESCALATED'" class="banner danger">安全信号优先转人工处理；不等待 AI，不指导拆机。</p>
          <p class="banner">下一步：{{!current.body.identity?'核实下方订单中的受影响商品；缺少证据时先向客户澄清。':!lastAdvice?'查看已核事实，再检索政策和生成建议；也可直接记录人工处理。':lastAdvice.ai.status==='AVAILABLE'?'审核建议、修订处理稿并保存内部决定。':'查看未生成原因和已有证据，继续补证或记录人工处理。'}}</p>
        </section>
        <div class="b-case-grid"><div class="b-case-evidence">
          <section class="panel b-panel"><h2>客户遇到了什么问题</h2><blockquote v-for="(m,i) in current.body.messages" :key="i">{{m.text}}<small>{{m.source==='CLAIM'?'人工补充的客户主张':'ERP 反馈原文'}} · {{formatDate(m.at)}}</small><small v-if="m.attachmentRefs?.length">待核附件：{{m.attachmentRefs.join('、')}}</small></blockquote><p v-if="!current.body.messages.length" class="banner warning">ERP 当前仅提供工单标题，尚无完整客户会话。请先获取真实诉求，不能把标题当作客户原话。</p>
            <details><summary>补充客户消息与附件线索</summary><form @submit.prevent="perform(async()=>{await mutate('cases',current!,'messages',{text:message,attachmentRefs:attachments.split(',').map(x=>x.trim()).filter(Boolean)});message='';attachments=''})"><label>补充客户消息<textarea v-model="message" required maxlength="6000"></textarea></label><label>客户提供的附件引用（可选）<input v-model="attachments" placeholder="仅记录已收到的附件线索，多个以逗号分隔"></label><button class="button" :disabled="busy || !message">追加消息</button></form></details>
          </section>
          <section class="panel b-panel"><div class="b-row"><h2>关联商品与已核事实</h2><button class="button small" :disabled="busy" @click="perform(()=>job(current!,'cases','evidence-jobs'))">重新核实事实</button></div>
            <div v-if="current.body.identity"><h3>{{current.body.identity.name}}</h3><p>{{current.body.identity.sku}} · {{current.body.identity.category==='UNKNOWN'?'商品类别待核实':current.body.identity.category==='APPAREL'?'服装':'电子产品'}}</p><p class="muted">{{current.body.identity.orderId==='UNKNOWN'?'订单尚未核实；本条反馈仅关联商品':'已核实所属订单'}} · {{current.body.identity.warehouseId==='UNKNOWN'?'发货仓尚未核实':'已核实来源仓库'}}</p></div><p v-else class="banner warning">尚未确定受影响商品，请核实订单和商品关联。</p>
            <details v-if="current.body.identity && identityCandidates.length"><summary>关联依据与纠正</summary><p>系统使用本次来源证据中的商品；更正已有记录会保留原值、操作者和原因。</p><form class="b-form" @submit.prevent="perform(async()=>{await mutate('cases',current!,'links',{lineId,reason:linkReason});lineId='';linkReason=''})"><label>纠正已有商品关联<select v-model="lineId" required><option value="">请选择本来源已核商品</option><option v-for="c in identityCandidates" :key="c.lineId" :value="c.lineId">{{c.name}} · {{c.sku}}</option></select></label><label>纠正原因<input v-model="linkReason" required></label><button class="button" :disabled="busy || !lineId">留痕纠正</button></form></details>
            <form v-else-if="identityCandidates.length" class="b-form" @submit.prevent="perform(async()=>{await mutate('cases',current!,'links',{lineId,reason:''});lineId=''})"><label>选择本订单受影响商品<select v-model="lineId" required><option value="">仅有多商品订单，请核实本次诉求对象</option><option v-for="c in identityCandidates" :key="c.lineId" :value="c.lineId">{{c.name}} · {{c.sku}}</option></select></label><button class="button" :disabled="busy || !lineId">确认商品</button></form>
            <details open v-if="current.body.evidence?.missing.length"><summary>尚待核实与处理限制</summary><p v-for="gap in current.body.evidence.missing" :key="gap" class="b-gap">{{gap}}</p></details>
            <div v-for="f in current.body.evidence?.facts" :key="f.id" class="b-fact"><b>{{factNames[f.domain] || (f.domain==='shipment'?'实际发货':f.domain==='return'?'退货记录':f.domain==='order'?'订单事实':'业务事实')}}</b><span class="chip plain">{{f.kind==='SIMULATED'?'独立教学事实':'ERP 已观察'}}</span><p>{{factText(f)}}</p><details><summary>证据来源与观察时间</summary><small>{{f.sourceRef}} · {{formatDate(f.observedAt)}}</small></details></div><p v-if="!current.body.evidence?.facts?.length" class="muted">尚无可用业务事实；客户陈述仍保留，不能据此承诺处理结果。</p>
          </section>
        </div><div class="b-case-actions">
          <section class="panel b-panel"><div class="b-row"><h2>{{current.body.erpVoiceId?'AI 反馈总结与处理建议':'AI 处理建议'}}</h2><button class="button primary" :disabled="busy || !current.body.identity || !current.body.evidence" @click="perform(()=>job(current!,'cases','advice-jobs'))">检索政策并生成建议</button></div>
            <p v-if="!lastAdvice" class="muted">结合客户原话、已核事实和适用政策生成可审核的草稿。AI 不确认缺陷，不执行退款或发送消息。</p>
            <template v-else><p v-if="lastAdvice.ai.status!=='AVAILABLE'" class="banner warning">建议未生成：{{lastAdvice.ai.reason==='B_MODEL_AUTHORIZATION_REQUIRED'?'B 模型调用未授权':lastAdvice.ai.reason==='POLICY_NOT_APPLICABLE'?'缺少匹配且已发布的政策（需核实类别、地区、语言及业务日期）':lastAdvice.ai.reason}}</p><template v-else><p class="b-ai-draft">{{lastAdvice.ai.output.replyDraft}}</p><button class="button small" @click="humanText=lastAdvice.ai.output.replyDraft">使用草稿，继续人工审核</button><p v-if="lastAdvice.caseRevision!==current.revision" class="banner warning">案件已有新版本，旧建议需重新生成后才可采纳。</p><ul><li v-for="g in lastAdvice.ai.output.missingEvidence" :key="g">待补证：{{g}}</li></ul></template>
            <details v-for="p in lastAdvice.policies" :key="p.policyId+p.sectionId"><summary>{{p.title}} · 政策依据</summary><p>{{p.text}}</p><small>版本 {{p.version}}</small></details></template>
            <ModelUsage v-if="lastAdvice" :ai="lastAdvice.ai" /><template v-if="lastAdvice?.feedbackAI"><h3>客户反馈分析</h3><div v-if="lastAdvice.feedbackAI.classifications.status==='AVAILABLE'" class="button-row"><span v-for="l in lastAdvice.feedbackAI.classifications.output.items[0]?.labels || []" :key="l" class="chip plain">{{labelNames[l] || l}}</span></div><p v-if="lastAdvice.feedbackAI.analysis.status!=='AVAILABLE'" class="muted">本次未生成 AI 原因分析，保留反馈原文与已核关联。</p><template v-else><h4>可能原因（待验证）</h4><p v-for="t in lastAdvice.feedbackAI.analysis.output.hypotheses" :key="t">{{t}}</p><h4>建议下一步</h4><p v-for="t in lastAdvice.feedbackAI.analysis.output.nextSteps" :key="t">{{t}}</p><details><summary>其他解释与待补材料</summary><p v-for="t in [...lastAdvice.feedbackAI.analysis.output.alternativeExplanations,...lastAdvice.feedbackAI.analysis.output.missingEvidence]" :key="t">{{t}}</p></details></template><ModelUsage :ai="lastAdvice.feedbackAI.analysis" /><button class="button" @click="prepareInvestigation(current!)">围绕此问题发起调查</button></template>
          </section>
          <section class="panel b-panel"><h2>审核并记录处理</h2><label>人工处理稿<textarea v-model="humanText" required maxlength="6000" placeholder="核对证据，修订回复或记录下一步处理"></textarea></label><label>审核理由<input v-model="reviewReason" required maxlength="1000" placeholder="说明本次决定的依据"></label><div class="button-row"><button v-for="d in [{key:'ACCEPT',label:'采纳并保存'},{key:'MANUAL',label:'保存人工处理'},{key:'RETURN',label:'退回补充'},{key:'ESCALATE',label:'升级人工'}]" :key="d.key" class="button" :disabled="busy || !humanText || !reviewReason || (d.key==='ACCEPT' && (lastAdvice?.ai.status!=='AVAILABLE' || lastAdvice?.caseRevision!==current.revision))" @click="perform(async()=>{await mutate('cases',current!,'reviews',{adviceVersion:lastAdvice?.version || null,text:humanText,reason:reviewReason,decision:d.key});humanText='';reviewReason=''})">{{d.label}}</button></div><p class="muted">仅保存内部记录，客户消息与退款须另行处理。</p><details :open="!!current.body.reviews.length"><summary>已记录的人工处理</summary><blockquote v-for="(r,i) in current.body.reviews" :key="i"><p>{{r.text}}</p><small>理由：{{r.reason}} · 审核者 {{r.actor}} · {{formatDate(r.at)}}</small></blockquote></details></section>
        </div></div>
      </template>
    </template>

    <template v-if="section==='experience'">
      <SourceInbox v-if="!reportData && workspace" :stores="workspace?.sourceStores || []" initial-kind="reviews" :disabled="busy" @open="openSource" />
      <p v-if="!reportData" class="banner">ERP 评价可直接进入商品问题核实与 AI 辅助处理。完整退货群组尚未核实，退货对比仅使用下方独立教学资料。</p>
      <section class="panel b-panel"><h2>独立教学：退货变化与原因调查</h2><div class="b-inline-form"><label>教学数据版本<select v-model="selectedDataset"><option value="">选择已启用资料</option><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</option></select></label><label class="b-check"><input v-model="analysisAI" type="checkbox" :disabled="!workspace?.modelEnabled">同时进行 AI 主题与原因分析</label><button class="button primary" :disabled="busy || !selectedDataset" @click="analyze">开始分析</button></div><label>与历史报告比较（可选）<select v-model="compareReport"><option value="">不比较</option><option v-for="r in all?.report.items" :key="r.id" :value="r.id">{{r.body.createdAt}} / {{r.body.datasetVersion}}</option></select></label><details><summary>观察范围与判定说明</summary><p>使用所选资料已核对的两段等长业务期间及截止日期，等待实际发货后满 30 天再判断；每期至少 20 个订单商品、20 件实发，实收退货至少 3 件且退货率上升至少 10 个百分点才提示调查。</p><p v-for="(w,i) in datasets.find(d=>d.id===selectedDataset)?.body.manifest.windows || []" :key="i">{{i===0?'上期':'本期'}}：{{formatDate(w[0])}} 至 {{formatDate(w[1])}}</p></details></section>
      <section v-if="!reportData" class="panel b-panel"><h2>分析历史</h2><a v-for="a in all?.report.items" :key="a.id" class="b-list-row" :href="link('experience',a.id)"><div><b>客户体验与退货分析</b><small>{{a.body.createdAt}} · {{a.body.datasetVersion}}</small></div><span>{{a.body.metrics.items.filter((i:any)=>i.finding==='NEEDS_INVESTIGATION').length}} 项待调查</span></a><p v-if="!all?.report.items.length" class="muted">还没有分析报告，请先在“政策与资料”导入、校验并启用教学资料。</p></section>
      <template v-if="reportData"><a :href="link('experience')" class="back">← 返回报告历史</a><p class="b-source">中台独立教学数据 · {{reportData.body.datasetVersion}} · 不与 ERP 交易混算</p>
        <section v-if="reportData.body.comparison" class="panel b-panel"><h2>与所选历史报告的差异</h2><p>{{reportData.body.comparison.comparable?'相同选择窗与观察周期':'观察口径发生变化，勿直接比较退货率'}} · 历史资料 {{reportData.body.comparison.datasetVersion}}</p><p>资料版本{{reportData.body.comparison.changes.datasetVersionChanged?'已变化':'相同'}}，输入事实{{reportData.body.comparison.changes.inputChanged?'有更新':'相同'}}，规则{{reportData.body.comparison.changes.ruleChanged?'有更新':'相同'}}。</p><p v-for="i in reportData.body.comparison.items" :key="i.productId">{{i.sku}}：历史本期 {{i.previous?.groups[1].numerator ?? '未知'}} / {{i.previous?.groups[1].denominator ?? '未知'}} 件 → 当前 {{i.current.groups[1].numerator}} / {{i.current.groups[1].denominator}} 件</p><small>{{reportData.body.comparison.limitation}}</small></section><section class="panel b-panel"><h2>退货变化与待调查问题</h2><article v-for="item in productItems" :key="item.productId+item.storeId" class="b-product-result"><div class="b-row"><h3>{{item.name}}</h3><span class="chip" :class="item.finding==='NEEDS_INVESTIGATION'?'warning':'plain'">{{item.finding==='NEEDS_INVESTIGATION'?'待调查异常':item.finding==='UNKNOWN'?'数据不足':'未触发异常阈值'}}</span></div><div class="b-stats"><div><small>上期退货率</small><b>{{item.groups[0].ratePercent==null?'未知':item.groups[0].ratePercent+'%'}}</b><span>{{item.groups[0].numerator}} / {{item.groups[0].denominator}} 件</span></div><div><small>本期退货率</small><b>{{item.groups[1].ratePercent==null?'未知':item.groups[1].ratePercent+'%'}}</b><span>{{item.groups[1].numerator}} / {{item.groups[1].denominator}} 件</span></div><div><small>变化</small><b>{{item.deltaPercentagePoints==null?'未知':item.deltaPercentagePoints+' 个百分点'}}</b><span>实收退货，不等于缺陷确认</span></div></div><p class="b-business-finding">{{item.deltaPercentagePoints==null?'数据不足，暂时无法判断；请补齐发货与退货记录。':Number(item.deltaPercentagePoints)>0?'退货率较上期上升 '+Number(item.deltaPercentagePoints)+' 个百分点':Number(item.deltaPercentagePoints)<0?'退货率较上期下降 '+Math.abs(Number(item.deltaPercentagePoints))+' 个百分点':'退货率与上期持平'}}</p><button class="button small" @click="showProduct(item.productId)">查看此商品的客户反馈</button><p v-for="g in item.groups" :key="g.denominator+g.numerator">{{g.unresolved?.length ? '待补证：'+g.unresolved.join('、') : ''}}</p><details><summary>阶段件数、金额与统计依据</summary><p>{{reportData.body.metrics.definition}}</p><div v-for="(g,i) in item.groups" :key="i"><h4>{{i===0?'上期':'本期'}}</h4><p>已满足观察期的订单商品 {{g.matureOrders}} / {{g.orders}}</p><p v-for="(count,stage) in g.stages" :key="stage">{{stages[stage] || stage}}：{{count}} 件</p><p>实际退款：{{Object.entries(g.refundAmounts).map(([currency,amount])=>amount+' '+currency).join('；') || '未提供'}}（按币种分列）</p><p>期外事件：{{g.outsideWindow.length}} 条</p><details><summary>发货、退货证据</summary><div class="button-row"><button v-for="eid in g.evidenceRefs" :key="eid" class="button small" :disabled="busy" @click="perform(async()=>{selectedEvidence=await get('/analyses/'+reportData!.id+'/evidence/'+eid)})">依据 {{eid.split('-').slice(-3).join('-')}}</button></div></details></div></details></article></section>
        <section class="panel b-panel"><h2>AI 原因分析</h2><ModelUsage :ai="reportData.body.ai" /><p v-if="reportData.body.ai.status!=='AVAILABLE'" class="muted">本次 AI 分析未生成，已核统计保留。{{reportData.body.ai.reason==='B_MODEL_AUTHORIZATION_REQUIRED'?'B 模型调用未授权':reportData.body.ai.reason}}</p><template v-else><div v-for="(name,key) in {facts:'已核事实引用',hypotheses:'待验证原因',alternativeExplanations:'其他可能解释',missingEvidence:'需补充证据',nextSteps:'建议下一步'}" :key="key"><h3>{{name}}</h3><ul><li v-for="text in reportData.body.ai.output[key]" :key="text">{{key==='facts'?metricFact(text):text}}</li></ul></div></template></section>
        <section id="customer-feedback" class="panel b-panel"><h2>商品反馈与主题</h2><label>查看商品<select v-model="productFilter"><option value="">全部反馈（含未定位商品）</option><option v-for="p in productItems" :key="p.productId" :value="p.productId">{{p.name}} · {{p.sku}}</option></select></label><p class="muted">按唯一反馈统计，含未分类反馈；多标签占比合计可能超过 100%。订单级反馈不分摊到商品。</p><div class="button-row"><span v-for="(n,l) in themeCounts" :key="l" class="chip plain">{{labelNames[l] || l}} {{n}} / {{effectiveClassifications.length}}</span></div><article v-for="f in effectiveClassifications" :key="f.feedbackId" class="b-fact"><p>{{f.text}}</p><p><small>{{f.productName?f.productName+' · '+f.sku:'商品未核实（不分摊到商品）'}}</small>{{f.classification?.labels.map((l:string)=>labelNames[l] || l).join('、')}} · {{f.channel==='ORDER_FEEDBACK'?'订单反馈':'客户反馈'}}</p><small>原文证据 {{f.feedbackId}} · {{f.lineId?'已关联订单明细':'订单级，未分摊商品'}}</small></article><details><summary>人工修订主题</summary><form class="b-form" @submit.prevent="perform(()=>mutate('analyses',reportData!,'classifications',{feedbackId,labels:selectedLabels,span,reason:correctionReason}))"><label>反馈<select v-model="feedbackId" required><option v-for="f in effectiveClassifications" :key="f.feedbackId" :value="f.feedbackId">{{f.text}}</option></select></label><fieldset><legend>反馈主题（可多选）</legend><label v-for="(name,code) in labelNames" :key="code" class="b-check"><input v-model="selectedLabels" type="checkbox" :value="code">{{name}}</label></fieldset><label>对应原文片段<input v-model="span" required></label><label>修订原因<input v-model="correctionReason" required></label><button class="button" :disabled="busy">留痕保存分类</button></form></details></section>
      </template>
    </template>

    <template v-if="(section==='cases' && current?.kind==='CASE') || (section==='experience' && reportData)">
      <section id="investigation-start" class="panel b-panel"><h2>发起人工调查</h2><form class="b-form" @submit.prevent="investigate((reportData || current)!)"><label>需要调查的问题<textarea v-model="investigationText" required></textarea></label><fieldset><legend>选择本次调查依据</legend><label v-for="f in availableEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></fieldset><button class="button" :disabled="busy">保存调查</button></form></section>
      <details class="panel b-panel"><summary>版本与处理历史</summary><article v-for="v in (reportData || current)?.history" :key="v.version"><h4>版本 {{v.version}} · {{v.createdAt}}</h4><p>操作者 {{v.actor}} · {{stateNames[v.body._state] || v.body._state}}</p><p v-if="v.body.identity">商品 {{v.body.identity.name}} · {{v.body.identity.sku}}</p><p v-if="v.body.linkHistory?.length">关联修订 {{v.body.linkHistory.length}} 次 · {{v.body.linkHistory.at(-1).reason || '首次必要确认'}}</p></article></details>
    </template>

    <template v-if="section==='risks'">
      <template v-if="current?.kind==='RISK'"><a :href="link('risks')" class="back">← 返回风险列表</a><section class="panel b-panel"><div class="b-row"><h2>{{current.body.reason}}</h2><span class="chip warning">{{status(current)}}</span></div><p>{{current.body.limitations}}</p><p class="b-source">{{current.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'独立教学风险：仅在明确授权并核实映射后演示补货提醒':'ERP 证据调查：人工确认后在对应商品店仓提醒'}}</p><p>适用商品 {{current.body.identity.sku}} · 店铺 {{current.body.identity.storeId}} · {{current.body.identity.warehouseMode==='ALL_STORE_WAREHOUSES'?'本店所有仓':current.body.identity.warehouseIds.join('、')}}</p><p>有效至 {{current.body.validUntil || '尚未人工确认'}}</p><label>决定理由<input v-model="riskDecisionReason" required></label><label v-if="current.state==='SUSPECTED'">提醒有效至（默认30天以内）<input type="datetime-local" :value="new Date(validUntil).toLocaleString('sv-SE').slice(0,16).replace(' ','T')" @change="validUntil=new Date(($event.target as HTMLInputElement).value).toISOString()"></label><div class="button-row"><button v-for="d in (current.state==='SUSPECTED'?[{key:'CONFIRM',name:'人工确认风险'},{key:'REJECT',name:'驳回'}]:effectiveState(current)==='CONFIRMED'?[{key:'CLOSE',name:'关闭'},{key:'REVOKE',name:'撤销'}]:[])" :key="d.key" class="button" :disabled="busy || !riskDecisionReason" @click="perform(()=>mutate('risks',current!,'decisions',{decision:d.key,reason:riskDecisionReason,validUntil:d.key==='CONFIRM'?validUntil:null}))">{{d.name}}</button></div><p class="muted">确认前须完成有证据支持的人工调查；风险只提醒，补货算法和采购条件继续适用。</p><h3>决定历史</h3><blockquote v-for="(d,i) in current.body.decisions" :key="i">{{d.reason}}<small>{{({CONFIRM:'人工确认',REJECT:'驳回',CLOSE:'关闭',REVOKE:'撤销'} as Record<string,string>)[d.decision] || d.decision}} · {{d.actor}} · {{d.at}}</small></blockquote><details><summary>历史版本</summary><article v-for="v in current.history" :key="v.version"><p>版本 {{v.version}} · {{stateNames[v.body._state] || v.body._state}} · {{v.createdAt}}</p><p>{{v.body.reason}}</p></article></details></section></template>
      <section v-else class="panel b-panel"><h2>风险线索与有效提醒</h2><label>查看风险<select v-model="riskView"><option value="CURRENT">疑似与当前有效提醒</option><option value="HISTORY">已关闭、撤销及到期</option><option value="ALL">全部历史</option></select></label><a v-for="a in filteredRisks" :key="a.id" class="b-list-row" :href="link('risks',a.id)"><div><b>{{a.body.reason}}</b><small>{{a.body.identity.sku}} · {{a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台教学风险':'ERP 事实调查'}}</small></div><span class="chip warning">{{status(a)}}</span></a><p v-if="!filteredRisks.length" class="muted">尚无风险。请先从案件或分析报告发起调查。</p></section>
      <section class="panel b-panel"><h2>人工调查</h2><article v-for="a in all?.investigation.items" :key="a.id" class="b-investigation"><div class="b-row"><h3>{{a.body.entries[0].text}}</h3><span class="chip plain">{{status(a)}}</span></div><p v-for="(entry,i) in a.body.entries" :key="i">{{entry.text}} · {{entry.conclusion==='SUPPORTED'?'证据支持':entry.conclusion==='REJECTED'?'不支持':entry.conclusion==='NEEDS_EVIDENCE'?'需补证':'调查中'}}<small> {{entry.actor}} · {{entry.at}}</small></p><button class="button small" :disabled="busy" @click="perform(()=>chooseInvestigation(a))">补充本次调查</button><details v-if="investigationId===a.id" open><summary>补充证据与结论</summary><form class="b-form" @submit.prevent="perform(()=>mutate('investigations',a,'entries',{text:investigationText,evidenceRefs:chosenEvidence,conclusion}))"><label>补证记录<textarea v-model="investigationText" required></textarea></label><fieldset><legend>可回查的调查证据</legend><label v-for="f in investigationEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></fieldset><label>人工结论<select v-model="conclusion"><option value="OPEN">继续调查</option><option value="SUPPORTED">证据支持风险</option><option value="REJECTED">证据不支持</option><option value="NEEDS_EVIDENCE">需进一步补证</option></select></label><button class="button" :disabled="busy">保存调查结论</button></form></details><button class="button small" :disabled="busy" @click="perform(async()=>{await chooseInvestigation(a);riskReason=a.body.entries[0].text})">将此调查登记为疑似风险</button></article></section>
      <form v-if="investigationId" class="panel b-panel b-form" @submit.prevent="createRisk"><h2>登记疑似风险</h2><label>调查<select v-model="investigationId" required><option v-for="a in all?.investigation.items" :key="a.id" :value="a.id">{{a.body.entries[0].text}}</option></select></label><label>问题与依据<textarea v-model="riskReason" required></textarea></label><label>限制与未确认事项<textarea v-model="limitations" required></textarea></label><label>本次调查涉及商品<select v-model="riskOption" required><option value="">请选择已核实商品</option><option v-for="(p,i) in riskOptions" :key="i" :value="String(i)">{{p.name}}</option></select></label><p class="muted">风险仅登记在来源调查已核实的商品、店铺与仓库范围；其他店铺需另行调查确认。</p><p v-if="!riskOptions.length" class="banner warning">此来源尚缺可核实的商品店仓范围。可以继续调查，补齐证据前不能形成有效补货风险提醒。</p><button class="button" :disabled="busy">保存疑似风险</button></form>
    </template>

    <template v-if="section==='materials'">
      <section class="panel b-panel"><div class="b-row"><h2>独立教学资料</h2><button class="button primary" :disabled="busy || datasets.some(d=>d.body.manifest.datasetId==='b-golden-20261116' && d.state!=='DRAFT')" @click="importPackage()">导入完整教学资料</button></div><p class="muted">40 张逻辑订单、每张 2 个商品，含实际发货、各退货阶段与反馈；资料存入中台，不创建 ERP 单据。</p><article v-for="d in datasets" :key="d.id" class="b-fact"><div class="b-row"><h3>{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</h3><span class="chip plain">{{status(d)}}</span></div><p v-for="issue in d.body.issues" :key="issue" class="banner danger">{{issue}}</p><p v-if="d.body.validation">已回读 {{d.body.validation.count}} 条事实 · {{d.body.validation.at}}</p><div class="button-row"><button v-if="d.state==='READBACK_VERIFIED'" class="button primary" :disabled="busy" @click="perform(()=>mutate('datasets',d,'activate',{}))">启用资料</button><button v-if="d.state==='ACTIVE'" class="button" :disabled="busy" @click="perform(()=>mutate('datasets',d,'deactivate',{}))">停用资料</button><button v-if="d.state==='SEALED'" class="button" :disabled="busy" @click="perform(()=>job(d,'datasets','validation-jobs'))">校验并独立回读</button><button class="button" :disabled="busy" @click="perform(async()=>{await readRecords(d.id);note='已读取资料，可在下方核对原始教学事实。'})">核对资料</button></div></article><details><summary>导入其他版本 / 继续未完成导入</summary><p>选择包含 manifest 和 chunks 的独立教学 JSON 包。版本、数量、指纹与全部关联会在启用前校验；同版本草稿可断点继续，迟到数据必须新建版本。</p><input type="file" accept=".json" aria-label="教学资料文件" @change="importFile=($event.target as HTMLInputElement).files?.[0]"><button class="button" :disabled="busy || !importFile" @click="importLocalPackage">导入并核对资料版本</button></details><details v-if="records.length"><summary>教学事实与证据（{{records.length}}条）</summary><article v-for="r in records" :key="r.id" class="b-fact"><p>{{factText(r)}}</p><small>资料记录 {{r.id}}</small></article></details></section>
      <section class="panel b-panel"><div class="b-row"><h2>政策知识</h2><button class="button" :disabled="busy || !!all?.policy.items.length" @click="importPolicyDrafts">准备四类教学政策草稿</button></div><p class="muted">草稿不能检索。请核对正文、适用范围及有效期，再明确发布；不代表企业正式政策。</p><article v-for="p in all?.policy.items" :key="p.id" class="b-fact"><div class="b-row"><h3>{{p.body.title}}</h3><span class="chip plain">{{status(p)}}</span></div><p v-for="s in p.body.sections" :key="s.id">{{s.text}}</p><p class="muted">{{p.body.category==='ALL'?'全部已声明类目':p.body.category}} / {{p.body.region}} / {{p.body.platform}} / {{p.body.language}} · {{p.body.effectiveFrom}} — {{p.body.effectiveUntil}}</p><div class="button-row"><button v-if="p.state==='DRAFT'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'submit-review',{}))">提交政策审核</button><button v-if="p.state==='IN_REVIEW'" class="button primary" :disabled="busy" @click="perform(()=>mutate('policies',p,'publish',{reason:'本人核对上述教学政策正文及适用范围后明确发布'}))">确认并发布此政策</button><button v-if="p.state==='PUBLISHED'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'revoke',{reason:'本人明确撤销此政策的后续使用'}))">撤销政策</button><button class="button" :disabled="busy" @click="editingPolicy=p.id;policyRevisionText=p.body.sections.map((s:any)=>s.text).join('\n\n')">修订并新建草稿版本</button></div><form v-if="editingPolicy===p.id" @submit.prevent="editPolicy(p)"><label>修订正文<textarea v-model="policyRevisionText" required maxlength="4000"></textarea></label><p>原版本及引用保留，新版本须重新审核发布。</p><button class="button" :disabled="busy">保存新版本</button></form></article><details><summary>录入新政策</summary><form class="b-form" @submit.prevent="createPolicy"><label>政策标题<input v-model="policyTitle" required></label><label>正文<textarea v-model="policyText" required></textarea></label><div class="b-grid"><label>类目<select v-model="policyCategory"><option value="APPAREL">服装</option><option value="ELECTRONICS">电子产品</option><option value="ALL">两类均适用</option></select></label><label>地区<input v-model="policyRegion" required></label><label>平台<input v-model="policyPlatform" required></label><label>语言<input v-model="policyLanguage" required></label></div><button class="button" :disabled="busy">保存待审核草稿</button></form></details></section>
      <details class="panel b-panel"><summary>教学风险与 ERP 商品的受控演示绑定</summary><p>需有管理权限。绑定由独立 ERP 回读核对真实商品和仓库，范围精确到当前用户、资料版本、店仓和有效期；不改变补货算法。</p><form class="b-form" @submit.prevent="bind"><label>教学版本<select v-model="bindingDataset" required><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}}</option></select></label><label>教学商品<select v-model="bindingProduct" required><option value="">选择资料内商品</option><option v-for="p in bindingProducts" :key="p.id" :value="p.id">{{p.name}} · {{p.sku}}</option></select></label><label>目标 ERP 店铺<select v-model="erpStore"><option v-for="s in workspace?.sourceStores" :key="s">{{s}}</option></select></label><label>目标 ERP 商品 SKU<input v-model="bindingSku" required placeholder="输入已获准商品 SKU 后核实"></label><button class="button" type="button" :disabled="busy || !bindingDataset || !bindingSku" @click="findMapping">查找已核实的商品与仓库</button><label>目标商品与仓库<select v-model="mappingChoice" required><option value="">从 ERP 已核实结果中选择</option><option v-for="(p,i) in mappingOptions" :key="i" :value="String(i)">{{p.name}}</option></select></label><label>有效至<input type="datetime-local" :value="new Date(validUntil).toLocaleString('sv-SE').slice(0,16).replace(' ','T')" @change="validUntil=new Date(($event.target as HTMLInputElement).value).toISOString()" required></label><button class="button" :disabled="busy">独立核实并建立演示绑定</button></form><article v-for="b in all?.binding.items" :key="b.id"><p>{{b.body.teachingIdentity.sku}} → {{b.body.erpIdentity.sku}} · {{status(b)}} · {{b.body.validUntil}}</p><button v-if="b.state==='ACTIVE'" class="button" :disabled="busy" @click="perform(()=>mutate('teaching-bindings',b,'revoke',{reason:'人工撤销教学演示绑定'}))">撤销绑定</button></article></details>
    </template>
    <div v-if="all && !route.query.id" class="button-row"><button v-for="[key,path,name] in ([['case','cases','案件'],['report','analyses','分析'],['risk','risks','风险'],['investigation','investigations','调查'],['dataset','datasets','资料'],['policy','policies','政策'],['binding','teaching-bindings','绑定']] as const)" v-show="all[key].nextCursor" :key="key" class="button small" :disabled="busy" @click="more(key,path)">加载更多{{name}}</button></div><section v-if="selectedEvidence" class="panel b-panel"><div class="b-row"><h2>原始业务依据</h2><button class="button small" @click="selectedEvidence=undefined">关闭</button></div><p>{{selectedEvidence.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台教学资料':'ERP 只读事实'}} · {{selectedEvidence.datasetVersion}}</p><p>{{factText(selectedEvidence.record)}}</p><details><summary>证据定位与校验</summary><p>记录 {{selectedEvidence.record?.id}} · 版本 {{selectedEvidence.datasetVersion || 'ERP 观察'}}</p><small>校验指纹 {{selectedEvidence.hash}}</small></details></section>
    <section v-if="all && ['workbench','cases','experience','risks'].includes(section)" class="b-tasks"><details><summary>后台任务与恢复</summary><p v-if="taskId">当前任务 {{taskId}}</p><button class="button" :disabled="busy" @click="perform(async()=>{const tasks=await get<any>('/tasks?workspaceId=after-sales-v1');backgroundTasks=tasks.items})">查询任务历史</button><div v-for="t in backgroundTasks" :key="t.taskRef.taskId" class="b-list-row"><span>{{t.scenarioId.includes('CASE')?'售后处理':t.scenarioId.includes('EXPERIENCE')?'体验分析':'资料核验'}} · {{t.state==='SUCCEEDED'?'已完成':t.state==='FAILED'?'需处理':t.state==='RUNNING'?'处理中':'等待处理'}}</span><button v-if="t.state==='SUCCEEDED'" class="button small" :disabled="busy" @click="perform(async()=>{const r=await request<any>('/analysis-tasks/'+t.taskRef.taskId+'/report');if(['CASE','REPORT','RISK'].includes(r.analysisReport.domainKind))open(r.analysisReport.domainKind==='CASE'?'cases':r.analysisReport.domainKind==='REPORT'?'experience':'risks',r.analysisReport.domainRef.id);else note='资料任务已完成，请在政策与资料查看。'})">查看结果</button><span v-if="t.errorCode">{{t.errorCode}}</span></div></details></section>
  </div>
</template>

<style scoped>
.b-case-grid{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:24px;align-items:start}.b-case-grid .b-panel{margin-top:0}.b-case-grid>div{min-width:0}.b-intro{color:#526573;line-height:1.8}.b-gap{border-left:3px solid #c49b4a;padding-left:12px;font-size:14px;line-height:1.7}.b-business-finding{font-size:18px;font-weight:600;color:#244d52}.b-page{max-width:1350px;margin:auto}.b-tabs{display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #dce5e9;margin-bottom:24px}.b-tabs a{padding:12px 16px;color:#526573;text-decoration:none;border-bottom:3px solid transparent}.b-tabs a.active{color:#0f6b64;border-color:#0f6b64;font-weight:700}.b-panel{padding:24px;margin:22px 0}.b-panel h2{font-size:19px;margin:0 0 20px}.b-panel h3{font-size:16px}.b-row{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.b-row h2,.b-row h3{margin:0}.b-list-row{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:20px 4px;border-bottom:1px solid #e5ebee;text-decoration:none;color:inherit}.b-list-row small,blockquote small{display:block;margin-top:8px;color:#687c88}.b-hero{display:flex;justify-content:space-between;align-items:center;gap:25px;background:#eaf4ef;border:1px solid #cce1d5;border-radius:12px;padding:30px;margin:24px 0}.b-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin:22px 0}.b-stats>a,.b-stats>div{background:#f6f8fa;border:1px solid #e2e8ec;border-radius:9px;padding:20px;color:inherit;text-decoration:none;display:grid;gap:7px}.b-stats b{font-size:25px;color:#193f46}.b-stats span,.b-stats small{font-size:13px;color:#687c88}.b-form{display:grid;gap:17px}.b-page label{display:grid;gap:8px;margin:12px 0;color:#3f5661;font-size:14px}.b-page input,.b-page select,.b-page textarea{border:1px solid #cad7dd;border-radius:6px;padding:10px 12px;background:white;color:#233d49;font:inherit;width:100%;min-width:0}.b-page textarea{min-height:95px;resize:vertical}.b-form>.button{justify-self:start}.b-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.b-inline-form{display:flex;align-items:end;gap:16px;flex-wrap:wrap}.b-inline-form label{flex:1;min-width:180px}.b-check{display:flex!important;align-items:center;gap:8px}.b-check input{width:auto}.b-fact,.b-investigation{padding:18px 0;border-bottom:1px solid #e2e9ed}.b-fact pre,.b-panel pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.65;background:#f7f9fa;padding:14px;border-radius:6px;max-height:400px;overflow:auto}.b-page details{margin:16px 0}.b-page summary{cursor:pointer;color:#42636b;font-size:14px}.b-model-note,.b-source{padding:12px 16px;background:#edf3f7;border-left:3px solid #7e9da8;color:#47616e;font-size:13px}.b-page blockquote{padding:15px 18px;background:#f5f7f9;border-left:3px solid #bad0d8;margin:14px 0;white-space:pre-wrap;overflow-wrap:anywhere}.b-ai-draft{font-size:17px;line-height:1.8;padding:20px;background:#eff7f2}.b-product-result{padding:20px 0;border-bottom:1px solid #e2e9ed}.b-tasks{font-size:13px;color:#748590}.b-page .button:disabled{opacity:.5}.b-page .banner{overflow-wrap:anywhere}.b-page h1{font-size:28px}
@media(max-width:1050px){.b-case-grid{grid-template-columns:1fr}.b-stats{gap:10px}.b-stats b{font-size:21px}.b-grid{grid-template-columns:1fr 1fr}.b-hero{padding:22px}.b-tabs a{padding:11px}}
@media(max-width:700px){.b-stats,.b-grid{grid-template-columns:1fr}.b-hero{display:block}.b-panel{padding:18px}.b-tabs{gap:0}.b-tabs a{font-size:13px}.b-inline-form{display:block}}
</style>
