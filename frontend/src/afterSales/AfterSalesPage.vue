<script setup lang="ts">
import CaseWorkspace from './CaseWorkspace.vue'
import ServiceDesk from './ServiceDesk.vue'
import CaseProducts from './CaseProducts.vue'
import { adviceResult, reviewData, storeLabel } from './presentation'
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
const starterScope=ref(route.value.query.scope || 'TEACHING')
const policySearch=ref(''),policyManage=ref(false),draftCaseId=ref(''),draftBaseline=ref('')
const visiblePolicies=computed(()=>(all.value?.policy.items || []).filter(p=>!policySearch.value || [p.body.title,...p.body.sections.map((s:any)=>s.text)].some(t=>t.includes(policySearch.value))))
const title = computed(() => current.value?.kind==='CASE'?'售后处理':section.value==='experience'?'客户体验与退货分析':tabs.find(t => t.key === section.value)?.name || '售后工作台')
const activeTask=ref<any>(),riskView=ref('CURRENT')
const filteredRisks=computed(()=>scopedRisks.value.filter(a=>riskView.value==='ALL' || riskView.value==='CURRENT' && ['SUSPECTED','CONFIRMED'].includes(effectiveState(a)) || riskView.value==='HISTORY' && !['SUSPECTED','CONFIRMED'].includes(effectiveState(a))))
const queue=ref('TODO'),caseSearch=ref(''),sourceFilter=ref(route.value.query.source || 'ERP'),productFilter=ref(''),selectedLabels=ref<string[]>(['UNKNOWN'])
const scopedCases=computed(()=>assets.value.filter(a=>(a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'TEACHING':'ERP')===sourceFilter.value))
const queueItems=[{key:'TODO',name:'待处理'},{key:'EVIDENCE_PENDING',name:'待补证'},{key:'REVIEW_PENDING',name:'待确认'},{key:'HANDLED',name:'已处理'}]
function inQueue(a:Asset,key:string){return key==='ALL' || key==='TODO' && ['OPEN','ESCALATED','EVIDENCE_PENDING','NEEDS_CLARIFICATION','REVIEW_PENDING'].includes(a.state) || key==='EVIDENCE_PENDING' && ['EVIDENCE_PENDING','NEEDS_CLARIFICATION'].includes(a.state) || a.state===key}
const filteredCases=computed(()=>scopedCases.value.filter(a=>inQueue(a,queue.value) && (!caseSearch.value || [a.body.title,a.body.identity?.name,a.body.identity?.sku,a.body.orderId,a.body.erpTicketId].some(v=>v?.includes(caseSearch.value)))).sort((a,b)=>Number(b.state==='ESCALATED')-Number(a.state==='ESCALATED')))
const scopedRisks=computed(()=>risks.value.filter(a=>(a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'TEACHING':'ERP')===sourceFilter.value))
const scopedInvestigations=computed(()=>(all.value?.investigation.items || []).filter(a=>(a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'TEACHING':'ERP')===sourceFilter.value))
const latestReport=computed(()=>all.value?.report.items.find(r=>activeDatasets.value.some(d=>d.id===r.body.datasetId)))
const alerts=computed(()=>latestReport.value?.body.metrics.items.filter((p:any)=>p.finding==='NEEDS_INVESTIGATION') || [])
const investigationOpen=ref(false), classificationOpen=ref(false), analysisSettings=ref(false), riskRegister=ref(false)
const activeInvestigation=computed(()=>all.value?.investigation.items.find(a=>a.id===investigationId.value))
function changeSource(){navigate('/after-sales/'+(section.value==='cases'?'workbench':section.value),{source:sourceFilter.value})}
function nextAction(a:Asset){return a.state==='ESCALATED'?'优先核实安全问题':a.state==='HANDLED'?'查看处理历史':a.state==='REVIEW_PENDING'?'核对回复并确认':!a.body.identity?'核实受影响商品':'查看事实和处理建议'}
function showHistory(){const el=document.getElementById('case-history');if(el instanceof HTMLDetailsElement)el.open=true;el?.scrollIntoView({behavior:'smooth'})}

