<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { route, navigate, href } from '../router'
import { request, errorText, ApiError } from '../api/client'
import { get, post, change, stateNames, labelNames, effectiveState, type Asset, type Workbench, type Workspace, type Index } from './api'

const workspace = ref<Workspace>(), all = ref<Workbench>(), current = ref<Asset>(), busy = ref(false), loading = ref(false), error = ref(''), note = ref('')
const section = computed(() => route.value.segments[1] || 'workbench')
const tabs = [{ key:'workbench',name:'售后工作台' },{key:'cases',name:'售后处理'},{key:'experience',name:'客户体验'},{key:'risks',name:'质量风险'},{key:'materials',name:'政策与资料'}]
const title = computed(() => tabs.find(t => t.key === section.value)?.name || '售后工作台')
const newCase = ref(false), customer = ref(''), caseTitle = ref(''), datasetId = ref(''), orderId = ref(''), businessDate = ref('2026-09-05T00:00:00Z')
const source = ref('TEACHING'), erpStore = ref(''), ticketId = ref(''), casePlatform = ref('TEACHING'), caseRegion = ref('CN'), caseLanguage = ref('zh')
const records = ref<Record<string, any>[]>([]), lineId = ref(''), linkReason = ref(''), message = ref(''), humanText = ref(''), reviewReason = ref('')
const selectedDataset = ref(''), reportData = ref<Asset>(), feedbackId = ref(''), labels = ref('UNKNOWN'), span = ref(''), correctionReason = ref('')
const investigationText = ref(''), investigationId = ref(''), evidenceRefs = ref(''), conclusion = ref('OPEN')
const riskReason = ref(''), limitations = ref('仅教学样本，尚未证实企业质量缺陷'), riskDataset = ref(''), riskDecisionReason = ref('')
const validUntil = ref(new Date(Date.now()+29*86400000).toISOString())
const mappingIdentity = ref(''), teachingIdentity = ref(''), bindingDataset = ref('')
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
  return (b.feedback || []).map((f: any) => ({...f, classification:[...(b.classificationCorrections || [])].reverse().find((x: any) => x.feedbackId === f.feedbackId) || b.classifications.find((x: any) => x.feedbackId === f.feedbackId)}))
})
const themeCounts = computed(() => { const counts: Record<string,number> = {}; for (const f of effectiveClassifications.value) for (const label of new Set<string>(f.classification?.labels || ['UNKNOWN'])) counts[label] = (counts[label] || 0)+1; return counts })
function link(page:string,id?:string) { return href('/after-sales/'+page,{id,returnTo:returnTo.value || undefined}) }
function open(page:string,id:string) { navigate('/after-sales/'+page,{id,returnTo:returnTo.value || undefined}) }
function collection() { return section.value === 'experience' ? 'analyses' : section.value }
function status(a:Asset) { return stateNames[effectiveState(a)] || a.state }
function pretty(v:unknown) { return typeof v === 'string' ? v : JSON.stringify(v,null,2) }
const stages:Record<string,string>={draft:'草稿',requested:'申请',authorized:'曾授权',authorizedValid:'有效授权',received:'实收',refunded:'实际退款',cancelled:'取消'}
function factText(f:any) {
  const r=f.value || f.record || f
  if(r.type==='shipment')return `实际发货 ${r.quantity} 件，时间 ${r.at}`
  if(r.type==='return')return `${stages[r.stage] || r.stage} ${r.quantity} 件，时间 ${r.at}`+(r.amount!=null?`；退款 ${r.amount} ${r.currency}`:'')
  if(r.type==='order')return `订单${r.paid===true?'已记录支付':'支付状态待核实'}；业务时间 ${r.paidAt || '未提供'}`
  if(r.type==='feedback')return r.text
  if(f.text)return f.text
  if(f.domain==='PAYMENT')return `已记录支付 ${r.amount} ${r.currency || ''}，时间 ${r.at}`
  if(typeof r==='string')return r
  return pretty(r)
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
    } else if(origin.body.identity){const p=origin.body.identity;riskOptions.value=[{name:p.name+' · '+p.sku,identity:{sourceTenant:origin.scope.sourceTenant,productId:p.productId,sku:p.sku,storeId:p.storeId,warehouseMode:'EXPLICIT_IDS',warehouseIds:[p.warehouseId]}}]}
  }catch(e){error.value=errorText(e)}
})
async function refresh() {
  const run=++sequence;loading.value=true;error.value='';current.value=undefined;reportData.value=undefined;selectedEvidence.value=undefined;chosenEvidence.value=[];investigationEvidence.value=[]
  try {
    const [w,index] = await Promise.all([get<Workspace>('/workspace'),get<Workbench>('/workbench')])
    if(run!==sequence || !alive.value)return
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
async function chooseInvestigation(a:Asset){investigationId.value=a.id;const o=a.body.origin;const origin=await get<Asset>('/'+(o.kind==='CASE'?'cases':'analyses')+'/'+o.id);investigationEvidence.value=o.kind==='CASE'?(origin.body.evidence?.facts || []).map((f:any)=>({id:f.id,text:factText(f)})):origin.body.feedback.map((f:any)=>({id:f.feedbackId,text:f.text}));chosenEvidence.value=[]}
async function importPolicyDrafts() {await perform(async()=>{for(const p of await get<any[]>('/policy-starters'))await command('/policies',p);await refresh();note.value='四类教学政策已保存为草稿，请逐项审核发布。'})}
async function createPolicy() {await perform(async()=>{
  await command('/policies',{title:policyTitle.value,category:policyCategory.value,topics:['REPLY'],sections:[{id:'s1',text:policyText.value}],region:policyRegion.value,platform:policyPlatform.value,language:policyLanguage.value,
    effectiveFrom:'2026-01-01T00:00:00Z',effectiveUntil:'2027-01-01T00:00:00Z',source:'本机人工录入政策，待人工发布',terms:['CLARIFY','MANUAL_REVIEW']});await refresh();policyTitle.value='';policyText.value=''
})}
async function analyze() {await perform(async()=>{
  const d=datasets.value.find(d=>d.id===selectedDataset.value);if(!d)return
  const rule={version:'return-config-'+crypto.randomUUID().slice(0,8),observationDays:Number(observationDays.value),minOrders:20,minQuantity:20,deltaBasisPoints:Math.round(Number(threshold.value)*100),minReceived:3}
  await job(d,'datasets','analysis-jobs',{ai:analysisAI.value,compareReportId:compareReport.value || undefined,windows:windows.value?JSON.parse(windows.value):d.body.manifest.windows,asOf:cutoff.value || d.body.manifest.asOf,rule})
})}
async function investigate(origin:Asset) {await perform(async()=>{const result=await command<Asset>('/investigations',{kind:origin.kind,id:origin.id,text:investigationText.value,evidenceRefs:chosenEvidence.value});investigationText.value='';open('risks','');await refresh();investigationId.value=result.id;note.value='调查已建立，请在下方补充证据与人工结论。'})}
async function createRisk() {await perform(async()=>{const identity=riskOptions.value[Number(riskOption.value)]?.identity;if(!identity)throw new Error('RISK_SCOPE_REQUIRED');const result=await command<Asset>('/risks',{investigationId:investigationId.value,reason:riskReason.value,limitations:limitations.value,identity,datasetId:riskDataset.value || null});open('risks',result.id);await refresh()})}
async function bind() {await perform(async()=>{const ds=datasets.value.find(d=>d.id===bindingDataset.value);if(ds)await job(ds,'datasets','binding-jobs',{teachingIdentity:JSON.parse(teachingIdentity.value),erpIdentity:JSON.parse(mappingIdentity.value),validUntil:validUntil.value})})}
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
    <p v-if="loading" role="status">正在读取当前记录…</p>
    <p v-if="workspace && !workspace.modelEnabled" class="b-model-note">AI 尚未获得 B 模块的独立调用授权。证据核实、统计、人工处理和风险调查可继续。</p>

    <template v-if="section==='workbench' && all">
      <section class="b-hero"><div><h2>先核实问题，再形成处理建议</h2><p>跟进客户问题，观察退货变化，将已确认风险带入补货决策。</p></div><a class="button primary" :href="link('cases')">处理售后 →</a></section>
      <div class="b-stats"><a :href="link('cases')"><b>{{assets.filter(a=>!['HANDLED'].includes(a.state)).length}}</b> 本页待跟进案件</a><a :href="link('experience')"><b>{{all.report.items.length}}</b> 本页体验分析</a><a :href="link('risks')"><b>{{risks.filter(a=>effectiveState(a)==='CONFIRMED').length}}</b> 本页已确认风险</a></div>
      <section class="panel b-panel"><h2>优先处理</h2><a v-for="a in assets.filter(a=>a.state==='ESCALATED' || a.state==='REVIEW_PENDING')" :key="a.id" class="b-list-row" :href="link('cases',a.id)"><b>{{a.body.title}}</b><span class="chip warning">{{status(a)}}</span></a><p v-if="!assets.some(a=>['ESCALATED','REVIEW_PENDING'].includes(a.state))" class="muted">当前没有安全升级或待审核案件。</p></section>
    </template>

    <template v-if="section==='cases'">
      <template v-if="!current">
        <button class="button primary" :disabled="busy" @click="newCase=!newCase">新建 / 接入案件</button>
        <form v-if="newCase" class="panel b-panel b-form" @submit.prevent="createCase">
          <h2>接入客户问题</h2><label>来源<select v-model="source"><option value="TEACHING">中台教学资料</option><option value="ERP">获准 ERP 工单（只读）</option></select></label>
          <template v-if="source==='ERP'"><label>店铺<select v-model="erpStore" required><option v-for="s in workspace?.sourceStores" :key="s">{{s}}</option></select></label><label>工单 ID<input v-model="ticketId" placeholder="留空可先发现该店工单" pattern="[1-9][0-9]*"></label></template>
          <template v-else><label>教学版本<select v-model="datasetId"><option value="">暂未关联资料</option><option v-for="d in activeDatasets" :value="d.id" :key="d.id">{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</option></select></label><label>订单<select v-model="orderId"><option value="">待补充订单</option><option v-for="o in records.filter(r=>r.type==='order')" :value="o.id" :key="o.id">{{o.orderNumber}}</option></select></label><label>案件业务日期<input v-model="businessDate" required></label></template>
          <label>问题标题<input v-model="caseTitle" maxlength="200" placeholder="概括客户遇到的问题"></label><label>客户原话<textarea v-model="customer" :required="source!=='ERP'" maxlength="6000" placeholder="仅录入实际收到的客户主张；工单标题不会被当作完整会话"></textarea></label>
          <details><summary>适用地区、平台与语言</summary><div class="b-grid"><label>地区<input v-model="caseRegion"></label><label>平台<input v-model="casePlatform"></label><label>语言<input v-model="caseLanguage"></label></div></details><button class="button primary" :disabled="busy">保存并核实事实</button>
        </form>
        <section class="panel b-panel"><a v-for="a in assets" :key="a.id" class="b-list-row" :href="link('cases',a.id)"><div><b>{{a.body.title}}</b><small>{{a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台教学':'ERP 只读'}} · {{a.body.identity?.name || '商品待核实'}}</small></div><span class="chip" :class="a.state==='ESCALATED'?'danger':'plain'">{{status(a)}}</span></a><p v-if="!assets.length" class="empty-inline">还没有案件。可接入 ERP 工单，或使用已启用的教学资料开始。</p></section>
      </template>
      <template v-if="current?.kind==='CASE'">
        <a class="back" :href="link('cases')">← 返回案件列表</a><section class="panel b-panel"><div class="b-row"><h2>{{current.body.title}}</h2><span class="chip warning">{{status(current)}}</span></div><p class="muted">{{current.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台独立教学资料':'ERP 只读观察'}} · 内部处理记录</p>
          <p v-if="current.state==='ESCALATED'" class="banner danger">安全信号优先转人工处理；不等待 AI，不指导拆机。</p>
          <div v-if="current.body.erpDiscovery" class="b-list"><h3>本次发现的 ERP 工单</h3><p v-if="!current.body.erpDiscovery.complete" class="muted">仅展示本次有界发现，非完整工单总量。</p><div v-for="candidate in current.body.erpDiscovery.items" :key="candidate.ticketId" class="b-list-row"><b>{{candidate.title}}</b><button class="button small" :disabled="busy" @click="source='ERP';ticketId=candidate.ticketId;erpStore=candidate.storeName;newCase=true;open('cases','')">接入此工单</button></div></div>
          <h3>客户陈述</h3><blockquote v-for="(m,i) in current.body.messages" :key="i">{{m.text}}<small>{{m.source==='CLAIM'?'客户主张':'来源观察'}} · {{m.at}}</small><small v-if="m.attachmentRefs?.length">待核附件：{{m.attachmentRefs.join('、')}}</small></blockquote>
          <form @submit.prevent="perform(async()=>{await mutate('cases',current!,'messages',{text:message,attachmentRefs:attachments.split(',').map(x=>x.trim()).filter(Boolean)});message='';attachments=''})"><label>补充客户消息<textarea v-model="message" required maxlength="6000"></textarea></label><label>客户提供的附件引用（可选）<input v-model="attachments" placeholder="多个以逗号分隔；仅记录引用，不代表附件内容已核实"></label><button class="button" :disabled="busy || !message">追加消息</button></form>
        </section>
        <section class="panel b-panel"><div class="b-row"><h2>商品与业务事实</h2><button class="button" :disabled="busy" @click="perform(()=>job(current!,'cases','evidence-jobs'))">重新核实事实</button></div>
          <div v-if="current.body.identity"><h3>{{current.body.identity.name}}</h3><p>{{current.body.identity.sku}} · {{current.body.identity.category==='UNKNOWN'?'商品属性待补证':current.body.identity.category==='APPAREL'?'服装':'电子产品'}}</p></div><p v-else class="banner warning">尚未确定受影响商品，请核实订单和商品关联。</p>
          <form v-if="identityCandidates.length" class="b-inline-form" @submit.prevent="perform(async()=>{await mutate('cases',current!,'links',{lineId,reason:linkReason});lineId='';linkReason=''})"><label>{{current.body.identity?'纠正已有商品关联':'选择本订单受影响商品'}}<select v-model="lineId" required><option value="">请选择</option><option v-for="c in identityCandidates" :key="c.lineId" :value="c.lineId">{{c.name}} · {{c.sku}}</option></select></label><label v-if="current.body.identity">纠正原因<input v-model="linkReason" required></label><button class="button" :disabled="busy || !lineId">{{current.body.identity?'留痕纠正':'确认商品'}}</button></form>
          <p v-for="gap in current.body.evidence?.missing" :key="gap" class="banner warning">{{gap}}</p>
          <div v-for="f in current.body.evidence?.facts" :key="f.id" class="b-fact"><b>{{f.domain==='shipment'?'实际发货':f.domain==='return'?'退货阶段':f.domain==='order'?'订单事实':f.domain}}</b><span class="chip plain">{{f.kind==='SIMULATED'?'教学事实':'ERP 已观察'}}</span><p>{{factText(f)}}</p><details><summary>证据来源与观察时间</summary><small>{{f.sourceRef}} · {{f.observedAt}}</small></details></div>
          <p v-if="!current.body.evidence?.facts?.length" class="muted">当前尚无可用业务事实；客户陈述仍完整保留。</p>
        </section>
        <section class="panel b-panel"><div class="b-row"><h2>AI 处理建议</h2><button class="button primary" :disabled="busy || !current.body.identity || !current.body.evidence" @click="perform(()=>job(current!,'cases','advice-jobs'))">检索政策并生成建议</button></div>
          <p v-if="!lastAdvice" class="muted">先核实关联和证据，再请求 AI；无有效政策或模型不可用时可继续人工处理。</p>
          <template v-else><p v-if="lastAdvice.ai.status!=='AVAILABLE'" class="banner warning">建议未生成：{{lastAdvice.ai.reason==='B_MODEL_AUTHORIZATION_REQUIRED'?'B 模型调用未授权':lastAdvice.ai.reason==='POLICY_NOT_APPLICABLE'?'缺少匹配且已发布的政策':lastAdvice.ai.reason}}</p><template v-else><p class="b-ai-draft">{{lastAdvice.ai.output.replyDraft}}</p><p v-if="lastAdvice.caseRevision!==current.revision" class="banner warning">案件已有新版本，旧建议需重新生成后才可采纳。</p><ul><li v-for="g in lastAdvice.ai.output.missingEvidence" :key="g">待补证：{{g}}</li></ul></template>
            <details v-for="p in lastAdvice.policies" :key="p.policyId+p.sectionId"><summary>{{p.title}} · 政策依据</summary><p>{{p.text}}</p><small>{{p.applicability}} · 版本 {{p.version}}</small></details></template>
        </section>
        <section class="panel b-panel"><h2>人工审核与处理</h2><label>人工处理稿<textarea v-model="humanText" required maxlength="6000"></textarea></label><label>审核理由<input v-model="reviewReason" required maxlength="1000"></label><div class="button-row"><button v-for="d in [{key:'ACCEPT',label:'采纳并保存'},{key:'MANUAL',label:'保存人工处理'},{key:'RETURN',label:'退回补充'},{key:'ESCALATE',label:'升级人工'}]" :key="d.key" class="button" :disabled="busy || !humanText || !reviewReason || (d.key==='ACCEPT' && (lastAdvice?.ai.status!=='AVAILABLE' || lastAdvice?.caseRevision!==current.revision))" @click="perform(async()=>{await mutate('cases',current!,'reviews',{adviceVersion:lastAdvice?.version || null,text:humanText,reason:reviewReason,decision:d.key});humanText='';reviewReason=''})">{{d.label}}</button></div><p class="muted">保存仅完成中台内部记录，客户消息与退款须另行处理。</p><blockquote v-for="(r,i) in current.body.reviews" :key="i"><p>{{r.text}}</p><small>理由：{{r.reason}} · 实际审核者 {{r.actor}} · {{r.at}}</small></blockquote></section>
      </template>
    </template>

    <template v-if="section==='experience'">
      <section class="panel b-panel"><h2>观察客户体验与退货变化</h2><div class="b-inline-form"><label>教学数据版本<select v-model="selectedDataset"><option value="">选择已启用资料</option><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</option></select></label><label class="b-check"><input v-model="analysisAI" type="checkbox" :disabled="!workspace?.modelEnabled">同时进行 AI 主题与原因分析</label><button class="button primary" :disabled="busy || !selectedDataset" @click="analyze">开始分析</button></div><label>与历史报告比较（可选）<select v-model="compareReport"><option value="">不比较</option><option v-for="r in all?.report.items" :key="r.id" :value="r.id">{{r.body.createdAt}} / {{r.body.datasetVersion}}</option></select></label><details><summary>观察周期与异常规则</summary><div class="b-grid"><label>观察天数<input v-model="observationDays" type="number" min="1" max="365"></label><label>异常增加百分点<input v-model="threshold" type="number" min="0.01" max="100" step="0.01"></label><label>分析截止（带时区）<input v-model="cutoff" placeholder="默认资料截止时间"></label></div><label>两个等长、不重叠的时间窗<textarea v-model="windows" placeholder='默认资料的前后两个时间窗；JSON数组'></textarea></label><p>最少 20 个成熟订单商品和 20 件实发；实收至少 3 件。规则与每份报告一同保存。</p></details></section>
      <section v-if="!reportData" class="panel b-panel"><h2>分析历史</h2><a v-for="a in all?.report.items" :key="a.id" class="b-list-row" :href="link('experience',a.id)"><div><b>客户体验与退货分析</b><small>{{a.body.createdAt}} · {{a.body.datasetVersion}}</small></div><span>{{a.body.metrics.items.filter((i:any)=>i.finding==='NEEDS_INVESTIGATION').length}} 项待调查</span></a><p v-if="!all?.report.items.length" class="muted">还没有分析报告，请先在“政策与资料”导入、校验并启用教学资料。</p></section>
      <template v-if="reportData"><a :href="link('experience')" class="back">← 返回报告历史</a><p class="b-source">中台独立教学数据 · {{reportData.body.datasetVersion}} · 不与 ERP 交易混算</p>
        <section v-if="reportData.body.comparison" class="panel b-panel"><h2>与所选历史报告的差异</h2><p>{{reportData.body.comparison.comparable?'相同选择窗与观察周期':'观察口径发生变化，勿直接比较退货率'}} · 历史资料 {{reportData.body.comparison.datasetVersion}}</p><p>资料版本{{reportData.body.comparison.changes.datasetVersionChanged?'已变化':'相同'}}，输入事实{{reportData.body.comparison.changes.inputChanged?'有更新':'相同'}}，规则{{reportData.body.comparison.changes.ruleChanged?'有更新':'相同'}}。</p><p v-for="i in reportData.body.comparison.items" :key="i.productId">{{i.sku}}：历史本期 {{i.previous?.groups[1].numerator ?? '未知'}} / {{i.previous?.groups[1].denominator ?? '未知'}} 件 → 当前 {{i.current.groups[1].numerator}} / {{i.current.groups[1].denominator}} 件</p><small>{{reportData.body.comparison.limitation}}</small></section><section class="panel b-panel"><h2>退货变化与待调查问题</h2><article v-for="item in reportData.body.metrics.items" :key="item.productId+item.storeId" class="b-product-result"><div class="b-row"><h3>{{item.name}}</h3><span class="chip" :class="item.finding==='NEEDS_INVESTIGATION'?'warning':'plain'">{{item.finding==='NEEDS_INVESTIGATION'?'待调查异常':item.finding==='UNKNOWN'?'数据不足':'未触发异常阈值'}}</span></div><div class="b-stats"><div><small>上期退货率</small><b>{{item.groups[0].ratePercent==null?'未知':item.groups[0].ratePercent+'%'}}</b><span>{{item.groups[0].numerator}} / {{item.groups[0].denominator}} 件</span></div><div><small>本期退货率</small><b>{{item.groups[1].ratePercent==null?'未知':item.groups[1].ratePercent+'%'}}</b><span>{{item.groups[1].numerator}} / {{item.groups[1].denominator}} 件</span></div><div><small>变化</small><b>{{item.deltaPercentagePoints==null?'未知':item.deltaPercentagePoints+' 个百分点'}}</b><span>实收退货，不等于缺陷确认</span></div></div><p v-for="g in item.groups" :key="g.denominator+g.numerator">{{g.unresolved?.length ? '待补证：'+g.unresolved.join('、') : ''}}</p><details><summary>阶段件数、金额与统计依据</summary><p>{{reportData.body.metrics.definition}}</p><div v-for="(g,i) in item.groups" :key="i"><h4>{{i===0?'上期':'本期'}}</h4><p>成熟订单商品 {{g.matureOrders}} / {{g.orders}}</p><p v-for="(count,stage) in g.stages" :key="stage">{{stages[stage] || stage}}：{{count}} 件</p><p>实际退款：{{pretty(g.refundAmounts)}}（按币种分列）</p><p>期外事件：{{g.outsideWindow.length}} 条</p><details><summary>发货、退货证据</summary><div class="button-row"><button v-for="eid in g.evidenceRefs" :key="eid" class="button small" :disabled="busy" @click="perform(async()=>{selectedEvidence=await get('/analyses/'+reportData!.id+'/evidence/'+eid)})">依据 {{eid.split('-').slice(-3).join('-')}}</button></div></details></div></details></article></section>
        <section class="panel b-panel"><h2>AI 原因分析</h2><p v-if="reportData.body.ai.status!=='AVAILABLE'" class="muted">本次 AI 分析未生成，已核统计保留。{{reportData.body.ai.reason==='B_MODEL_AUTHORIZATION_REQUIRED'?'B 模型调用未授权':reportData.body.ai.reason}}</p><template v-else><div v-for="(name,key) in {facts:'已核事实引用',hypotheses:'待验证原因',alternativeExplanations:'其他可能解释',missingEvidence:'需补充证据',nextSteps:'建议下一步'}" :key="key"><h3>{{name}}</h3><ul><li v-for="text in reportData.body.ai.output[key]" :key="text">{{text}}</li></ul></div></template></section>
        <section class="panel b-panel"><h2>客户反馈与主题</h2><p class="muted">按唯一反馈统计，含未分类反馈；多标签占比合计可能超过 100%。订单级反馈不分摊到商品。</p><div class="button-row"><span v-for="(n,l) in themeCounts" :key="l" class="chip plain">{{labelNames[l] || l}} {{n}} / {{effectiveClassifications.length}}</span></div><article v-for="f in effectiveClassifications" :key="f.feedbackId" class="b-fact"><p>{{f.text}}</p><p>{{f.classification?.labels.map((l:string)=>labelNames[l] || l).join('、')}} · {{f.channel==='ORDER_FEEDBACK'?'订单反馈':f.channel}}</p><small>原文证据 {{f.feedbackId}} · {{f.lineId?'已关联订单明细':'订单级，未分摊商品'}}</small></article><details><summary>人工修订主题</summary><form class="b-form" @submit.prevent="perform(()=>mutate('analyses',reportData!,'classifications',{feedbackId,labels:labels.split(',').map(x=>x.trim()),span,reason:correctionReason}))"><label>反馈<select v-model="feedbackId" required><option v-for="f in effectiveClassifications" :key="f.feedbackId" :value="f.feedbackId">{{f.text}}</option></select></label><label>主题代码（多项逗号分隔）<input v-model="labels" required></label><p class="muted">SIZE 尺码 / DESCRIPTION 描述 / DAMAGE 破损 / LOGISTICS 物流 / FUNCTION 功能 / COMPATIBILITY 兼容 / SAFETY 安全 / OTHER 其他 / UNKNOWN 未知</p><label>对应原文片段<input v-model="span" required></label><label>修订原因<input v-model="correctionReason" required></label><button class="button" :disabled="busy">留痕保存分类</button></form></details></section>
      </template>
    </template>

    <template v-if="(section==='cases' && current?.kind==='CASE') || (section==='experience' && reportData)">
      <section class="panel b-panel"><h2>发起人工调查</h2><form class="b-form" @submit.prevent="investigate((reportData || current)!)"><label>需要调查的问题<textarea v-model="investigationText" required></textarea></label><fieldset><legend>选择本次调查依据</legend><label v-for="f in availableEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></fieldset><button class="button" :disabled="busy">保存调查</button></form></section>
      <details class="panel b-panel"><summary>版本与处理历史</summary><article v-for="v in (reportData || current)?.history" :key="v.version"><h4>版本 {{v.version}} · {{v.createdAt}}</h4><p>操作者 {{v.actor}} · {{stateNames[v.body._state] || v.body._state}}</p><details><summary>查看当时记录</summary><pre>{{pretty(v.body)}}</pre></details></article></details>
    </template>

    <template v-if="section==='risks'">
      <template v-if="current?.kind==='RISK'"><a :href="link('risks')" class="back">← 返回风险列表</a><section class="panel b-panel"><div class="b-row"><h2>{{current.body.reason}}</h2><span class="chip warning">{{status(current)}}</span></div><p>{{current.body.limitations}}</p><p>适用商品 {{current.body.identity.sku}} · 店铺 {{current.body.identity.storeId}} · {{current.body.identity.warehouseMode==='ALL_STORE_WAREHOUSES'?'本店所有仓':current.body.identity.warehouseIds.join('、')}}</p><p>有效至 {{current.body.validUntil || '尚未人工确认'}}</p><label>决定理由<input v-model="riskDecisionReason" required></label><label v-if="current.state==='SUSPECTED'">有效期截止（默认不超过30天）<input v-model="validUntil"></label><div class="button-row"><button v-for="d in (current.state==='SUSPECTED'?[{key:'CONFIRM',name:'人工确认风险'},{key:'REJECT',name:'驳回'}]:effectiveState(current)==='CONFIRMED'?[{key:'CLOSE',name:'关闭'},{key:'REVOKE',name:'撤销'}]:[])" :key="d.key" class="button" :disabled="busy || !riskDecisionReason" @click="perform(()=>mutate('risks',current!,'decisions',{decision:d.key,reason:riskDecisionReason,validUntil:d.key==='CONFIRM'?validUntil:null}))">{{d.name}}</button></div><p class="muted">确认前须完成有证据支持的人工调查；风险只提醒，补货算法和采购条件继续适用。</p><h3>决定历史</h3><blockquote v-for="(d,i) in current.body.decisions" :key="i">{{d.reason}}<small>{{d.decision}} · {{d.actor}} · {{d.at}}</small></blockquote><details><summary>历史版本</summary><article v-for="v in current.history" :key="v.version"><p>版本 {{v.version}} · {{stateNames[v.body._state] || v.body._state}} · {{v.createdAt}}</p><p>{{v.body.reason}}</p></article></details></section></template>
      <section v-else class="panel b-panel"><h2>风险线索与有效提醒</h2><a v-for="a in risks" :key="a.id" class="b-list-row" :href="link('risks',a.id)"><div><b>{{a.body.reason}}</b><small>{{a.body.identity.sku}} · {{a.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台教学风险':'ERP 事实调查'}}</small></div><span class="chip warning">{{status(a)}}</span></a><p v-if="!risks.length" class="muted">尚无风险。请先从案件或分析报告发起调查。</p></section>
      <section class="panel b-panel"><h2>人工调查</h2><article v-for="a in all?.investigation.items" :key="a.id" class="b-investigation"><div class="b-row"><h3>{{a.body.entries[0].text}}</h3><span class="chip plain">{{status(a)}}</span></div><p v-for="(entry,i) in a.body.entries" :key="i">{{entry.text}} · {{entry.conclusion==='SUPPORTED'?'证据支持':entry.conclusion==='REJECTED'?'不支持':entry.conclusion==='NEEDS_EVIDENCE'?'需补证':'调查中'}}<small> {{entry.actor}} · {{entry.at}}</small></p><button class="button small" :disabled="busy" @click="perform(()=>chooseInvestigation(a))">补充本次调查</button><details v-if="investigationId===a.id" open><summary>补充证据与结论</summary><form class="b-form" @submit.prevent="perform(()=>mutate('investigations',a,'entries',{text:investigationText,evidenceRefs:chosenEvidence,conclusion}))"><label>补证记录<textarea v-model="investigationText" required></textarea></label><fieldset><legend>可回查的调查证据</legend><label v-for="f in investigationEvidence" :key="f.id" class="b-check"><input v-model="chosenEvidence" type="checkbox" :value="f.id">{{f.text}}</label></fieldset><label>人工结论<select v-model="conclusion"><option value="OPEN">继续调查</option><option value="SUPPORTED">证据支持风险</option><option value="REJECTED">证据不支持</option><option value="NEEDS_EVIDENCE">需进一步补证</option></select></label><button class="button" :disabled="busy">保存调查结论</button></form></details><button class="button small" :disabled="busy" @click="perform(async()=>{await chooseInvestigation(a);riskReason=a.body.entries[0].text})">将此调查登记为疑似风险</button></article></section>
      <form class="panel b-panel b-form" @submit.prevent="createRisk"><h2>登记疑似风险</h2><label>调查<select v-model="investigationId" required><option v-for="a in all?.investigation.items" :key="a.id" :value="a.id">{{a.body.entries[0].text}}</option></select></label><label>问题与依据<textarea v-model="riskReason" required></textarea></label><label>限制与未确认事项<textarea v-model="limitations" required></textarea></label><label>本次调查涉及商品<select v-model="riskOption" required><option value="">请选择已核实商品</option><option v-for="(p,i) in riskOptions" :key="i" :value="String(i)">{{p.name}}</option></select></label><p class="muted">风险仅登记在来源调查已核实的商品、店铺与仓库范围；其他店铺需另行调查确认。</p><button class="button" :disabled="busy">保存疑似风险</button></form>
    </template>

    <template v-if="section==='materials'">
      <section class="panel b-panel"><div class="b-row"><h2>独立教学资料</h2><button class="button primary" :disabled="busy || datasets.some(d=>d.body.manifest.datasetId==='b-golden-20261116' && d.state!=='DRAFT')" @click="importPackage()">导入完整教学资料</button></div><p class="muted">40 张逻辑订单、每张 2 个商品，含实际发货、各退货阶段与反馈；资料存入中台，不创建 ERP 单据。</p><article v-for="d in datasets" :key="d.id" class="b-fact"><div class="b-row"><h3>{{d.body.manifest.datasetId}} / {{d.body.manifest.version}}</h3><span class="chip plain">{{status(d)}}</span></div><p v-for="issue in d.body.issues" :key="issue" class="banner danger">{{issue}}</p><p v-if="d.body.validation">已回读 {{d.body.validation.count}} 条事实 · {{d.body.validation.at}}</p><div class="button-row"><button v-if="d.state==='READBACK_VERIFIED'" class="button primary" :disabled="busy" @click="perform(()=>mutate('datasets',d,'activate',{}))">启用资料</button><button v-if="d.state==='ACTIVE'" class="button" :disabled="busy" @click="perform(()=>mutate('datasets',d,'deactivate',{}))">停用资料</button><button v-if="d.state==='SEALED'" class="button" :disabled="busy" @click="perform(()=>job(d,'datasets','validation-jobs'))">校验并独立回读</button><button class="button" :disabled="busy" @click="perform(async()=>{await readRecords(d.id);note='已读取资料，可在下方核对原始教学事实。'})">核对资料</button></div></article><details><summary>导入其他版本 / 继续未完成导入</summary><p>选择包含 manifest 和 chunks 的独立教学 JSON 包。版本、数量、指纹与全部关联会在启用前校验；同版本草稿可断点继续，迟到数据必须新建版本。</p><input type="file" accept=".json" aria-label="教学资料文件" @change="importFile=($event.target as HTMLInputElement).files?.[0]"><button class="button" :disabled="busy || !importFile" @click="importLocalPackage">导入并核对资料版本</button></details><details v-if="records.length"><summary>教学事实与证据（{{records.length}}条）</summary><pre>{{pretty(records)}}</pre></details></section>
      <section class="panel b-panel"><div class="b-row"><h2>政策知识</h2><button class="button" :disabled="busy || !!all?.policy.items.length" @click="importPolicyDrafts">准备四类教学政策草稿</button></div><p class="muted">草稿不能检索。请核对正文、适用范围及有效期，再明确发布；不代表企业正式政策。</p><article v-for="p in all?.policy.items" :key="p.id" class="b-fact"><div class="b-row"><h3>{{p.body.title}}</h3><span class="chip plain">{{status(p)}}</span></div><p v-for="s in p.body.sections" :key="s.id">{{s.text}}</p><p class="muted">{{p.body.category==='ALL'?'全部已声明类目':p.body.category}} / {{p.body.region}} / {{p.body.platform}} / {{p.body.language}} · {{p.body.effectiveFrom}} — {{p.body.effectiveUntil}}</p><div class="button-row"><button v-if="p.state==='DRAFT'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'submit-review',{}))">提交政策审核</button><button v-if="p.state==='IN_REVIEW'" class="button primary" :disabled="busy" @click="perform(()=>mutate('policies',p,'publish',{reason:'本人核对上述教学政策正文及适用范围后明确发布'}))">确认并发布此政策</button><button v-if="p.state==='PUBLISHED'" class="button" :disabled="busy" @click="perform(()=>mutate('policies',p,'revoke',{reason:'本人明确撤销此政策的后续使用'}))">撤销政策</button><button class="button" :disabled="busy" @click="editingPolicy=p.id;policyRevisionText=p.body.sections.map((s:any)=>s.text).join('\n\n')">修订并新建草稿版本</button></div><form v-if="editingPolicy===p.id" @submit.prevent="editPolicy(p)"><label>修订正文<textarea v-model="policyRevisionText" required maxlength="4000"></textarea></label><p>原版本及引用保留，新版本须重新审核发布。</p><button class="button" :disabled="busy">保存新版本</button></form></article><details><summary>录入新政策</summary><form class="b-form" @submit.prevent="createPolicy"><label>政策标题<input v-model="policyTitle" required></label><label>正文<textarea v-model="policyText" required></textarea></label><div class="b-grid"><label>类目<select v-model="policyCategory"><option value="APPAREL">服装</option><option value="ELECTRONICS">电子产品</option><option value="ALL">两类均适用</option></select></label><label>地区<input v-model="policyRegion" required></label><label>平台<input v-model="policyPlatform" required></label><label>语言<input v-model="policyLanguage" required></label></div><button class="button" :disabled="busy">保存待审核草稿</button></form></details></section>
      <details class="panel b-panel"><summary>教学风险与 ERP 商品的受控演示绑定</summary><p>需有管理权限。绑定由独立 ERP 回读核对真实商品和仓库，范围精确到当前用户、资料版本、店仓和有效期；不改变补货算法。</p><form class="b-form" @submit.prevent="bind"><label>教学版本<select v-model="bindingDataset" required><option v-for="d in activeDatasets" :key="d.id" :value="d.id">{{d.body.manifest.datasetId}}</option></select></label><label>教学商品身份<textarea v-model="teachingIdentity" required></textarea></label><label>目标 ERP 商品身份<textarea v-model="mappingIdentity" required></textarea></label><label>有效至<input v-model="validUntil" required></label><button class="button" :disabled="busy">独立核实并建立演示绑定</button></form><article v-for="b in all?.binding.items" :key="b.id"><p>{{b.body.teachingIdentity.sku}} → {{b.body.erpIdentity.sku}} · {{status(b)}} · {{b.body.validUntil}}</p><button v-if="b.state==='ACTIVE'" class="button" :disabled="busy" @click="perform(()=>mutate('teaching-bindings',b,'revoke',{reason:'人工撤销教学演示绑定'}))">撤销绑定</button></article></details>
    </template>
    <div v-if="all && !route.query.id" class="button-row"><button v-for="[key,path,name] in ([['case','cases','案件'],['report','analyses','分析'],['risk','risks','风险'],['investigation','investigations','调查'],['dataset','datasets','资料'],['policy','policies','政策'],['binding','teaching-bindings','绑定']] as const)" v-show="all[key].nextCursor" :key="key" class="button small" :disabled="busy" @click="more(key,path)">加载更多{{name}}</button></div><section v-if="selectedEvidence" class="panel b-panel"><div class="b-row"><h2>原始业务依据</h2><button class="button small" @click="selectedEvidence=undefined">关闭</button></div><p>{{selectedEvidence.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'中台教学资料':'ERP 只读事实'}} · {{selectedEvidence.datasetVersion}}</p><p>{{factText(selectedEvidence.record)}}</p><details><summary>完整受控记录与校验指纹</summary><pre>{{pretty(selectedEvidence)}}</pre></details></section>
    <section v-if="all && ['cases','experience','risks'].includes(section)" class="b-tasks"><details><summary>后台任务与恢复</summary><p v-if="taskId">当前任务 {{taskId}}</p><button class="button" :disabled="busy" @click="perform(async()=>{const tasks=await get<any>('/tasks?workspaceId=after-sales-v1');backgroundTasks=tasks.items})">查询任务历史</button><div v-for="t in backgroundTasks" :key="t.taskRef.taskId" class="b-list-row"><span>{{t.scenarioId.includes('CASE')?'售后处理':t.scenarioId.includes('EXPERIENCE')?'体验分析':'资料核验'}} · {{t.state==='SUCCEEDED'?'已完成':t.state==='FAILED'?'需处理':t.state==='RUNNING'?'处理中':'等待处理'}}</span><button v-if="t.state==='SUCCEEDED'" class="button small" :disabled="busy" @click="perform(async()=>{const r=await request<any>('/analysis-tasks/'+t.taskRef.taskId+'/report');if(['CASE','REPORT','RISK'].includes(r.analysisReport.domainKind))open(r.analysisReport.domainKind==='CASE'?'cases':r.analysisReport.domainKind==='REPORT'?'experience':'risks',r.analysisReport.domainRef.id);else note='资料任务已完成，请在政策与资料查看。'})">查看结果</button><span v-if="t.errorCode">{{t.errorCode}}</span></div></details></section>
  </div>
</template>

<style scoped>
.b-page{max-width:1350px;margin:auto}.b-tabs{display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid #dce5e9;margin-bottom:24px}.b-tabs a{padding:12px 16px;color:#526573;text-decoration:none;border-bottom:3px solid transparent}.b-tabs a.active{color:#0f6b64;border-color:#0f6b64;font-weight:700}.b-panel{padding:24px;margin:22px 0}.b-panel h2{font-size:19px;margin:0 0 20px}.b-panel h3{font-size:16px}.b-row{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.b-row h2,.b-row h3{margin:0}.b-list-row{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:20px 4px;border-bottom:1px solid #e5ebee;text-decoration:none;color:inherit}.b-list-row small,blockquote small{display:block;margin-top:8px;color:#687c88}.b-hero{display:flex;justify-content:space-between;align-items:center;gap:25px;background:#eaf4ef;border:1px solid #cce1d5;border-radius:12px;padding:30px;margin:24px 0}.b-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin:22px 0}.b-stats>a,.b-stats>div{background:#f6f8fa;border:1px solid #e2e8ec;border-radius:9px;padding:20px;color:inherit;text-decoration:none;display:grid;gap:7px}.b-stats b{font-size:25px;color:#193f46}.b-stats span,.b-stats small{font-size:13px;color:#687c88}.b-form{display:grid;gap:17px}.b-page label{display:grid;gap:8px;margin:12px 0;color:#3f5661;font-size:14px}.b-page input,.b-page select,.b-page textarea{border:1px solid #cad7dd;border-radius:6px;padding:10px 12px;background:white;color:#233d49;font:inherit;width:100%;min-width:0}.b-page textarea{min-height:95px;resize:vertical}.b-form>.button{justify-self:start}.b-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.b-inline-form{display:flex;align-items:end;gap:16px;flex-wrap:wrap}.b-inline-form label{flex:1;min-width:180px}.b-check{display:flex!important;align-items:center;gap:8px}.b-check input{width:auto}.b-fact,.b-investigation{padding:18px 0;border-bottom:1px solid #e2e9ed}.b-fact pre,.b-panel pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.65;background:#f7f9fa;padding:14px;border-radius:6px;max-height:400px;overflow:auto}.b-page details{margin:16px 0}.b-page summary{cursor:pointer;color:#42636b;font-size:14px}.b-model-note,.b-source{padding:12px 16px;background:#edf3f7;border-left:3px solid #7e9da8;color:#47616e;font-size:13px}.b-page blockquote{padding:15px 18px;background:#f5f7f9;border-left:3px solid #bad0d8;margin:14px 0;white-space:pre-wrap;overflow-wrap:anywhere}.b-ai-draft{font-size:17px;line-height:1.8;padding:20px;background:#eff7f2}.b-product-result{padding:20px 0;border-bottom:1px solid #e2e9ed}.b-tasks{font-size:13px;color:#748590}.b-page .button:disabled{opacity:.5}.b-page .banner{overflow-wrap:anywhere}.b-page h1{font-size:28px}
@media(max-width:1050px){.b-stats{gap:10px}.b-stats b{font-size:21px}.b-grid{grid-template-columns:1fr 1fr}.b-hero{padding:22px}.b-tabs a{padding:11px}}
@media(max-width:700px){.b-stats,.b-grid{grid-template-columns:1fr}.b-hero{display:block}.b-panel{padding:18px}.b-tabs{gap:0}.b-tabs a{font-size:13px}.b-inline-form{display:block}}
</style>
