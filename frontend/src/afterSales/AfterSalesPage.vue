<script setup lang="ts">
import ModelUsage from '../components/ModelUsage.vue'
import Modal from '../components/Modal.vue'
import ProductExperience from './ProductExperience.vue'
import StatusBadge from '../components/StatusBadge.vue'
import SourceInbox from './SourceInbox.vue'
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { route, navigate, href } from '../router'
import { request, errorText, ApiError } from '../api/client'
import { get, post, change, stateNames, labelNames, effectiveState, type Asset, type Workbench, type Workspace, type Index } from './api'

const workspace = ref<Workspace>(), all = ref<Workbench>(), current = ref<Asset>(), busy = ref(false), loading = ref(false), error = ref(''), note = ref('')
const section = computed(() => route.value.segments[1] || 'workbench')
const tabs = [{ key:'workbench',name:'售后工作台' },{key:'cases',name:'售后处理'},{key:'experience',name:'客户体验'},{key:'risks',name:'质量风险'},{key:'materials',name:'知识与资料'}]
const title = computed(() => current.value?.kind==='CASE'?current.value.body.title:section.value==='experience'?'客户体验与退货分析':tabs.find(t => t.key === section.value)?.name || '售后工作台')
const activeTask=ref<any>(),riskView=ref('CURRENT')
const filteredRisks=computed(()=>scopedRisks.value.filter(a=>riskView.value==='ALL' || riskView.value==='CURRENT' && ['SUSPECTED','CONFIRMED'].includes(effectiveState(a)) || riskView.value==='HISTORY' && !['SUSPECTED','CONFIRMED'].includes(effectiveState(a))))
const queue=ref('TODO'),caseSearch=ref(''),sourceFilter=ref(route.value.query.source || 'ERP'),productFilter=ref(''),selectedLabels=ref<string[]>(['UNKNOWN'])
const scopedCases=computed(()=>assets.value.filter(a=>(a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'TEACHING':'ERP')===sourceFilter.value))
const queueItems=[{key:'TODO',name:'待处理'},{key:'EVIDENCE_PENDING',name:'待补证'},{key:'REVIEW_PENDING',name:'待审核'},{key:'HANDLED',name:'处理记录'}]
function inQueue(a:Asset,key:string){return key==='ALL' || key==='TODO' && ['OPEN','ESCALATED'].includes(a.state) || key==='EVIDENCE_PENDING' && ['EVIDENCE_PENDING','NEEDS_CLARIFICATION'].includes(a.state) || a.state===key}
const filteredCases=computed(()=>scopedCases.value.filter(a=>inQueue(a,queue.value) && (!caseSearch.value || [a.body.title,a.body.identity?.name,a.body.identity?.sku,a.body.orderId,a.body.erpTicketId].some(v=>v?.includes(caseSearch.value)))).sort((a,b)=>Number(b.state==='ESCALATED')-Number(a.state==='ESCALATED')))
const scopedRisks=computed(()=>risks.value.filter(a=>(a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'TEACHING':'ERP')===sourceFilter.value))
const latestReport=computed(()=>all.value?.report.items.find(r=>activeDatasets.value.some(d=>d.id===r.body.datasetId)))
const alerts=computed(()=>latestReport.value?.body.metrics.items.filter((p:any)=>p.finding==='NEEDS_INVESTIGATION') || [])
const investigationOpen=ref(false), classificationOpen=ref(false), analysisSettings=ref(false), riskRegister=ref(false)
const activeInvestigation=computed(()=>all.value?.investigation.items.find(a=>a.id===investigationId.value))
function changeSource(){navigate('/after-sales/'+(section.value==='cases'?'workbench':section.value),{source:sourceFilter.value})}
function nextAction(a:Asset){return a.state==='ESCALATED'?'优先核实安全问题':a.state==='HANDLED'?'查看处理历史':a.state==='REVIEW_PENDING'?'审核建议并保存处理':!a.body.identity?'核实受影响商品':'查看事实和处理建议'}
function showHistory(){const el=document.getElementById('case-history');if(el instanceof HTMLDetailsElement)el.open=true;el?.scrollIntoView({behavior:'smooth'})}

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
function link(page:string,id?:string) { return href('/after-sales/'+page,{id,returnTo:returnTo.value || undefined,source:sourceFilter.value}) }
function open(page:string,id:string) { navigate('/after-sales/'+page,{id,returnTo:returnTo.value || undefined,source:sourceFilter.value}) }
function collection() { return section.value === 'experience' ? 'analyses' : section.value }
function status(a:Asset) { return stateNames[effectiveState(a)] || a.state }
function pretty(v:unknown) { return typeof v === 'string' ? v : JSON.stringify(v,null,2) }
const stages:Record<string,string>={draft:'草稿',requested:'申请',authorized:'曾授权',authorizedValid:'有效授权',received:'实收',refunded:'实际退款',cancelled:'取消'}
const aiReason=(reason:string)=>({INVALID_OUTPUT:'模型结果未通过证据校验，可先继续人工调查',B_MODEL_AUTHORIZATION_REQUIRED:'模型尚未启用',B_MODEL_ALLOWANCE_UNAVAILABLE:'本次模型额度不足，已保留原有事实',TIMEOUT:'模型响应超时，正在保留原始依据'} as Record<string,string>)[reason] || '本次模型结果不可用，已有事实保留'
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
    if(!route.value.query.id && section.value==='experience' && sourceFilter.value==='TEACHING' && latestReport.value){reportData.value=await get<Asset>('/analyses/'+latestReport.value.id)}
    if(route.value.query.id && ['cases','experience','risks'].includes(section.value)) {
      const a=await get<Asset>('/'+collection()+'/'+encodeURIComponent(route.value.query.id))
      if(run!==sequence || !alive.value)return
      current.value=a
      sourceFilter.value=a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'TEACHING':'ERP'
      if(a.kind==='REPORT')reportData.value=a
    }
    if(section.value==='risks' && route.value.query.investigation && run===sequence){
      const inv=index.investigation.items.find(a=>a.id===route.value.query.investigation)
      if(inv)await chooseInvestigation(inv)
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
  try{await action()}catch(e){note.value='';error.value=e instanceof Error && !(e instanceof ApiError) && e.message==='PENDING_COMMAND'?'请先核对上一笔结果不确定的操作。':e instanceof Error && !(e instanceof ApiError) && e.message.startsWith('TASK:')?'任务未完成：'+e.message.slice(5)+'，已保留已有事实和记录。':errorText(e)}finally{busy.value=false}
}
async function retry() { if(!pending.value)return;await perform(async()=>{const p=pending.value!;const result=await get<any>('/commands/'+p.key);pending.value=undefined;sessionStorage.removeItem('b-pending-command');await refresh();note.value='原命令已找到并核对。';if(result.result?.taskRef)taskId.value=result.result.taskRef.taskId}) }
async function mutate(collection:string,asset:Asset,action:string,data:unknown) {
  await command('/'+collection+'/'+asset.id+'/'+action,{expectedRevision:asset.revision,data});await refresh()
}
async function job(asset:Asset,collection:string,action:string,data:unknown={}) {
  activeTask.value=undefined
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
function metricFact(ref:string){const feedback=reportData.value?.body.feedback?.find((f:any)=>f.feedbackId===ref);if(feedback)return '客户反馈：'+feedback.text;const metrics=reportData.value?.body.metrics;if(!ref.startsWith('metric:') || !metrics)return ref;const [,id,index]=ref.split(':');const item=metrics.items.find((p:any)=>p.productId===id);const g=item?.groups[Number(index)];return g?`${item.name} · ${index==='0'?'上期':'本期'}实收退货 ${g.numerator} / 实发 ${g.denominator} 件，退货率 ${g.ratePercent ?? '未知'}%`:ref}
function prepareInvestigation(origin:Asset){investigationOpen.value=true;investigationText.value=origin.kind==='CASE'?(lastAdvice.value?.feedbackAI?.analysis.output?.hypotheses || []).join('；'):(origin.body.ai.output?.hypotheses || []).join('；');document.getElementById('investigation-start')?.scrollIntoView({behavior:'smooth'})}
function startProductInvestigation(value:{text:string;refs:string[];productId:string}){productFilter.value=value.productId;investigationText.value=value.text;chosenEvidence.value=value.refs;investigationOpen.value=true}
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
const availableEvidence=computed(()=>reportData.value?.body.feedback.filter((f:any)=>!productFilter.value || f.productId===productFilter.value).map((f:any)=>({id:f.feedbackId,text:f.text})) || current.value?.body.evidence?.facts.map((f:any)=>({id:f.id,text:factText(f)})) || [])
async function chooseInvestigation(a:Asset){investigationId.value=a.id;conclusion.value='OPEN';investigationText.value='';const o=a.body.origin;const origin=await get<Asset>('/'+(o.kind==='CASE'?'cases':'analyses')+'/'+o.id);limitations.value=origin.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'仅独立教学样本，不代表企业质量缺陷':'来源为教学 ERP 观察；原因与缺陷仍需人工调查，不代表已认证质量结论';investigationEvidence.value=o.kind==='CASE'?(origin.body.evidence?.facts || []).map((f:any)=>({id:f.id,text:factText(f)})):origin.body.feedback.map((f:any)=>({id:f.feedbackId,text:f.text}));chosenEvidence.value=(a.body.entries.at(-1)?.evidenceRefs || []).filter((id:string)=>investigationEvidence.value.some(f=>f.id===id))}
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
function viewInvestigation(id:string){navigate('/after-sales/risks',{source:sourceFilter.value,investigation:id})}
async function investigate(origin:Asset) {await perform(async()=>{const result=await command<Asset>('/investigations',{kind:origin.kind,id:origin.id,text:investigationText.value,evidenceRefs:chosenEvidence.value});investigationText.value='';investigationOpen.value=false;viewInvestigation(result.id);note.value='调查已建立，请核实证据并记录人工结论。'})}

async function createRisk() {await perform(async()=>{const identity=riskOptions.value[Number(riskOption.value)]?.identity;if(!identity)throw new Error('RISK_SCOPE_REQUIRED');const result=await command<Asset>('/risks',{investigationId:investigationId.value,reason:riskReason.value,limitations:limitations.value,identity,datasetId:riskDataset.value || null});riskRegister.value=false;investigationId.value='';open('risks',result.id);await refresh()})}
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
watch(()=>[route.value.path,route.value.query.id,route.value.query.source,route.value.query.investigation],()=>{if(route.value.query.source)sourceFilter.value=route.value.query.source;investigationOpen.value=false;classificationOpen.value=false;riskRegister.value=false;investigationId.value='';riskDecisionReason.value='';void refresh()})
</script>

<template>
  <div class="b-page">
    <a v-if="current?.kind==='CASE'" class="back" :href="link('workbench')">← 返回案件队列</a>
    <a v-if="returnTo" class="back" :href="'#'+returnTo">← 返回原补货页面</a>
    <header class="page-head"><div><span class="eyebrow">AFTER SALES / B V1.0</span><h1>{{title}}</h1><p class="subtitle">{{current?.kind==='CASE'?'客户问题、业务事实与人工决定分别留存。':section==='experience'?'优先找到异常商品、客户关心的问题和下一步处理方向。':section==='risks'?'围绕证据开展调查，由人工确认有效风险并提醒补货。':section==='materials'?'维护可追溯的政策与独立教学资料。':'从已有售后记录继续工作，优先处理需要判断和补证的事项。'}}</p></div><button class="button small" :disabled="busy || loading" @click="refresh">更新记录</button></header>
    <p v-if="error" class="banner danger" role="alert">{{error}}</p><p v-if="note" class="banner" role="status">{{note}}</p>
    <p v-if="pending && !busy" class="banner warning">上一操作结果待核对。<button class="button small" @click="retry">核对原命令</button></p>
    <p v-if="loading" role="status">正在读取当前记录…</p>
    <p v-if="activeTask && busy && !['SUCCEEDED','FAILED','CANCELLED'].includes(activeTask.state)" class="banner" role="status"><StatusBadge :value="activeTask.state" /> 正在{{activeTask.scenarioId.includes('EVIDENCE')?'核实商品与业务证据':activeTask.scenarioId.includes('ADVICE')?'检索政策并生成建议':'分析客户反馈'}}，完成后保存到历史。</p>
    <div v-if="!current && !route.query.id && section!=='materials'" class="b-scope"><span class="chip plain">{{sourceFilter==='ERP'?'本项目自建 ERP':'中台独立教学'}}</span><label>记录来源<select v-model="sourceFilter" @change="changeSource"><option value="ERP">本项目自建 ERP</option><option value="TEACHING">独立教学体验</option></select></label><small>{{sourceFilter==='ERP'?'与补货共用已登记范围，当前 '+(workspace?.trackedProducts ?? '—')+' 款商品；不跟踪其他 ERP 数据。':'独立教学资料与 ERP 分开使用，不混算业务指标。'}}</small></div>

    <template v-if="['workbench','cases'].includes(section) && !current && !route.query.id">
      <div class="b-workbench-grid"><div>
        <section class="panel b-queue"><div class="b-queue-tabs"><button v-for="q in queueItems" :key="q.key" :class="{active:queue===q.key}" @click="queue=q.key">{{q.name}} <small>{{scopedCases.filter(a=>inQueue(a,q.key)).length}}</small></button><button :class="{active:queue==='ALL'}" @click="queue='ALL'">全部</button></div>
          <div v-if="scopedCases.length || sourceFilter==='TEACHING'" class="b-search"><label>搜索售后记录<input v-model="caseSearch" placeholder="工单 / 订单 / 商品 / 问题"></label></div>
          <div v-if="scopedCases.length || sourceFilter==='TEACHING'" class="b-table-scroll"><table class="b-table"><thead><tr><th>售后问题 / 商品</th><th>来源 / 订单</th><th>处理状态 / 下一步</th></tr></thead><tbody><tr v-for="a in filteredCases" :key="a.id"><td><a :href="link('cases',a.id)">{{a.body.title}}</a><small>{{a.body.identity?.name || '商品待核实'}}<template v-if="a.body.identity"> · {{a.body.identity.sku}}</template></small></td><td><span class="chip plain">{{a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'独立教学':'自建 ERP'}}</span><small>{{a.body.erpStoreName || '教学店铺'}}</small><small>{{a.body.identity?.orderId==='UNKNOWN'?'订单待核实':a.body.identity?.orderId || a.body.orderId || '待关联订单'}}</small></td><td><span class="chip" :class="a.state==='ESCALATED'?'danger':'warning'">{{status(a)}}</span><small>{{nextAction(a)}}</small></td></tr></tbody></table></div>
          <SourceInbox v-if="sourceFilter==='ERP' && !scopedCases.length && workspace" :stores="workspace.sourceStores" :disabled="busy" embedded @open="openSource" />
          <div v-if="!filteredCases.length && (scopedCases.length || sourceFilter==='TEACHING')" class="b-empty"><b>{{queue==='HANDLED'?'暂无已处理记录':'当前队列暂无案件'}}</b><p>{{sourceFilter==='ERP'?'可从下方本项目 ERP 工单接入并处理。':'可查看其他队列或创建教学案件。'}}</p></div>
          <div class="b-queue-foot"><small>仅展示当前来源与授权范围</small><a v-if="sourceFilter==='TEACHING'" href="#" @click.prevent="newCase=!newCase">教学与异常演示</a></div>
        </section>
        <SourceInbox v-if="sourceFilter==='ERP' && scopedCases.length && workspace" :stores="workspace.sourceStores" :disabled="busy" @open="openSource" />
      </div><aside class="b-workbench-side">
        <section class="panel b-panel"><h2>退货异常提醒</h2><template v-if="sourceFilter==='TEACHING' && alerts.length"><article v-for="p in alerts" :key="p.productId"><h3>{{p.name}}</h3><p>本期退货率 {{p.groups[1].ratePercent}}%，较上期上升 {{p.deltaPercentagePoints}} 个百分点。</p><a class="button small" :href="link('experience',latestReport?.id)">查看异常分析 →</a></article></template><p v-else class="muted">{{sourceFilter==='ERP'?'当前自建 ERP 尚缺完整退货统计依据。可先查看客户反馈与问题商品。':'暂无已核实的退货异常报告。'}}</p></section>
        <section class="panel b-panel"><h2>商品评价与客户反馈</h2><p>从已关联商品的评价了解客户问题，再查看 AI 建议和原始证据。</p><a class="button small" :href="link('experience')">查看商品反馈 →</a></section>
        <section class="panel b-panel"><h2>质量风险协同</h2><p>{{scopedRisks.filter(r=>effectiveState(r)==='CONFIRMED').length}} 项当前有效提醒，{{scopedRisks.filter(r=>r.state==='SUSPECTED').length}} 项待人工确认。</p><a class="button small" :href="link('risks')">查看调查与风险 →</a></section>
      </aside></div>
      <form v-if="newCase && sourceFilter==='TEACHING'" class="panel b-panel b-form" @submit.prevent="source='TEACHING';createCase()"><h2>教学与异常演示</h2><div class="b-grid"><label>教学资料<select v-model="datasetId" required><option value="">选择已启用资料</option><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}}</option></select></label><label>订单<select v-model="orderId" required><option value="">选择资料内订单</option><option v-for="o in records.filter(r=>r.type==='order')" :key="o.id" :value="o.id">{{o.orderNumber}}</option></select></label></div><label>问题标题<input v-model="caseTitle" required></label><label>客户原话<textarea v-model="customer" required></textarea></label><details><summary>业务日期与适用范围</summary><label>业务日期<input v-model="businessDate"></label><label>地区<input v-model="caseRegion"></label><label>平台<input v-model="casePlatform"></label><label>语言<input v-model="caseLanguage"></label></details><button class="button primary" :disabled="busy">保存并核实事实</button></form>
    </template>

    <template v-if="current?.kind==='CASE'">
      <div class="b-case-meta"><span class="chip" :class="current.state==='ESCALATED'?'danger':'warning'">{{status(current)}}</span><span class="chip plain">{{current.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台独立教学':'本项目自建 ERP'}}</span><span>{{current.body.erpStoreName || '教学店铺'}}</span><span v-if="current.body.identity?.orderId && current.body.identity.orderId!=='UNKNOWN'">订单 {{current.body.identity.orderId}}</span><button class="button small" @click="showHistory()">查看处理历史</button></div>
      <p v-if="current.state==='ESCALATED'" class="banner danger">安全信号优先由人工核实处理，不等待 AI，不指导拆机。</p>
      <div class="b-case-grid">
        <section class="panel b-case-column"><h2>客户反馈了什么</h2><blockquote v-for="(m,i) in current.body.messages" :key="i"><small>{{m.source==='CLAIM'?'客户主张 · 人工补充':'ERP 反馈原文'}} · {{formatDate(m.at)}}</small><p>{{m.text}}</p><small v-if="m.attachmentRefs?.length">附件线索：{{m.attachmentRefs.join('、')}}</small></blockquote><p v-if="!current.body.messages.length" class="b-gap">ERP 仅提供工单标题，完整客户会话待补充。</p><details><summary>补充客户信息或内部记录</summary><form @submit.prevent="perform(async()=>{await mutate('cases',current!,'messages',{text:message,attachmentRefs:attachments.split(',').map(x=>x.trim()).filter(Boolean)});message='';attachments=''})"><label>客户消息<textarea v-model="message" required maxlength="6000"></textarea></label><label>附件线索（可选）<input v-model="attachments"></label><button class="button small" :disabled="busy || !message">追加消息</button></form></details></section>
        <section class="panel b-case-column"><div class="b-row"><h2>系统核实的业务事实</h2><button class="b-text-button" :disabled="busy" @click="perform(()=>job(current!,'cases','evidence-jobs'))">更新</button></div>
          <template v-if="current.body.identity"><div class="b-verified"><b>已核实关联商品</b><small>已利用来源订单或商品关联，无需重复选择。</small></div><dl class="b-fact-list"><div><dt>商品</dt><dd>{{current.body.identity.name}}</dd></div><div><dt>SKU</dt><dd>{{current.body.identity.sku}}</dd></div><div><dt>订单 / 明细</dt><dd>{{current.body.identity.orderId==='UNKNOWN'?'订单待核实':current.body.identity.orderId}} / {{current.body.identity.lineId}}</dd></div><div><dt>店铺 / 仓库</dt><dd>{{current.body.erpStoreName || '教学店铺'}} / {{current.body.identity.warehouseId==='UNKNOWN'?'待核实':current.body.identity.warehouseId}}</dd></div></dl></template><p v-else class="b-gap">商品关联尚未核实，请先确认本次问题对应的订单明细。</p>
          <details v-if="current.body.identity && identityCandidates.length"><summary>关联依据与人工纠正</summary><p>更正已有关系会保留原关联、操作者和原因。</p><form @submit.prevent="perform(async()=>{await mutate('cases',current!,'links',{lineId,reason:linkReason});lineId='';linkReason='';await job(current!,'cases','evidence-jobs')})"><label>纠正商品<select v-model="lineId" required><option value="">选择已核实的本单商品</option><option v-for="c in identityCandidates" :key="c.lineId" :value="c.lineId">{{c.name}} · {{c.sku}}</option></select></label><label>纠正原因<input v-model="linkReason" required></label><button class="button small" :disabled="busy">留痕纠正</button></form></details>
          <form v-else-if="identityCandidates.length" @submit.prevent="perform(async()=>{await mutate('cases',current!,'links',{lineId,reason:''});lineId='';await job(current!,'cases','evidence-jobs')})"><label>选择本订单受影响商品<select v-model="lineId" required><option value="">请选择本次问题商品</option><option v-for="c in identityCandidates" :key="c.lineId" :value="c.lineId">{{c.name}} · {{c.sku}}</option></select></label><button class="button small" :disabled="busy || !lineId">确认商品</button></form>
          <h3>交易与处理状态</h3><div v-for="f in (current.body.evidence?.facts || []).filter((f:any)=>f.domain!=='feedback')" :key="f.id" class="b-fact"><b>{{factNames[f.domain] || (f.domain==='shipment'?'实际发货':f.domain==='return'?'退货记录':f.domain==='order'?'订单事实':'业务事实')}}</b><p>{{factText(f)}}</p></div><p v-if="!current.body.evidence?.facts?.length" class="muted">尚无可用业务事实。</p><details v-if="current.body.evidence?.missing.length"><summary>待补证（{{current.body.evidence.missing.length}}）</summary><p v-for="gap in current.body.evidence.missing" :key="gap" class="b-gap">{{gap}}</p></details><details><summary>查看取证与来源明细</summary><p v-for="f in current.body.evidence?.facts" :key="f.id">{{f.sourceRef}} · {{formatDate(f.observedAt)}}</p></details>
        </section>
        <section class="panel b-case-column b-decision"><h2>AI 处理建议与人工审核</h2><small>重要决定由业务人员审核</small>
          <div v-if="lastAdvice?.ai.status==='AVAILABLE'" class="b-insight"><small>AI 建议</small><p>{{lastAdvice.ai.output.replyDraft}}</p></div>
          <template v-else-if="lastAdvice?.feedbackAI?.analysis.status==='AVAILABLE'"><div class="b-insight"><p v-for="line in lastAdvice.feedbackAI.analysis.output.hypotheses.slice(0,2)" :key="line">{{line}}</p></div><p v-for="line in lastAdvice.feedbackAI.analysis.output.nextSteps.slice(0,2)" :key="line">{{line}}</p></template>
          <p v-else class="muted">{{!workspace?.modelEnabled?'当前模型不可用，可继续人工核实和处理。':!lastAdvice?'结合客户反馈、业务事实与政策生成建议。':lastAdvice.ai.reason==='POLICY_NOT_APPLICABLE'?'缺少适用政策，可补证或记录人工处理。':aiReason(lastAdvice.ai.reason)}}</p>
          <details v-if="lastAdvice?.policies?.length"><summary>查看适用政策与原文</summary><article v-for="p in lastAdvice.policies" :key="p.policyId+p.sectionId"><b>{{p.title}}</b><p>{{p.text}}</p><small>政策版本 {{p.version}}</small></article></details>
          <button class="button primary" :disabled="busy || !current.body.identity || !current.body.evidence || !workspace?.modelEnabled" @click="perform(()=>job(current!,'cases','advice-jobs'))">{{lastAdvice?'重新生成建议':'生成处理建议'}}</button>
          <button v-if="lastAdvice?.ai.status==='AVAILABLE'" class="b-text-button" @click="humanText=lastAdvice.ai.output.replyDraft">使用草稿</button>
          <p v-if="lastAdvice && current.state!=='HANDLED' && lastAdvice.caseRevision!==current.revision" class="b-gap">案件已有更新，原建议须重新生成后才可采纳。</p>
          <label>人工回复稿<textarea v-model="humanText" maxlength="6000" placeholder="审核 AI 草稿或记录人工澄清"></textarea></label><label>审核 / 升级理由<input v-model="reviewReason" maxlength="1000" placeholder="说明本次处理依据"></label>
          <div class="button-row"><button v-for="d in [{key:'ACCEPT',label:'保存并采纳'},{key:'MANUAL',label:'保存人工处理'},{key:'RETURN',label:'退回修改'},{key:'ESCALATE',label:'升级人工'}]" :key="d.key" class="button small" :class="{primary:d.key==='ACCEPT'}" :disabled="busy || !humanText || !reviewReason || (d.key==='ACCEPT' && (lastAdvice?.ai.status!=='AVAILABLE' || lastAdvice?.caseRevision!==current.revision))" @click="perform(async()=>{await mutate('cases',current!,'reviews',{adviceVersion:lastAdvice?.version || null,text:humanText,reason:reviewReason,decision:d.key});humanText='';reviewReason=''})">{{d.label}}</button></div><small>人工决定仅保留为内部记录，不发送客户消息或执行退款。</small><details v-if="lastAdvice"><summary>AI 依据、待补材料与用量</summary><p v-for="g in lastAdvice.ai.output?.missingEvidence || []" :key="g">{{g}}</p><ModelUsage :ai="lastAdvice.ai" /><ModelUsage v-if="lastAdvice.feedbackAI" :ai="lastAdvice.feedbackAI.analysis" /></details><button class="b-text-button" @click="prepareInvestigation(current!)">需要进一步调查 →</button>
        </section>
      </div>
      <details id="case-history" class="panel b-panel"><summary>消息、关联与处理历史</summary><article v-for="(r,i) in current.body.reviews" :key="i" class="b-fact"><b>人工处理 · {{formatDate(r.at)}}</b><p>{{r.text}}</p><small>依据：{{r.reason}} · {{r.actor}}</small></article><article v-for="v in current.history" :key="v.version"><p>版本 {{v.version}} · {{formatDate(v.createdAt)}} · {{stateNames[v.body._state] || v.body._state}}</p><small v-if="v.body.linkHistory?.length">关联变更：{{v.body.linkHistory.at(-1).reason || '首次必要确认'}}</small></article></details>
    </template>

    <template v-if="section==='experience'">
      <template v-if="sourceFilter==='ERP'"><SourceInbox v-if="workspace" :stores="workspace.sourceStores" initial-kind="reviews" :disabled="busy" @open="openSource" /><p class="b-boundary">仅查看本项目自建商品的反馈。当前未取得完整的发货与实收退货总体，暂不提供 ERP 退货率。</p></template>
      <template v-else><div class="b-row"><small>独立教学资料 · {{reportData?.body.datasetVersion || '尚无已保存分析'}} · 不与 ERP 混算</small><button class="button small" @click="analysisSettings=!analysisSettings">{{analysisSettings?'收起分析范围':'调整分析范围 / 更新分析'}}</button></div>
        <section v-if="analysisSettings || !reportData" class="panel b-panel"><h2>分析范围</h2><div class="b-inline-form"><label>已启用资料<select v-model="selectedDataset"><option value="">选择资料</option><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</option></select></label><label class="b-check"><input v-model="analysisAI" type="checkbox" :disabled="!workspace?.modelEnabled">AI 主题与原因分析</label><button class="button primary" :disabled="busy || !selectedDataset" @click="analyze">更新分析</button></div><details><summary>观察范围与历史对比</summary><label>对比历史报告<select v-model="compareReport"><option value="">不比较</option><option v-for="r in all?.report.items" :key="r.id" :value="r.id">{{formatDate(r.body.createdAt)}} · {{r.body.datasetVersion}}</option></select></label><p v-for="(w,i) in datasets.find(d=>d.id===selectedDataset)?.body.manifest.windows || []" :key="i">{{i===0?'上期':'本期'}}：{{formatDate(w[0])}} 至 {{formatDate(w[1])}}</p><p>每期须满足完整观察期、至少20个订单商品及20件实发；本期实收至少3件且上升至少10个百分点才提示调查。</p></details><p v-if="!activeDatasets.length">请在知识与资料中启用已核验的独立教学资料。</p></section>
        <ProductExperience v-if="reportData" :report="reportData" :cases="assets" :busy="busy" @evidence="(id:string)=>perform(async()=>{selectedEvidence=await get('/analyses/'+reportData!.id+'/evidence/'+id)})" @investigate="startProductInvestigation" @correct="classificationOpen=true"><template #advanced><p v-if="reportData.body.comparison">历史对比：{{reportData.body.comparison.comparable?'口径一致，可查看原始件数差异':'口径不同，不能直接比较退货率'}}。</p></template></ProductExperience>
        <details class="panel b-panel"><summary>查看历史分析</summary><a v-for="r in all?.report.items" :key="r.id" class="b-list-row" :href="link('experience',r.id)"><span>{{formatDate(r.body.createdAt)}} · {{r.body.datasetVersion}}</span><span>{{r.body.metrics.items.filter((p:any)=>p.finding==='NEEDS_INVESTIGATION').length}} 项待调查</span></a></details>
      </template>
    </template>

    <template v-if="section==='risks'">
      <template v-if="current?.kind==='RISK'"><a :href="link('risks')" class="back">← 返回调查与风险</a><section class="panel b-panel"><div class="b-row"><h2>{{current.body.reason}}</h2><span class="chip warning">{{status(current)}}</span></div><p>{{current.body.limitations}}</p><dl class="b-fact-list"><div><dt>适用商品</dt><dd>{{current.body.identity.sku}}</dd></div><div><dt>适用店仓</dt><dd>{{current.body.identity.storeId}} / {{current.body.identity.warehouseMode==='ALL_STORE_WAREHOUSES'?'本店所有仓':current.body.identity.warehouseIds.join('、')}}</dd></div><div><dt>有效至</dt><dd>{{current.body.validUntil?formatDate(current.body.validUntil):'尚未人工确认'}}</dd></div></dl><div v-if="current.state==='SUSPECTED' || effectiveState(current)==='CONFIRMED'" class="b-risk-decision"><h3>{{current.state==='SUSPECTED'?'人工核实后确认提醒':'管理当前风险提醒'}}</h3><label>决定理由<input v-model="riskDecisionReason" required placeholder="记录核实依据或关闭、撤销原因"></label><label v-if="current.state==='SUSPECTED'">提醒有效至<input type="datetime-local" :value="new Date(validUntil).toLocaleString('sv-SE').slice(0,16).replace(' ','T')" @change="validUntil=new Date(($event.target as HTMLInputElement).value).toISOString()"></label><div class="button-row"><button v-for="d in (current.state==='SUSPECTED'?[{key:'CONFIRM',name:'确认风险并启用提醒'},{key:'REJECT',name:'驳回'}]:[{key:'CLOSE',name:'关闭'},{key:'REVOKE',name:'撤销'}])" :key="d.key" class="button" :class="{primary:d.key==='CONFIRM'}" :disabled="busy || !riskDecisionReason" @click="perform(()=>mutate('risks',current!,'decisions',{decision:d.key,reason:riskDecisionReason,validUntil:d.key==='CONFIRM'?validUntil:null}))">{{d.name}}</button></div></div><p class="b-boundary">{{current.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'独立教学风险需有效演示绑定才会在补货显示。':'确认后的有效风险在对应自建商品店仓提醒。'}} 原补货数量及采购规则继续适用。</p><details open><summary>调查来源与决定历史</summary><p v-for="entry in all?.investigation.items.find(a=>a.id===current!.body.investigationId)?.body.entries || []" :key="entry.at">{{entry.text}}</p><blockquote v-for="(d,i) in current.body.decisions" :key="i">{{d.reason}}<small>{{d.actor}} · {{formatDate(d.at)}}</small></blockquote><button class="button small" @click="perform(async()=>{const a=all!.investigation.items.find(a=>a.id===current!.body.investigationId);if(a){viewInvestigation(a.id)}})">查看关联调查</button></details></section></template>
      <template v-else><section class="panel b-panel"><div class="b-queue-tabs"><button v-for="q in [{key:'CURRENT',name:'疑似与有效提醒'},{key:'HISTORY',name:'已关闭 / 撤销 / 到期'},{key:'ALL',name:'全部'}]" :key="q.key" :class="{active:riskView===q.key}" @click="riskView=q.key">{{q.name}}</button></div><a v-for="a in filteredRisks" :key="a.id" class="b-list-row" :href="link('risks',a.id)"><div><b>{{a.body.reason}}</b><small>{{a.body.identity.sku}} · {{a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'独立教学':'自建 ERP 调查'}}</small></div><span class="chip warning">{{status(a)}}</span></a><p v-if="!filteredRisks.length" class="muted">当前来源下暂无适用风险。从案件或商品分析发起调查后，可在此跟进。</p></section>
        <section class="panel b-panel"><h2>待跟进调查</h2><article v-for="a in (all?.investigation.items || []).filter(a=>(a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'TEACHING':'ERP')===sourceFilter)" :key="a.id" class="b-fact"><div class="b-row"><div><b>{{a.body.entries[0].text}}</b><small>{{status(a)}} · {{formatDate(a.body.entries.at(-1).at)}}</small></div><button class="button small" :disabled="busy" @click="viewInvestigation(a.id)">继续调查</button></div></article></section>
        <section v-if="activeInvestigation" class="panel b-panel"><h2>{{activeInvestigation.body.entries[0].text}}</h2><a :href="link(activeInvestigation.body.origin.kind==='REPORT'?'experience':'cases',activeInvestigation.body.origin.id)">查看来源问题与证据 →</a><details><summary>调查记录</summary><p v-for="(e,i) in activeInvestigation.body.entries" :key="i">{{e.text}} · {{formatDate(e.at)}}</p></details><form class="b-form" @submit.prevent="perform(()=>mutate('investigations',activeInvestigation!,'entries',{text:investigationText,evidenceRefs:chosenEvidence,conclusion}))"><label>本次核实情况<textarea v-model="investigationText" required placeholder="记录已核事实、补证及下一步"></textarea></label><details><summary>选择可追溯证据（已选 {{chosenEvidence.length}} 条）</summary><label v-for="f in investigationEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></details><label>人工结论<select v-model="conclusion"><option value="OPEN">继续调查</option><option value="SUPPORTED">证据支持风险</option><option value="REJECTED">证据不支持</option><option value="NEEDS_EVIDENCE">需进一步补证</option></select></label><button class="button primary" :disabled="busy || (conclusion==='SUPPORTED' && !chosenEvidence.length)">保存调查结论</button></form><button v-if="activeInvestigation.state==='SUPPORTED' && !risks.some(r=>r.body.investigationId===activeInvestigation!.id)" class="button" :disabled="busy" @click="riskRegister=true;riskReason=activeInvestigation.body.entries[0].text">登记疑似风险</button><p v-else class="muted">{{risks.some(r=>r.body.investigationId===activeInvestigation!.id)?'此调查已有关联风险，请在上方查看。':'证据支持风险后，可明确范围并登记疑似风险。'}}</p></section>
        <form v-if="riskRegister && activeInvestigation" class="panel b-panel b-form" @submit.prevent="createRisk"><h2>确认本次风险线索范围</h2><label>问题与依据<textarea v-model="riskReason" required></textarea></label><label>尚未确认的事项<textarea v-model="limitations" required></textarea></label><label>本次涉及商品<select v-model="riskOption" required><option value="">选择调查内已核实商品</option><option v-for="(p,i) in riskOptions" :key="i" :value="String(i)">{{p.name}}</option></select></label><p v-if="!riskOptions.length" class="b-gap">来源尚缺明确商品或仓库，先回到案件核实。</p><button class="button primary" :disabled="busy || !riskOptions.length">保存疑似风险，继续人工确认</button></form>
      </template>
    </template>
    <template v-if="section==='materials'">
      <section class="panel b-panel"><div class="b-row"><h2>独立教学资料</h2><button class="button primary" :disabled="busy || datasets.some(d=>d.body.manifest.datasetId==='b-golden-20261116' && d.state!=='DRAFT')" @click="importPackage()">导入完整教学资料</button></div><p class="muted">40 张逻辑订单、每张 2 个商品，含实际发货、各退货阶段与反馈；资料存入中台，不创建 ERP 单据。</p><article v-for="d in datasets" :key="d.id" class="b-fact"><div class="b-row"><h3>{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</h3><span class="chip plain">{{status(d)}}</span></div><p v-for="issue in d.body.issues" :key="issue" class="banner danger">{{issue}}</p><p v-if="d.body.validation">已回读 {{d.body.validation.count}} 条事实 · {{d.body.validation.at}}</p><div class="button-row"><button v-if="['READBACK_VERIFIED','INACTIVE'].includes(d.state)" class="button primary" :disabled="busy" @click="perform(()=>mutate('datasets',d,'activate',{}))">启用资料</button><button v-if="d.state==='ACTIVE'" class="button" :disabled="busy" @click="perform(()=>mutate('datasets',d,'deactivate',{}))">停用资料</button><button v-if="d.state==='SEALED'" class="button" :disabled="busy" @click="perform(()=>job(d,'datasets','validation-jobs'))">校验并独立回读</button><button class="button" :disabled="busy" @click="perform(async()=>{await readRecords(d.id);note='已读取资料，可在下方核对原始教学事实。'})">核对资料</button></div></article><details><summary>导入其他版本 / 继续未完成导入</summary><p>选择包含 manifest 和 chunks 的独立教学 JSON 包。版本、数量、指纹与全部关联会在启用前校验；同版本草稿可断点继续，迟到数据必须新建版本。</p><input type="file" accept=".json" aria-label="教学资料文件" @change="importFile=($event.target as HTMLInputElement).files?.[0]"><button class="button" :disabled="busy || !importFile" @click="importLocalPackage">导入并核对资料版本</button></details><details v-if="records.length"><summary>教学事实与证据（{{records.length}}条）</summary><article v-for="r in records" :key="r.id" class="b-fact"><p>{{factText(r)}}</p><small>资料记录 {{r.id}}</small></article></details></section>
      <section class="panel b-panel"><div class="b-row"><h2>政策知识</h2><button class="button" :disabled="busy || !!all?.policy.items.length" @click="importPolicyDrafts">准备四类教学政策草稿</button></div><p class="muted">草稿不能检索。请核对正文、适用范围及有效期，再明确发布；不代表企业正式政策。</p><article v-for="p in all?.policy.items" :key="p.id" class="b-fact"><div class="b-row"><h3>{{p.body.title}}</h3><span class="chip plain">{{status(p)}}</span></div><p v-for="s in p.body.sections" :key="s.id">{{s.text}}</p><p class="muted">{{p.body.category==='ALL'?'全部已声明类目':p.body.category}} / {{p.body.region}} / {{p.body.platform}} / {{p.body.language}} · {{p.body.effectiveFrom}} — {{p.body.effectiveUntil}}</p><div class="button-row"><button v-if="p.state==='DRAFT'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'submit-review',{}))">提交政策审核</button><button v-if="p.state==='IN_REVIEW'" class="button primary" :disabled="busy" @click="perform(()=>mutate('policies',p,'publish',{reason:'本人核对上述教学政策正文及适用范围后明确发布'}))">确认并发布此政策</button><button v-if="p.state==='PUBLISHED'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'revoke',{reason:'本人明确撤销此政策的后续使用'}))">撤销政策</button><button class="button" :disabled="busy" @click="editingPolicy=p.id;policyRevisionText=p.body.sections.map((s:any)=>s.text).join('\n\n')">修订并新建草稿版本</button></div><form v-if="editingPolicy===p.id" @submit.prevent="editPolicy(p)"><label>修订正文<textarea v-model="policyRevisionText" required maxlength="4000"></textarea></label><p>原版本及引用保留，新版本须重新审核发布。</p><button class="button" :disabled="busy">保存新版本</button></form></article><details><summary>录入新政策</summary><form class="b-form" @submit.prevent="createPolicy"><label>政策标题<input v-model="policyTitle" required></label><label>正文<textarea v-model="policyText" required></textarea></label><div class="b-grid"><label>类目<select v-model="policyCategory"><option value="APPAREL">服装</option><option value="ELECTRONICS">电子产品</option><option value="ALL">两类均适用</option></select></label><label>地区<input v-model="policyRegion" required></label><label>平台<input v-model="policyPlatform" required></label><label>语言<input v-model="policyLanguage" required></label></div><button class="button" :disabled="busy">保存待审核草稿</button></form></details></section>
      <details class="panel b-panel"><summary>教学风险与 ERP 商品的受控演示绑定</summary><p>需有管理权限。绑定由独立 ERP 回读核对真实商品和仓库，范围精确到当前用户、资料版本、店仓和有效期；不改变补货算法。</p><form class="b-form" @submit.prevent="bind"><label>教学版本<select v-model="bindingDataset" required><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}}</option></select></label><label>教学商品<select v-model="bindingProduct" required><option value="">选择资料内商品</option><option v-for="p in bindingProducts" :key="p.id" :value="p.id">{{p.name}} · {{p.sku}}</option></select></label><label>目标 ERP 店铺<select v-model="erpStore"><option v-for="s in workspace?.sourceStores" :key="s">{{s}}</option></select></label><label>目标 ERP 商品 SKU<input v-model="bindingSku" required placeholder="输入已获准商品 SKU 后核实"></label><button class="button" type="button" :disabled="busy || !bindingDataset || !bindingSku" @click="findMapping">查找已核实的商品与仓库</button><label>目标商品与仓库<select v-model="mappingChoice" required><option value="">从 ERP 已核实结果中选择</option><option v-for="(p,i) in mappingOptions" :key="i" :value="String(i)">{{p.name}}</option></select></label><label>有效至<input type="datetime-local" :value="new Date(validUntil).toLocaleString('sv-SE').slice(0,16).replace(' ','T')" @change="validUntil=new Date(($event.target as HTMLInputElement).value).toISOString()" required></label><button class="button" :disabled="busy">独立核实并建立演示绑定</button></form><article v-for="b in all?.binding.items" :key="b.id"><p>{{b.body.teachingIdentity.sku}} → {{b.body.erpIdentity.sku}} · {{status(b)}} · {{b.body.validUntil}}</p><button v-if="b.state==='ACTIVE'" class="button" :disabled="busy" @click="perform(()=>mutate('teaching-bindings',b,'revoke',{reason:'人工撤销教学演示绑定'}))">撤销绑定</button></article></details>
    </template>

    <Modal v-if="investigationOpen" title="发起人工调查" @close="investigationOpen=false"><form class="b-form" @submit.prevent="investigate((reportData || current)!)"><label>需要调查的问题<textarea v-model="investigationText" required></textarea></label><fieldset><legend>本次调查依据</legend><label v-for="f in availableEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></fieldset><button class="button primary" :disabled="busy || !chosenEvidence.length">保存调查</button></form></Modal>
    <Modal v-if="classificationOpen && reportData" title="修订反馈主题" @close="classificationOpen=false"><form class="b-form" @submit.prevent="perform(async()=>{await mutate('analyses',reportData!,'classifications',{feedbackId,labels:selectedLabels,span,reason:correctionReason});classificationOpen=false})"><label>反馈<select v-model="feedbackId" required><option value="">选择原文</option><option v-for="f in effectiveClassifications" :key="f.feedbackId" :value="f.feedbackId">{{f.text}}</option></select></label><fieldset><legend>反馈主题（可多选）</legend><label v-for="(name,code) in labelNames" :key="code" class="b-check"><input v-model="selectedLabels" type="checkbox" :value="code">{{name}}</label></fieldset><label>对应原文片段<input v-model="span" required></label><label>修订原因<input v-model="correctionReason" required></label><button class="button primary" :disabled="busy">留痕保存分类</button></form></Modal>
    <Modal v-if="selectedEvidence" title="原始业务依据" @close="selectedEvidence=undefined"><p>{{selectedEvidence.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台独立教学资料':'ERP 只读事实'}} · {{selectedEvidence.datasetVersion}}</p><p>{{factText(selectedEvidence.record)}}</p><details><summary>证据定位与校验</summary><p>{{selectedEvidence.record?.id}}</p><small>{{selectedEvidence.hash}}</small></details></Modal>
    <section v-if="all && ['workbench','cases','experience','risks'].includes(section)" class="b-tasks"><details><summary>后台任务与恢复</summary><p v-if="taskId">当前任务 {{taskId}}</p><button class="button" :disabled="busy" @click="perform(async()=>{const tasks=await get<any>('/tasks?workspaceId=after-sales-v1');backgroundTasks=tasks.items})">查询任务历史</button><div v-for="t in backgroundTasks" :key="t.taskRef.taskId" class="b-list-row"><span>{{t.scenarioId.includes('CASE')?'售后处理':t.scenarioId.includes('EXPERIENCE')?'体验分析':'资料核验'}} · {{t.state==='SUCCEEDED'?'已完成':t.state==='FAILED'?'需处理':t.state==='RUNNING'?'处理中':'等待处理'}}</span><button v-if="t.state==='SUCCEEDED'" class="button small" :disabled="busy" @click="perform(async()=>{const r=await request<any>('/analysis-tasks/'+t.taskRef.taskId+'/report');if(['CASE','REPORT','RISK'].includes(r.analysisReport.domainKind))open(r.analysisReport.domainKind==='CASE'?'cases':r.analysisReport.domainKind==='REPORT'?'experience':'risks',r.analysisReport.domainRef.id);else note='资料任务已完成，请在政策与资料查看。'})">查看结果</button><span v-if="t.errorCode">{{t.errorCode}}</span></div></details></section>
  </div>
</template>

<style scoped>
.b-page{max-width:1360px;margin:auto;color:#243b4b}.b-page h1{font-size:27px}.b-page .page-head{margin-bottom:22px}.b-page .subtitle{font-size:13px;color:#71818b;line-height:1.8;margin:10px 0 0}.b-page h2{font-size:17px;margin:0 0 18px}.b-page h3{font-size:14px;margin:20px 0 10px}.b-page p{line-height:1.8;font-size:14px}.b-page small{font-size:12px;color:#71818b;line-height:1.7}.b-panel{padding:21px;margin:20px 0}.b-row{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}.b-row h2{margin:0}.b-scope{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0 22px}.b-scope label{display:flex!important;align-items:center;font-size:12px;margin:0!important}.b-scope select{width:auto!important;font-size:12px!important;padding:7px!important}.b-workbench-grid{display:grid;grid-template-columns:minmax(0,1fr) 285px;gap:20px;align-items:start}.b-workbench-grid>div{min-width:0}.b-workbench-side .b-panel{margin-top:0}.b-workbench-side h2{font-size:16px}.b-workbench-side p{font-size:13px}.b-queue{overflow:hidden}.b-queue-tabs{display:flex;gap:6px;border-bottom:1px solid #e1e8ec;padding:0 16px;overflow:auto}.b-queue-tabs button{border:0;border-bottom:2px solid transparent;padding:16px 8px;background:none;font:inherit;font-size:13px;white-space:nowrap;color:#71818b;cursor:pointer}.b-queue-tabs button.active{color:#116d66;border-color:#116d66;font-weight:600}.b-queue-tabs small{background:#f0f3f5;padding:1px 4px;margin-left:4px}.b-search{padding:0 18px;border-bottom:1px solid #e1e8ec}.b-search label{display:flex!important;align-items:center;gap:12px!important}.b-search input{max-width:320px}.b-table-scroll{overflow:auto}.b-table{width:100%;text-align:left;border-collapse:collapse;font-size:13px}.b-table th{background:#f8fafb;padding:13px 16px;font-weight:500;color:#71818b;font-size:12px}.b-table td{padding:20px 16px;border-bottom:1px solid #e6ecef;vertical-align:top}.b-table a{color:#126c66;font-weight:600}.b-table small{display:block;margin-top:6px}.b-queue-foot{display:flex;justify-content:space-between;padding:14px 18px;font-size:12px}.b-empty{text-align:center;padding:42px 18px;color:#71818b}.b-empty b{font-size:14px}.b-case-meta{display:flex;align-items:center;gap:10px;font-size:12px;margin:12px 0 22px;flex-wrap:wrap}.b-case-meta>.button{margin-left:auto}.b-case-grid{display:grid;grid-template-columns:minmax(0,.85fr) minmax(0,1fr) minmax(0,1.1fr);align-items:start;gap:16px}.b-case-grid>.panel{margin:0}.b-case-column{padding:20px;min-width:0}.b-case-column>h2,.b-case-column>.b-row{padding-bottom:18px;border-bottom:1px solid #e2e9ed;margin-bottom:18px}.b-case-column blockquote{background:#f6f8fa;border-left:0;padding:13px;margin:0 0 12px;overflow-wrap:anywhere}.b-case-column blockquote p{font-size:13px;margin:8px 0 0}.b-case-column details{margin:18px 0}.b-verified{padding:12px;background:#edf6ef;border:1px solid #c5decf;border-left:3px solid #317a5b;font-size:13px}.b-verified small{display:block;margin-top:4px}.b-fact-list{font-size:12px;margin:16px 0}.b-fact-list>div{display:flex;justify-content:space-between;gap:12px;padding:12px 0;border-bottom:1px solid #e5ebef}.b-fact-list dt{color:#71818b;flex-shrink:0}.b-fact-list dd{margin:0;text-align:right;overflow-wrap:anywhere}.b-fact{padding:12px 0;border-bottom:1px solid #e6ecef;font-size:13px}.b-fact p{font-size:13px;margin:6px 0}.b-fact small,.b-list-row small{display:block}.b-insight{background:#f1f7f4;border-left:3px solid #99beb1;padding:12px 14px;margin:16px 0}.b-insight p{font-size:14px;margin:4px 0}.b-text-button{border:0;background:none;padding:6px 0;font:inherit;font-size:12px;color:#126c66;cursor:pointer}.b-text-button:disabled{opacity:.4}.b-decision>.b-text-button{margin:0 12px 0 0}.b-decision textarea{min-height:110px}.b-gap{font-size:12px!important;border-left:3px solid #c7a65e;padding-left:10px;color:#82652d}.b-boundary{font-size:12px!important;color:#71818b;margin:18px 0}.b-form{display:grid;gap:12px}.b-page label{display:grid;gap:7px;margin:12px 0;color:#425f70;font-size:13px}.b-page input,.b-page select,.b-page textarea{border:1px solid #cbd7de;border-radius:5px;padding:9px 10px;width:100%;font:inherit;color:#243b4b;background:white;min-width:0}.b-page textarea{resize:vertical;min-height:85px}.b-check{display:flex!important;align-items:center;gap:8px}.b-check input{width:auto}.b-page fieldset{border:1px solid #dce4e9}.b-page summary{cursor:pointer;color:#37666c;font-size:12px}.b-page details{margin:18px 0}.b-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.b-inline-form{display:flex;align-items:end;gap:14px;flex-wrap:wrap}.b-inline-form label{flex:1;min-width:180px}.b-list-row{display:flex;justify-content:space-between;gap:16px;padding:16px 0;border-bottom:1px solid #e5ebef;color:inherit;font-size:13px}.b-risk-decision{max-width:600px}.b-tasks{font-size:12px;color:#71818b;margin-top:22px}.b-page .banner{font-size:13px;overflow-wrap:anywhere}.b-page .button:disabled{opacity:.5}.b-page .back{font-size:12px;margin-bottom:12px;display:inline-block}
@media(max-width:1150px){.b-workbench-grid{grid-template-columns:minmax(0,1fr) 250px}.b-case-grid{grid-template-columns:1fr 1fr}.b-case-column:first-child{grid-column:1/-1}.b-case-column:first-child blockquote{max-width:100%}.b-case-column{padding:18px}}
@media(max-width:800px){.b-workbench-grid,.b-case-grid,.b-grid{grid-template-columns:1fr}.b-case-column:first-child{grid-column:auto}.b-workbench-side{display:grid;gap:14px;grid-template-columns:1fr}.b-scope small{flex-basis:100%}.b-case-meta>.button{margin-left:0}.b-panel{padding:18px}.b-page h1{font-size:23px}}
</style>