const newCase = ref(false), customer = ref(''), caseTitle = ref(''), datasetId = ref(''), orderId = ref(''), businessDate = ref('2026-09-05T00:00:00Z')
const source = ref('TEACHING'), erpStore = ref(''), ticketId = ref(''), casePlatform = ref('TEACHING'), caseRegion = ref('CN'), caseLanguage = ref('zh')
const records = ref<Record<string, any>[]>([]), lineId = ref(''), linkReason = ref(''), message = ref(''), humanText = ref(''), reviewReason = ref('')
const selectedDataset = ref(''), reportData = ref<Asset>(), feedbackId = ref(''), labels = ref('UNKNOWN'), span = ref(''), correctionReason = ref('')
const investigationText = ref(''), investigationId = ref(''), evidenceRefs = ref(''), conclusion = ref('OPEN')
const riskReason = ref(''), limitations = ref('问题原因及影响范围仍待核实'), riskDataset = ref(''), riskDecisionReason = ref('')
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
      const confirmation=a.body.confirmation
      if(confirmation && ['PREPARED','SENDING','PENDING'].includes(confirmation.status)){pending.value={path:'/cases/'+a.id+'/reviews',key:confirmation.key};sessionStorage.setItem('b-pending-command',JSON.stringify(pending.value))}
      if(a.kind==='CASE' && draftCaseId.value!==a.id){draftCaseId.value=a.id;humanText.value=a.body.reviews.at(-1)?.text || (a.body.advice.at(-1)?.ai.status==='AVAILABLE'?a.body.advice.at(-1).ai.output.replyDraft:'');draftBaseline.value=a.body.reviews.at(-1)?.text || ''}
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
async function refreshOnEntry(){
  await refresh()
  if(current.value?.kind==='CASE' && current.value.sourceNature==='TEACHING_ERP_OBSERVED' && current.value.state!=='HANDLED' && !['PREPARED','SENDING','PENDING'].includes(current.value.body.confirmation?.status) && !busy.value)
    await perform(()=>job(current.value!,'cases','evidence-jobs'))
}
async function command<T>(path:string,body:unknown):Promise<T> {
  if(pending.value)throw new Error('PENDING_COMMAND')
  const value={path,body,key:crypto.randomUUID()};pending.value=value
  sessionStorage.setItem('b-pending-command',JSON.stringify({path:value.path,key:value.key}))
  try{const result=await post<T>(path,body,value.key);if((result as any)?.handlingStatus!=='PENDING'){pending.value=undefined;sessionStorage.removeItem('b-pending-command')}return result}
  catch(e){if(e instanceof ApiError){pending.value=undefined;sessionStorage.removeItem('b-pending-command')}throw e}
}
async function perform(action:()=>Promise<void>) {
  if(busy.value)return
  busy.value=true;error.value='';note.value=''
  try{await action()}catch(e){note.value='';error.value=e instanceof Error && !(e instanceof ApiError) && e.message==='PENDING_COMMAND'?'请先核对上一笔结果不确定的操作。':e instanceof Error && !(e instanceof ApiError) && e.message.startsWith('TASK:')?'任务未完成：'+e.message.slice(5)+'，已保留已有事实和记录。':errorText(e)}finally{busy.value=false}
}
async function retry() { if(!pending.value)return;await perform(async()=>{const p=pending.value!;const result=await request<any>('/commands/'+p.key,{},undefined,60000,'/api/b/v1');if(result.result?.handlingStatus!=='PENDING'){pending.value=undefined;sessionStorage.removeItem('b-pending-command')}await refresh();note.value=result.result?.handlingStatus==='PENDING'?'ERP 保存结果仍待核验。':result.result?.handlingStatus==='REJECTED'?'ERP 未接受本次处理，请更新记录后重新确认。':'处理结果已核对。';if(result.result?.taskRef)taskId.value=result.result.taskRef.taskId}) }
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
async function job(asset:Asset,collection:string,action:string,data:unknown={}) {
  activeTask.value=undefined
  note.value=action==='advice-jobs'?'正在生成 AI 回复…':'正在核实资料…'
  const accepted=await command<{ taskRef:{taskId:string} }>('/'+collection+'/'+asset.id+'/'+action,{expectedRevision:asset.revision,data})
  taskId.value=accepted.taskRef.taskId
  const ownTask=accepted.taskRef.taskId, ownRoute=route.value.path+'?'+(route.value.query.id || '')
  // Task survives leaving this page. Re-open through history to continue reading.
  for(let attempt=0;attempt<300 && alive.value;attempt++) {
    const task=await request<any>('/analysis-tasks/'+ownTask)
    if(ownTask===taskId.value)activeTask.value=task
    if(task.state==='SUCCEEDED') {
      const report=await request<any>('/analysis-tasks/'+ownTask+'/report')
      if(ownRoute!==route.value.path+'?'+(route.value.query.id || ''))return
      if(report.analysisReport.domainKind==='REPORT')open('experience',report.analysisReport.domainRef.id)
      await refresh()
      if(action==='advice-jobs'){note.value=adviceResult(current.value);if(current.value?.body.advice.at(-1)?.ai.status==='AVAILABLE'){if(!humanText.value || humanText.value===asset.body.advice.at(-1)?.ai.output?.replyDraft)humanText.value=current.value.body.advice.at(-1).ai.output.replyDraft;else note.value='AI 回复已生成，当前编辑稿已保留，可查看并使用新草稿。'}}
      else note.value=action==='evidence-jobs'?(current.value?.body.evidence?.latestUnverified?'订单资料未更新成功，请稍后重试。':'订单资料已更新。'):'分析已保存。'
      return
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
  if(existing){open('cases',existing.id);const saved=await get<Asset>('/cases/'+existing.id);await job(saved,'cases','evidence-jobs');return}
  const created=await command<Asset>('/cases',{title:record.title || '客户反馈',message:'',region:'UNKNOWN',platform:'UNKNOWN',language:'zh',erpStoreName:record.storeName,erpTicketId,erpVoiceId,erpVoiceKind:erpVoiceId?record.kind:null})
  open('cases',created.id);const saved=await get<Asset>('/cases/'+created.id);await job(saved,'cases','evidence-jobs')
})}
function formatDate(value:any){return value?new Date(value).toLocaleString('zh-CN',{hour12:false}):'未提供'}
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
async function chooseInvestigation(a:Asset){investigationId.value=a.id;conclusion.value='OPEN';investigationText.value='';const o=a.body.origin;const origin=await get<Asset>('/'+(o.kind==='CASE'?'cases':'analyses')+'/'+o.id);limitations.value='问题原因及影响范围仍待核实';investigationEvidence.value=o.kind==='CASE'?(origin.body.evidence?.facts || []).map((f:any)=>({id:f.id,text:factText(f)})):origin.body.feedback.map((f:any)=>({id:f.feedbackId,text:f.text}));chosenEvidence.value=(a.body.entries.at(-1)?.evidenceRefs || []).filter((id:string)=>investigationEvidence.value.some(f=>f.id===id))}
async function importPolicyDrafts() {await perform(async()=>{const path='/policy-starters'+(starterScope.value==='AMAZON'?'?region=US&platform=Amazon':'');for(const p of await get<any[]>(path)){if(!all.value?.policy.items.some(a=>a.body.title===p.title && a.body.region===p.region && a.body.platform===p.platform && JSON.stringify(a.body.sections)===JSON.stringify(p.sections)))await command('/policies',p)}await refresh();note.value='政策草稿已准备。'})}
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
function warnDraft(event:BeforeUnloadEvent){if((humanText.value && humanText.value!==draftBaseline.value) || message.value){event.preventDefault();event.returnValue=''}}
function guardDraft(event:MouseEvent){const anchor=(event.target as Element)?.closest('a');if(anchor && anchor.hash!==location.hash && ((humanText.value && humanText.value!==draftBaseline.value) || message.value) && !confirm('人工处理稿或补充消息尚未保存。确认离开并放弃未保存内容？')){event.preventDefault();event.stopImmediatePropagation()}}
onMounted(()=>{window.addEventListener('beforeunload',warnDraft);document.addEventListener('click',guardDraft,true)})
onBeforeUnmount(()=>{window.removeEventListener('beforeunload',warnDraft);document.removeEventListener('click',guardDraft,true)})
watch(()=>route.value.query.id,(id,previous)=>{if(id!==previous){humanText.value='';reviewReason.value='';message.value='';attachments.value='';productFilter.value=''}})
onMounted(()=>{try{const saved=sessionStorage.getItem('b-pending-command');if(saved)pending.value=JSON.parse(saved)}catch{};void refreshOnEntry()})
onBeforeUnmount(()=>{alive.value=false;sequence++})
watch(()=>[route.value.path,route.value.query.id,route.value.query.source,route.value.query.investigation],()=>{if(route.value.query.source)sourceFilter.value=route.value.query.source;investigationOpen.value=false;classificationOpen.value=false;riskRegister.value=false;investigationId.value='';riskDecisionReason.value='';void refreshOnEntry()})
</script>

<template>
  <div class="b-page">
    <a v-if="current?.kind==='CASE'" class="back" :href="link('workbench')">← 返回案件队列</a>
    <a v-if="returnTo" class="back" :href="'#'+returnTo">← 返回原补货页面</a>
    <header class="page-head"><div><h1>{{title}}</h1></div><button v-if="current?.state!=='HANDLED' && !pending" class="button small" :disabled="busy || loading" @click="current?.kind==='CASE'?perform(()=>job(current!,'cases','evidence-jobs')):refresh()">更新记录</button></header>
    <p v-if="error" class="banner danger" role="alert">{{error}}</p><p v-if="note" class="banner" role="status">{{note}}</p>
    <p v-if="pending && !busy" class="banner warning">保存结果待核验。<button class="button small" @click="retry">核对处理结果</button></p>
    <p v-if="loading" role="status">正在读取当前记录…</p>

    <div v-if="!current && !route.query.id && section!=='materials'" class="b-scope"><label>记录来源<select v-model="sourceFilter" @change="changeSource"><option value="ERP">已接入店铺</option><option value="TEACHING">独立教学资料</option></select></label></div>

    <template v-if="['workbench','cases'].includes(section) && !current && !route.query.id">
      <ServiceDesk v-if="sourceFilter==='ERP' && workspace" :workspace="workspace" :cases="scopedCases" :cases-complete="!all?.case.nextCursor" :disabled="busy" @more="more('case','cases')" @open="openSource" @case="id=>open('cases',id)" />
      <div v-if="sourceFilter==='TEACHING'" class="b-workbench-grid"><div>
        <section class="panel b-queue"><div class="b-queue-tabs"><button v-for="q in queueItems" :key="q.key" :class="{active:queue===q.key}" @click="queue=q.key">{{q.name}} <small>{{scopedCases.filter(a=>inQueue(a,q.key)).length}}</small></button><button :class="{active:queue==='ALL'}" @click="queue='ALL'">全部</button></div>
          <div v-if="scopedCases.length || sourceFilter==='TEACHING'" class="b-search"><label>搜索售后记录<input v-model="caseSearch" placeholder="工单 / 订单 / 商品 / 问题"></label></div>
          <div v-if="scopedCases.length || sourceFilter==='TEACHING'" class="b-table-scroll"><table class="b-table"><thead><tr><th>售后问题 / 商品</th><th>来源 / 订单</th><th>处理状态 / 下一步</th></tr></thead><tbody><tr v-for="a in filteredCases" :key="a.id"><td><a :href="link('cases',a.id)">{{a.body.title}}</a><small>{{a.body.identity?.name || '商品待核实'}}<template v-if="a.body.identity"> · {{a.body.identity.sku}}</template></small></td><td><span class="chip plain">{{a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'独立教学':'自建 ERP'}}</span><small>{{storeLabel(a.body.erpStoreName)}}</small><small>{{a.body.identity?.orderId==='UNKNOWN'?'订单待核实':a.body.identity?.orderId || a.body.orderId || '待关联订单'}}</small></td><td><span class="chip" :class="a.state==='ESCALATED'?'danger':'warning'">{{status(a)}}</span><small>{{nextAction(a)}}</small></td></tr></tbody></table></div>
          <div v-if="!filteredCases.length && (scopedCases.length || sourceFilter==='TEACHING')" class="b-empty"><b>{{queue==='HANDLED'?'暂无已处理记录':'当前队列暂无案件'}}</b><p>可查看其他队列或接入新问题。</p></div>
          <div class="b-queue-foot"><small>{{filteredCases.length}} 条记录</small><a v-if="sourceFilter==='TEACHING'" href="#" @click.prevent="newCase=!newCase">教学与异常演示</a></div>
        </section>
      </div><aside class="b-workbench-side">
        <section class="panel b-panel"><h2>商品问题</h2><p v-if="sourceFilter==='TEACHING' && alerts.length">{{alerts.length}} 款商品退货异常</p><p v-else>{{scopedCases.length}} 条售后记录</p><a class="button small" :href="link('experience')">查看商品分析 →</a></section>
        <section class="panel b-panel"><h2>调查与风险</h2><p>{{scopedRisks.filter(r=>r.state==='SUSPECTED').length}} 项待确认 · {{scopedRisks.filter(r=>effectiveState(r)==='CONFIRMED').length}} 项有效提醒</p><a class="button small" :href="link('risks')">跟进调查 →</a></section>
      </aside></div>
      <form v-if="newCase && sourceFilter==='TEACHING'" class="panel b-panel b-form" @submit.prevent="source='TEACHING';createCase()"><h2>教学与异常演示</h2><div class="b-grid"><label>教学资料<select v-model="datasetId" required><option value="">选择已启用资料</option><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}}</option></select></label><label>订单<select v-model="orderId" required><option value="">选择资料内订单</option><option v-for="o in records.filter(r=>r.type==='order')" :key="o.id" :value="o.id">{{o.orderNumber}}</option></select></label></div><label>问题标题<input v-model="caseTitle" required></label><label>客户原话<textarea v-model="customer" required></textarea></label><details><summary>业务日期与适用范围</summary><label>业务日期<input v-model="businessDate"></label><label>地区<input v-model="caseRegion"></label><label>平台<input v-model="casePlatform"></label><label>语言<input v-model="caseLanguage"></label></details><button class="button primary" :disabled="busy">保存并核实事实</button></form>
    </template>

    <template v-if="current?.kind==='CASE'">
      <div class="b-case-meta"><span class="chip" :class="current.state==='ESCALATED'?'danger':'plain'">{{status(current)}}</span><span>{{storeLabel(current.body.erpStoreName)}}</span></div>
      <p v-if="current.state==='ESCALATED'" class="banner danger">请优先核实安全问题并跟进处理。</p>
      <CaseWorkspace :asset="current" :busy="busy" :model-enabled="!!workspace?.modelEnabled" v-model:draft="humanText" v-model:message="message" v-model:attachments="attachments" v-model:reason="reviewReason"
        @generate="perform(()=>job(current!,'cases','advice-jobs'))" @evidence="perform(()=>job(current!,'cases','evidence-jobs'))" @history="showHistory" @investigate="prepareInvestigation(current!)"
        @append="perform(async()=>{await mutate('cases',current!,'messages',{text:message,attachmentRefs:attachments.split(',').map(x=>x.trim()).filter(Boolean)});message='';attachments=''})"
        @link="(selected:string,reason:string)=>perform(async()=>{await mutate('cases',current!,'links',{lineId:selected,reason});await job(current!,'cases','evidence-jobs')})"
        @save="saveReply" />
      <details id="case-history" class="panel b-panel"><summary>消息、关联与处理历史</summary><article v-for="(r,i) in current.body.reviews" :key="i" class="b-fact"><b>人工处理 · {{formatDate(r.at)}}</b><p>{{r.text}}</p><small>依据：{{r.reason}} · {{r.actor}}</small></article><article v-for="v in current.history" :key="v.version"><p>版本 {{v.version}} · {{formatDate(v.createdAt)}} · {{stateNames[v.body._state] || v.body._state}}</p><small v-if="v.body.linkHistory?.length">关联变更：{{v.body.linkHistory.at(-1).reason || '首次必要确认'}}</small></article></details>
    </template>

    <template v-if="section==='experience'">
      <template v-if="sourceFilter==='ERP'"><CaseProducts :cases="scopedCases" /><details class="panel b-panel"><summary>商品评价与订单反馈</summary><SourceInbox v-if="workspace" :stores="workspace.sourceStores" initial-kind="reviews" :disabled="busy" @open="openSource" /></details><details class="b-boundary"><summary>退货统计</summary><p>尚未取得完整的发货与实收退货记录，暂不展示退货率。</p></details></template>
      <template v-else><div class="b-row"><small>独立教学资料 · {{reportData?.body.datasetVersion || '尚无已保存分析'}} · 不与 ERP 混算</small><button class="button small" @click="analysisSettings=!analysisSettings">{{analysisSettings?'收起分析范围':'调整分析范围 / 更新分析'}}</button></div>
        <section v-if="analysisSettings || !reportData" class="panel b-panel"><h2>分析范围</h2><div class="b-inline-form"><label>已启用资料<select v-model="selectedDataset"><option value="">选择资料</option><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</option></select></label><label class="b-check"><input v-model="analysisAI" type="checkbox" :disabled="!workspace?.modelEnabled">AI 主题与原因分析</label><button class="button primary" :disabled="busy || !selectedDataset" @click="analyze">更新分析</button></div><details><summary>观察范围与历史对比</summary><label>对比历史报告<select v-model="compareReport"><option value="">不比较</option><option v-for="r in all?.report.items" :key="r.id" :value="r.id">{{formatDate(r.body.createdAt)}} · {{r.body.datasetVersion}}</option></select></label><p v-for="(w,i) in datasets.find(d=>d.id===selectedDataset)?.body.manifest.windows || []" :key="i">{{i===0?'上期':'本期'}}：{{formatDate(w[0])}} 至 {{formatDate(w[1])}}</p><p>每期须满足完整观察期、至少20个订单商品及20件实发；本期实收至少3件且上升至少10个百分点才提示调查。</p></details><p v-if="!activeDatasets.length">请在知识与资料中启用已核验的独立教学资料。</p></section>
        <ProductExperience v-if="reportData" :report="reportData" :cases="assets" :busy="busy" @evidence="(id:string)=>perform(async()=>{selectedEvidence=await get('/analyses/'+reportData!.id+'/evidence/'+id)})" @investigate="startProductInvestigation" @correct="classificationOpen=true"><template #advanced><p v-if="reportData.body.comparison">历史对比：{{reportData.body.comparison.comparable?'口径一致，可查看原始件数差异':'口径不同，不能直接比较退货率'}}。</p></template></ProductExperience>
        <details class="panel b-panel"><summary>查看历史分析</summary><a v-for="r in all?.report.items" :key="r.id" class="b-list-row" :href="link('experience',r.id)"><span>{{formatDate(r.body.createdAt)}} · {{r.body.datasetVersion}}</span><span>{{r.body.metrics.items.filter((p:any)=>p.finding==='NEEDS_INVESTIGATION').length}} 项待调查</span></a></details>
      </template>
    </template>

    <template v-if="section==='risks'">
      <template v-if="current?.kind==='RISK'"><a :href="link('risks')" class="back">← 返回调查与风险</a><section class="panel b-panel"><div class="b-row"><h2>{{current.body.reason}}</h2><span class="chip warning">{{status(current)}}</span></div><p>{{current.body.limitations}}</p><dl class="b-fact-list"><div><dt>适用商品</dt><dd>{{current.body.identity.sku}}</dd></div><div><dt>适用店仓</dt><dd>{{current.body.identity.storeId}} / {{current.body.identity.warehouseMode==='ALL_STORE_WAREHOUSES'?'本店所有仓':current.body.identity.warehouseIds.join('、')}}</dd></div><div><dt>有效至</dt><dd>{{current.body.validUntil?formatDate(current.body.validUntil):'尚未人工确认'}}</dd></div></dl><div v-if="current.state==='SUSPECTED' || effectiveState(current)==='CONFIRMED'" class="b-risk-decision"><h3>{{current.state==='SUSPECTED'?'人工核实后确认提醒':'管理当前风险提醒'}}</h3><label>决定理由<input v-model="riskDecisionReason" required placeholder="记录核实依据或关闭、撤销原因"></label><label v-if="current.state==='SUSPECTED'">提醒有效至<input type="datetime-local" :value="new Date(validUntil).toLocaleString('sv-SE').slice(0,16).replace(' ','T')" @change="validUntil=new Date(($event.target as HTMLInputElement).value).toISOString()"></label><div class="button-row"><button v-for="d in (current.state==='SUSPECTED'?[{key:'CONFIRM',name:'确认风险并启用提醒'},{key:'REJECT',name:'驳回'}]:[{key:'CLOSE',name:'关闭'},{key:'REVOKE',name:'撤销'}])" :key="d.key" class="button" :class="{primary:d.key==='CONFIRM'}" :disabled="busy || !riskDecisionReason" @click="perform(()=>mutate('risks',current!,'decisions',{decision:d.key,reason:riskDecisionReason,validUntil:d.key==='CONFIRM'?validUntil:null}))">{{d.name}}</button></div></div><details open><summary>调查来源与决定历史</summary><p v-for="entry in all?.investigation.items.find(a=>a.id===current!.body.investigationId)?.body.entries || []" :key="entry.at">{{entry.text}}</p><blockquote v-for="(d,i) in current.body.decisions" :key="i">{{d.reason}}<small>{{d.actor}} · {{formatDate(d.at)}}</small></blockquote><button class="button small" @click="perform(async()=>{const a=all!.investigation.items.find(a=>a.id===current!.body.investigationId);if(a){viewInvestigation(a.id)}})">查看关联调查</button></details></section></template>
      <template v-else><template v-if="!activeInvestigation"><div class="b-risk-summary"><span>待跟进 <b>{{scopedInvestigations.filter(a=>['OPEN','NEEDS_EVIDENCE'].includes(a.state)).length}}</b></span><span>待确认 <b>{{scopedRisks.filter(r=>r.state==='SUSPECTED').length}}</b></span><span>有效提醒 <b>{{scopedRisks.filter(r=>effectiveState(r)==='CONFIRMED').length}}</b></span></div>
        <section class="panel b-panel"><h2>待跟进调查</h2><p v-if="!scopedInvestigations.some(a=>['OPEN','NEEDS_EVIDENCE'].includes(a.state))" class="muted">暂无调查。</p><article v-for="a in scopedInvestigations.filter(a=>['OPEN','NEEDS_EVIDENCE'].includes(a.state))" :key="a.id" class="b-fact"><div class="b-row"><div><b>{{a.body.entries[0].text}}</b><small>{{status(a)}} · {{formatDate(a.body.entries.at(-1).at)}}</small></div><button class="button small" :disabled="busy" @click="viewInvestigation(a.id)">继续调查</button></div></article><details v-if="scopedInvestigations.some(a=>!['OPEN','NEEDS_EVIDENCE'].includes(a.state))"><summary>已记录结论的调查</summary><a v-for="a in scopedInvestigations.filter(a=>!['OPEN','NEEDS_EVIDENCE'].includes(a.state))" :key="a.id" class="b-list-row" :href="href('/after-sales/risks',{source:sourceFilter,investigation:a.id})"><span>{{a.body.entries[0].text}}</span><span>{{status(a)}}</span></a></details></section>
<section class="panel b-panel"><div class="b-queue-tabs"><button v-for="q in [{key:'CURRENT',name:'风险提醒'},{key:'HISTORY',name:'历史记录'},{key:'ALL',name:'全部'}]" :key="q.key" :class="{active:riskView===q.key}" @click="riskView=q.key">{{q.name}}</button></div><a v-for="a in filteredRisks" :key="a.id" class="b-list-row" :href="link('risks',a.id)"><div><b>{{a.body.reason}}</b><small>{{a.body.identity.sku}}</small></div><span class="chip warning">{{status(a)}}</span></a><p v-if="!filteredRisks.length" class="muted">暂无风险提醒。</p></section></template><a v-else class="back" :href="link('risks')">← 返回调查与风险</a>
        <section v-if="activeInvestigation" class="panel b-panel"><h2>{{activeInvestigation.body.entries[0].text}}</h2><a :href="link(activeInvestigation.body.origin.kind==='REPORT'?'experience':'cases',activeInvestigation.body.origin.id)">查看来源问题与证据 →</a><details><summary>调查记录</summary><p v-for="(e,i) in activeInvestigation.body.entries" :key="i">{{e.text}} · {{formatDate(e.at)}}</p></details><form class="b-form" @submit.prevent="perform(()=>mutate('investigations',activeInvestigation!,'entries',{text:investigationText,evidenceRefs:chosenEvidence,conclusion}))"><label>本次核实情况<textarea v-model="investigationText" required placeholder="记录已核事实、补证及下一步"></textarea></label><details><summary>选择可追溯证据（已选 {{chosenEvidence.length}} 条）</summary><label v-for="f in investigationEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></details><label>人工结论<select v-model="conclusion"><option value="OPEN">继续调查</option><option value="SUPPORTED">证据支持风险</option><option value="REJECTED">证据不支持</option><option value="NEEDS_EVIDENCE">需进一步补证</option></select></label><button class="button primary" :disabled="busy || (conclusion==='SUPPORTED' && !chosenEvidence.length)">保存调查结论</button></form><button v-if="activeInvestigation.state==='SUPPORTED' && !risks.some(r=>r.body.investigationId===activeInvestigation!.id)" class="button" :disabled="busy" @click="riskRegister=true;riskReason=activeInvestigation.body.entries[0].text">登记疑似风险</button><p v-else class="muted">{{risks.some(r=>r.body.investigationId===activeInvestigation!.id)?'此调查已有关联风险，请在上方查看。':'证据支持风险后，可明确范围并登记疑似风险。'}}</p></section>
        <form v-if="riskRegister && activeInvestigation" class="panel b-panel b-form" @submit.prevent="createRisk"><h2>确认本次风险线索范围</h2><label>问题与依据<textarea v-model="riskReason" required></textarea></label><label>尚未确认的事项<textarea v-model="limitations" required></textarea></label><label>本次涉及商品<select v-model="riskOption" required><option value="">选择调查内已核实商品</option><option v-for="(p,i) in riskOptions" :key="i" :value="String(i)">{{p.name}}</option></select></label><p v-if="!riskOptions.length" class="b-gap">来源尚缺明确商品或仓库，先回到案件核实。</p><button class="button primary" :disabled="busy || !riskOptions.length">保存疑似风险，继续人工确认</button></form>
      </template>
    </template>
    <template v-if="section==='materials'">
      <section class="panel b-panel"><div class="b-row"><h2>售后政策</h2><button v-if="policyManage && workspace?.capabilities?.policyWrite" class="button" :disabled="busy" @click="importPolicyDrafts">准备政策草稿</button></div><label v-if="policyManage">适用范围<select v-model="starterScope"><option value="TEACHING">教学店铺 · 中国</option><option value="AMAZON">Amazon · 美国</option></select></label><label>搜索政策<input v-model="policySearch" placeholder="政策名称或关键词"></label><button v-if="workspace?.capabilities?.policyWrite || workspace?.capabilities?.policyPublish" class="b-text-button" @click="policyManage=!policyManage">{{policyManage?'退出维护':'维护政策'}}</button><article v-for="p in visiblePolicies.filter(p=>policyManage || p.state==='PUBLISHED')" :key="p.id" class="b-fact"><div class="b-row"><h3>{{p.body.title}}</h3><span class="chip plain">{{status(p)}}</span></div><p v-for="s in p.body.sections" :key="s.id">{{s.text}}</p><p class="muted">{{p.body.category==='ALL'?'服装及电子产品':p.body.category==='APPAREL'?'服装':'电子产品'}} / {{p.body.region}} / {{p.body.platform}} / {{p.body.language}} · {{p.body.effectiveFrom}} — {{p.body.effectiveUntil}}</p><div v-if="policyManage" class="button-row"><button v-if="workspace?.capabilities?.policyWrite && p.state==='DRAFT'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'submit-review',{}))">提交政策审核</button><button v-if="workspace?.capabilities?.policyPublish && p.state==='IN_REVIEW'" class="button primary" :disabled="busy" @click="perform(()=>mutate('policies',p,'publish',{reason:'本人核对政策正文及适用范围后明确发布'}))">确认并发布此政策</button><button v-if="workspace?.capabilities?.policyPublish && p.state==='PUBLISHED'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'revoke',{reason:'本人明确撤销此政策的后续使用'}))">撤销政策</button><button v-if="workspace?.capabilities?.policyWrite" class="button" :disabled="busy" @click="editingPolicy=p.id;policyRevisionText=p.body.sections.map((s:any)=>s.text).join('\n\n')">修订并新建草稿版本</button></div><form v-if="editingPolicy===p.id" @submit.prevent="editPolicy(p)"><label>修订正文<textarea v-model="policyRevisionText" required maxlength="4000"></textarea></label><p>原版本及引用保留，新版本须重新审核发布。</p><button class="button" :disabled="busy">保存新版本</button></form></article><details v-if="policyManage && workspace?.capabilities?.policyWrite"><summary>录入新政策</summary><form class="b-form" @submit.prevent="createPolicy"><label>政策标题<input v-model="policyTitle" required></label><label>正文<textarea v-model="policyText" required></textarea></label><div class="b-grid"><label>类目<select v-model="policyCategory"><option value="APPAREL">服装</option><option value="ELECTRONICS">电子产品</option><option value="ALL">两类均适用</option></select></label><label>地区<input v-model="policyRegion" required></label><label>平台<input v-model="policyPlatform" required></label><label>语言<input v-model="policyLanguage" required></label></div><button class="button" :disabled="busy">保存待审核草稿</button></form></details><p v-if="!visiblePolicies.some(p=>policyManage || p.state==='PUBLISHED')" class="muted">暂无可查看的政策。</p></section>
      <details v-if="workspace?.capabilities?.datasetManage" class="panel b-panel"><summary>资料管理</summary><div class="b-row"><h2>独立教学资料</h2><button class="button primary" :disabled="busy || datasets.some(d=>d.body.manifest.datasetId==='b-golden-20261116' && d.state!=='DRAFT')" @click="importPackage()">导入完整教学资料</button></div><p class="muted">40 张逻辑订单、每张 2 个商品，含实际发货、各退货阶段与反馈；资料存入中台，不创建 ERP 单据。</p><article v-for="d in datasets" :key="d.id" class="b-fact"><div class="b-row"><h3>{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</h3><span class="chip plain">{{status(d)}}</span></div><p v-for="issue in d.body.issues" :key="issue" class="banner danger">{{issue}}</p><p v-if="d.body.validation">已回读 {{d.body.validation.count}} 条事实 · {{d.body.validation.at}}</p><div class="button-row"><button v-if="['READBACK_VERIFIED','INACTIVE'].includes(d.state)" class="button primary" :disabled="busy" @click="perform(()=>mutate('datasets',d,'activate',{}))">启用资料</button><button v-if="d.state==='ACTIVE'" class="button" :disabled="busy" @click="perform(()=>mutate('datasets',d,'deactivate',{}))">停用资料</button><button v-if="d.state==='SEALED'" class="button" :disabled="busy" @click="perform(()=>job(d,'datasets','validation-jobs'))">校验并独立回读</button><button class="button" :disabled="busy" @click="perform(async()=>{await readRecords(d.id);note='已读取资料，可在下方核对原始教学事实。'})">核对资料</button></div></article><details><summary>导入其他版本 / 继续未完成导入</summary><p>选择包含 manifest 和 chunks 的独立教学 JSON 包。版本、数量、指纹与全部关联会在启用前校验；同版本草稿可断点继续，迟到数据必须新建版本。</p><input type="file" accept=".json" aria-label="教学资料文件" @change="importFile=($event.target as HTMLInputElement).files?.[0]"><button class="button" :disabled="busy || !importFile" @click="importLocalPackage">导入并核对资料版本</button></details><details v-if="records.length"><summary>教学事实与证据（{{records.length}}条）</summary><article v-for="r in records" :key="r.id" class="b-fact"><p>{{factText(r)}}</p><small>资料记录 {{r.id}}</small></article></details></details>
      <details v-if="workspace?.capabilities?.bindingManage" class="panel b-panel"><summary>教学风险与 ERP 商品的受控演示绑定</summary><p>需有管理权限。绑定由独立 ERP 回读核对真实商品和仓库，范围精确到当前用户、资料版本、店仓和有效期；不改变补货算法。</p><form class="b-form" @submit.prevent="bind"><label>教学版本<select v-model="bindingDataset" required><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}}</option></select></label><label>教学商品<select v-model="bindingProduct" required><option value="">选择资料内商品</option><option v-for="p in bindingProducts" :key="p.id" :value="p.id">{{p.name}} · {{p.sku}}</option></select></label><label>目标 ERP 店铺<select v-model="erpStore"><option v-for="s in workspace?.sourceStores" :key="s">{{s}}</option></select></label><label>目标 ERP 商品 SKU<input v-model="bindingSku" required placeholder="输入已获准商品 SKU 后核实"></label><button class="button" type="button" :disabled="busy || !bindingDataset || !bindingSku" @click="findMapping">查找已核实的商品与仓库</button><label>目标商品与仓库<select v-model="mappingChoice" required><option value="">从 ERP 已核实结果中选择</option><option v-for="(p,i) in mappingOptions" :key="i" :value="String(i)">{{p.name}}</option></select></label><label>有效至<input type="datetime-local" :value="new Date(validUntil).toLocaleString('sv-SE').slice(0,16).replace(' ','T')" @change="validUntil=new Date(($event.target as HTMLInputElement).value).toISOString()" required></label><button class="button" :disabled="busy">独立核实并建立演示绑定</button></form><article v-for="b in all?.binding.items" :key="b.id"><p>{{b.body.teachingIdentity.sku}} → {{b.body.erpIdentity.sku}} · {{status(b)}} · {{b.body.validUntil}}</p><button v-if="b.state==='ACTIVE'" class="button" :disabled="busy" @click="perform(()=>mutate('teaching-bindings',b,'revoke',{reason:'人工撤销教学演示绑定'}))">撤销绑定</button></article></details>
    </template>

    <Modal v-if="investigationOpen" title="发起人工调查" @close="investigationOpen=false"><form class="b-form" @submit.prevent="investigate((reportData || current)!)"><label>需要调查的问题<textarea v-model="investigationText" required></textarea></label><fieldset><legend>本次调查依据</legend><label v-for="f in availableEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></fieldset><button class="button primary" :disabled="busy || !chosenEvidence.length">保存调查</button></form></Modal>
    <Modal v-if="classificationOpen && reportData" title="修订反馈主题" @close="classificationOpen=false"><form class="b-form" @submit.prevent="perform(async()=>{await mutate('analyses',reportData!,'classifications',{feedbackId,labels:selectedLabels,span,reason:correctionReason});classificationOpen=false})"><label>反馈<select v-model="feedbackId" required><option value="">选择原文</option><option v-for="f in effectiveClassifications" :key="f.feedbackId" :value="f.feedbackId">{{f.text}}</option></select></label><fieldset><legend>反馈主题（可多选）</legend><label v-for="(name,code) in labelNames" :key="code" class="b-check"><input v-model="selectedLabels" type="checkbox" :value="code">{{name}}</label></fieldset><label>对应原文片段<input v-model="span" required></label><label>修订原因<input v-model="correctionReason" required></label><button class="button primary" :disabled="busy">留痕保存分类</button></form></Modal>
    <Modal v-if="selectedEvidence" title="原始业务依据" @close="selectedEvidence=undefined"><p>{{selectedEvidence.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台独立教学资料':'ERP 只读事实'}} · {{selectedEvidence.datasetVersion}}</p><p>{{factText(selectedEvidence.record)}}</p><details><summary>证据定位与校验</summary><p>{{selectedEvidence.record?.id}}</p><small>{{selectedEvidence.hash}}</small></details></Modal>
    <section v-if="all && ['workbench','cases','experience','risks'].includes(section)" class="b-tasks"><details><summary>后台任务与恢复</summary><p v-if="taskId">当前任务 {{taskId}}</p><button class="button" :disabled="busy" @click="perform(async()=>{const tasks=await get<any>('/tasks?workspaceId=after-sales-v1');backgroundTasks=tasks.items})">查询任务历史</button><div v-for="t in backgroundTasks" :key="t.taskRef.taskId" class="b-list-row"><span>{{t.scenarioId.includes('CASE')?'售后处理':t.scenarioId.includes('EXPERIENCE')?'体验分析':'资料核验'}} · {{t.state==='SUCCEEDED'?'已完成':t.state==='FAILED'?'需处理':t.state==='RUNNING'?'处理中':'等待处理'}}</span><button v-if="t.state==='SUCCEEDED'" class="button small" :disabled="busy" @click="perform(async()=>{const r=await request<any>('/analysis-tasks/'+t.taskRef.taskId+'/report');if(['CASE','REPORT','RISK'].includes(r.analysisReport.domainKind))open(r.analysisReport.domainKind==='CASE'?'cases':r.analysisReport.domainKind==='REPORT'?'experience':'risks',r.analysisReport.domainRef.id);else note='资料任务已完成，请在政策与资料查看。'})">查看结果</button><span v-if="t.errorCode">{{t.errorCode}}</span></div></details></section>
  </div>
</template>

<style scoped>
.b-page{max-width:1360px;margin:auto;color:#243b4b}.b-page h1{font-size:27px}.b-page .page-head{margin-bottom:22px}.b-page .subtitle{font-size:13px;color:#71818b;line-height:1.8;margin:10px 0 0}.b-page h2{font-size:17px;margin:0 0 18px}.b-page h3{font-size:14px;margin:20px 0 10px}.b-page p{line-height:1.8;font-size:14px}.b-page small{font-size:12px;color:#71818b;line-height:1.7}.b-panel{padding:21px;margin:20px 0}.b-row{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}.b-row h2{margin:0}.b-scope{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:16px 0 22px}.b-scope label{display:flex!important;align-items:center;font-size:12px;margin:0!important}.b-scope select{width:auto!important;font-size:12px!important;padding:7px!important}.b-workbench-grid{display:grid;grid-template-columns:minmax(0,1fr) 285px;gap:20px;align-items:start}.b-workbench-grid>div{min-width:0}.b-workbench-side .b-panel{margin-top:0}.b-workbench-side h2{font-size:16px}.b-workbench-side p{font-size:13px}.b-queue{overflow:hidden}.b-queue-tabs{display:flex;gap:6px;border-bottom:1px solid #e1e8ec;padding:0 16px;overflow:auto}.b-queue-tabs button{border:0;border-bottom:2px solid transparent;padding:16px 8px;background:none;font:inherit;font-size:13px;white-space:nowrap;color:#71818b;cursor:pointer}.b-queue-tabs button.active{color:#116d66;border-color:#116d66;font-weight:600}.b-queue-tabs small{background:#f0f3f5;padding:1px 4px;margin-left:4px}.b-search{padding:0 18px;border-bottom:1px solid #e1e8ec}.b-search label{display:flex!important;align-items:center;gap:12px!important}.b-search input{max-width:320px}.b-table-scroll{overflow:auto}.b-table{width:100%;text-align:left;border-collapse:collapse;font-size:13px}.b-table th{background:#f8fafb;padding:13px 16px;font-weight:500;color:#71818b;font-size:12px}.b-table td{padding:20px 16px;border-bottom:1px solid #e6ecef;vertical-align:top}.b-table a{color:#126c66;font-weight:600}.b-table small{display:block;margin-top:6px}.b-queue-foot{display:flex;justify-content:space-between;padding:14px 18px;font-size:12px}.b-empty{text-align:center;padding:42px 18px;color:#71818b}.b-empty b{font-size:14px}.b-case-meta{display:flex;align-items:center;gap:10px;font-size:12px;margin:12px 0 22px;flex-wrap:wrap}.b-case-meta>.button{margin-left:auto}.b-case-grid{display:grid;grid-template-columns:minmax(0,.85fr) minmax(0,1fr) minmax(0,1.1fr);align-items:start;gap:16px}.b-case-grid>.panel{margin:0}.b-case-column{padding:20px;min-width:0}.b-case-column>h2,.b-case-column>.b-row{padding-bottom:18px;border-bottom:1px solid #e2e9ed;margin-bottom:18px}.b-case-column blockquote{background:#f6f8fa;border-left:0;padding:13px;margin:0 0 12px;overflow-wrap:anywhere}.b-case-column blockquote p{font-size:13px;margin:8px 0 0}.b-case-column details{margin:18px 0}.b-verified{padding:12px;background:#edf6ef;border:1px solid #c5decf;border-left:3px solid #317a5b;font-size:13px}.b-verified small{display:block;margin-top:4px}.b-fact-list{font-size:12px;margin:16px 0}.b-fact-list>div{display:flex;justify-content:space-between;gap:12px;padding:12px 0;border-bottom:1px solid #e5ebef}.b-fact-list dt{color:#71818b;flex-shrink:0}.b-fact-list dd{margin:0;text-align:right;overflow-wrap:anywhere}.b-fact{padding:12px 0;border-bottom:1px solid #e6ecef;font-size:13px}.b-fact p{font-size:13px;margin:6px 0}.b-fact small,.b-list-row small{display:block}.b-insight{background:#f1f7f4;border-left:3px solid #99beb1;padding:12px 14px;margin:16px 0}.b-insight p{font-size:14px;margin:4px 0}.b-text-button{border:0;background:none;padding:6px 0;font:inherit;font-size:12px;color:#126c66;cursor:pointer}.b-text-button:disabled{opacity:.4}.b-decision>.b-text-button{margin:0 12px 0 0}.b-decision textarea{min-height:110px}.b-gap{font-size:12px!important;border-left:3px solid #c7a65e;padding-left:10px;color:#82652d}.b-boundary{font-size:12px!important;color:#71818b;margin:18px 0}.b-form{display:grid;gap:12px}.b-page label{display:grid;gap:7px;margin:12px 0;color:#425f70;font-size:13px}.b-page input,.b-page select,.b-page textarea{border:1px solid #cbd7de;border-radius:5px;padding:9px 10px;width:100%;font:inherit;color:#243b4b;background:white;min-width:0}.b-page textarea{resize:vertical;min-height:85px}.b-check{display:flex!important;align-items:center;gap:8px}.b-check input{width:auto}.b-page fieldset{border:1px solid #dce4e9}.b-page summary{cursor:pointer;color:#37666c;font-size:12px}.b-page details{margin:18px 0}.b-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.b-inline-form{display:flex;align-items:end;gap:14px;flex-wrap:wrap}.b-inline-form label{flex:1;min-width:180px}.b-list-row{display:flex;justify-content:space-between;gap:16px;padding:16px 0;border-bottom:1px solid #e5ebef;color:inherit;font-size:13px}.b-risk-summary{display:flex;gap:36px;font-size:13px;color:#71818b;padding:18px 0}.b-risk-summary b{font-size:22px;font-weight:600;color:#243b4b;margin-left:10px}.b-risk-decision{max-width:600px}.b-tasks{font-size:12px;color:#71818b;margin-top:22px}.b-page .banner{font-size:13px;overflow-wrap:anywhere}.b-page .button:disabled{opacity:.5}.b-page .back{font-size:12px;margin-bottom:12px;display:inline-block}
@media(max-width:1150px){.b-workbench-grid{grid-template-columns:minmax(0,1fr) 250px}.b-case-grid{grid-template-columns:1fr 1fr}.b-case-column:first-child{grid-column:1/-1}.b-case-column:first-child blockquote{max-width:100%}.b-case-column{padding:18px}}
@media(max-width:800px){.b-workbench-grid,.b-case-grid,.b-grid{grid-template-columns:1fr}.b-case-column:first-child{grid-column:auto}.b-workbench-side{display:grid;gap:14px;grid-template-columns:1fr}.b-scope small{flex-basis:100%}.b-case-meta>.button{margin-left:0}.b-panel{padding:18px}.b-page h1{font-size:23px}}
</style>
