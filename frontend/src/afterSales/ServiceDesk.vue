<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, toRefs, watch } from 'vue'
import { request, errorText } from '../api/client'
import { storeLabel } from './presentation'
import type { Asset, Workspace } from './api'
import { desk, loadPage, resultPage } from './session'
const props=defineProps<{workspace:Workspace; cases:Asset[]; casesComplete:boolean; disabled:boolean}>()
const emit=defineEmits<{open:[record:any];case:[id:string];more:[]}>()
const {store,query,queue,kind}=toRefs(desk)
const page=computed(()=>resultPage('desk:'+store.value))
const records=computed<any[]>(()=>page.value.data?.items || [])
const complete=computed(()=>!!page.value.data?.complete),loading=computed(()=>page.value.loading),error=computed(()=>page.value.error),updated=computed(()=>page.value.updated)
const kinds=[{key:'reviews',name:'商品评价'},{key:'feedback',name:'订单反馈'},{key:'tickets',name:'售后工单'}]
const rows=computed(()=>records.value.map(r=>{
  const asset=props.cases.find(c=>c.body.erpStoreName===store.value && (r.kind==='tickets'
    ? c.body.erpTicketId===r.ticketId : c.body.erpVoiceId===r.recordId && c.body.erpVoiceKind===r.kind))
  const handled=asset?.state==='HANDLED'
  const pending=['PREPARED','SENDING','PENDING'].includes(asset?.body.confirmation?.status)
  return {...r,asset,handled,pending,product:asset?.body.identity || r.identity,
    text:asset?.body.messages?.filter((m:any)=>m.role==='CUSTOMER').at(-1)?.text || r.text || r.title}
}))
const done=computed(()=>rows.value.filter(r=>r.handled).length)
const visible=computed(()=>rows.value.filter(r=>(queue.value==='ALL' || (queue.value==='HANDLED'?r.handled:!r.handled)) && (kind.value==='ALL' || kind.value===r.kind)
  && (!query.value || [r.text,r.title,r.product?.name,r.product?.sku,r.ticketNumber].some(v=>v?.toLowerCase().includes(query.value.toLowerCase())))))
const skuCount=computed(()=>props.workspace.sourceProductCounts?.[store.value] ?? new Set(rows.value.map(r=>r.product?.sku).filter(Boolean)).size)
async function load(force=true){
  const ownStore=store.value;if(!ownStore)return
  await loadPage('desk:'+ownStore,async()=>{
    const results=await Promise.all(kinds.map(async k=>{
      const q=new URLSearchParams({store:ownStore,kind:k.key,full:'true'})
      const result=await request<any>('/source-inbox?'+q,{},undefined,60000,'/api/b/v1')
      return {...result,items:result.items.map((r:any)=>({...r,kind:k.key,storeName:ownStore}))}
    }))
    return {items:results.flatMap(r=>r.items),complete:results.every(r=>r.complete)}
  },force)
}
watch(()=>props.workspace.sourceStores,stores=>{if(!stores.includes(store.value))store.value=stores.find(s=>s.includes('SIM-AS-20261116')) || stores.at(-1) || ''},{immediate:true})
watch(store,()=>{void load(false)},{immediate:true})
function saveScroll(){desk.scroll=window.scrollY}
onMounted(()=>{void nextTick(()=>window.scrollTo(0,desk.scroll));window.addEventListener('scroll',saveScroll,{passive:true})})
onBeforeUnmount(()=>window.removeEventListener('scroll',saveScroll))
const count=(n:number)=>complete.value && props.casesComplete?String(n):'—'
</script>
<template>
  <div class="desk">
    <div class="desk-toolbar"><label>店铺<select v-model="store" :disabled="disabled"><option v-for="s in workspace.sourceStores" :key="s" :value="s">{{storeLabel(s)}}</option></select></label><div><small v-if="complete">{{updated}} 更新</small><button class="button small" :disabled="disabled || loading" @click="load(true)">{{loading?'读取中…':'刷新'}}</button></div></div>
    <div class="desk-kpis">
      <article><span class="metric-icon">▦</span><div><small>覆盖 SKU</small><strong>{{skuCount}}</strong></div></article>
      <article><span class="metric-icon">☷</span><div><small>客户问题</small><strong>{{count(rows.length)}}</strong><span v-if="complete" class="breakdown">评价 {{rows.filter(r=>r.kind==='reviews').length}} · 反馈 {{rows.filter(r=>r.kind==='feedback').length}} · 工单 {{rows.filter(r=>r.kind==='tickets').length}}</span></div></article>
      <article class="todo"><span class="metric-icon">◷</span><div><small>待处理</small><strong>{{count(rows.length-done)}}</strong></div></article>
      <article class="done"><span class="metric-icon">✓</span><div><small>已处理</small><strong>{{count(done)}}</strong></div><span v-if="complete && casesComplete && rows.length" class="completion">{{Math.round(done/rows.length*100)}}%</span></article>
    </div>
    <p v-if="!casesComplete" class="banner">处理记录尚未读全。<button class="button small" :disabled="disabled" @click="emit('more')">加载更多</button></p>
    <p v-if="error" class="banner danger" role="alert">{{error}}</p>
    <section class="panel desk-queue">
      <div class="queue-toolbar"><div class="queue-tabs"><button v-for="q in [{key:'TODO',name:'待处理'},{key:'HANDLED',name:'已处理'},{key:'ALL',name:'全部'}]" :key="q.key" :class="{active:queue===q.key}" @click="queue=q.key">{{q.name}}</button></div><div class="queue-filters"><select v-model="kind" aria-label="问题类型"><option value="ALL">全部类型</option><option v-for="k in kinds" :key="k.key" :value="k.key">{{k.name}}</option></select><input v-model="query" aria-label="搜索客户问题" placeholder="搜索问题、商品或 SKU"></div></div>
      <div v-if="loading && !records.length" class="empty" role="status">正在读取客户问题…</div>
      <div v-else-if="!visible.length" class="empty"><span>✓</span><p>{{queue==='HANDLED'?'暂无已处理记录':query?'没有匹配的问题':'当前没有待处理问题'}}</p></div>
      <div v-else class="table-scroll"><table><colgroup><col class="col-problem"><col class="col-product"><col class="col-kind"><col class="col-status"><col class="col-action"></colgroup><thead><tr><th>客户问题</th><th>商品</th><th>类型</th><th>状态</th><th></th></tr></thead><tbody><tr v-for="r in visible" :key="r.kind+(r.ticketId || r.recordId)"><td class="problem"><button :title="r.text" @click="r.asset?emit('case',r.asset.id):emit('open',r)">{{r.text}}</button><small v-if="r.rating">{{'★'.repeat(Math.max(0,Math.min(5,r.rating)))}}<span class="rating-rest">{{'☆'.repeat(Math.max(0,5-r.rating))}}</span></small><small v-else>{{r.ticketNumber || r.businessDate || '—'}}</small></td><td class="product-cell"><b :title="r.product?.name || '待核实'">{{r.product?.name || '待核实'}}</b><small :title="r.product?.sku || '—'">{{r.product?.sku || '—'}}</small></td><td class="kind-cell">{{kinds.find(k=>k.key===r.kind)?.name}}</td><td class="state-cell"><span class="status" :class="{done:r.handled,pending:r.pending}">{{r.handled?'已处理':r.pending?'保存待核验':r.asset?.state==='REVIEW_PENDING'?'待确认':'待处理'}}</span></td><td class="action-cell"><button class="button small" :disabled="disabled" @click="r.asset?emit('case',r.asset.id):emit('open',r)">{{r.handled?'查看':'处理 →'}}</button></td></tr></tbody></table></div>
      <div v-if="complete" class="queue-footer">{{visible.length}} 条</div>
    </section>
  </div>
</template>
<style scoped>
.desk-toolbar,.desk-toolbar>div,.queue-toolbar,.queue-filters{display:flex;align-items:center;gap:14px}.desk-toolbar{justify-content:space-between;margin:0 0 20px}.desk-toolbar label{display:flex;align-items:center;gap:12px;font-size:13px}.desk-toolbar small{color:#7a8c96;font-size:12px}select,input{border:1px solid #d5e0e6;border-radius:7px;padding:9px 12px;font:inherit;font-size:13px;background:#fff;color:#2d4859;min-width:0}.desk-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-bottom:24px}.desk-kpis article{display:flex;align-items:flex-start;gap:14px;padding:24px 20px;background:#fff;border:1px solid #dce5eb;border-radius:10px;position:relative;min-width:0}.metric-icon{display:grid;place-items:center;width:38px;height:38px;background:#edf3f8;border-radius:10px;font-size:24px;color:#577a96;flex-shrink:0}.desk-kpis small{font-size:12px;color:#728692;display:block}.desk-kpis strong{display:block;font-size:32px;font-weight:600;line-height:1.5;font-variant-numeric:tabular-nums;color:#263f50}.breakdown{font-size:11px;color:#728692;white-space:nowrap}.todo .metric-icon{color:#b07832;background:#fff4df}.done .metric-icon{color:#247e6d;background:#e8f5ef}.completion{position:absolute;right:18px;top:20px;font-size:12px;color:#247e6d}.desk-queue{overflow:hidden}.queue-toolbar{justify-content:space-between;padding:0 20px;border-bottom:1px solid #e4ebef;flex-wrap:wrap}.queue-tabs{display:flex;gap:22px}.queue-tabs button{padding:18px 0;border:0;border-bottom:2px solid transparent;background:none;color:#718390;cursor:pointer;font:inherit;font-size:14px}.queue-tabs button.active{color:#167368;border-color:#167368;font-weight:600}.queue-filters{padding:10px 0}.queue-filters input{width:230px}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}th{font-weight:500;font-size:12px;color:#718390;background:#f7f9fb;padding:14px 20px}td{padding:20px;border-bottom:1px solid #e9eef2;vertical-align:middle}td b{font-weight:500}td small{display:block;color:#84939e;font-size:11px;margin-top:8px}.problem{width:42%;min-width:260px}.problem>button{border:0;background:none;text-align:left;font:inherit;line-height:1.7;color:#254c61;padding:0;cursor:pointer;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.problem small{color:#c4943e}.rating-rest{color:#b6c1c8}.status{display:inline-block;padding:5px 9px;color:#99732f;background:#fff5df;border-radius:5px;white-space:nowrap;font-size:12px}.status.done{color:#2a7c63;background:#eaf5ef}.status.pending{color:#496c91;background:#edf3fb}.empty{text-align:center;padding:65px 20px;color:#7e909b;font-size:14px}.empty>span{display:block;font-size:30px;color:#91afa5}.queue-footer{padding:14px 20px;font-size:12px;color:#81919b}@media(max-width:1100px){.desk-kpis{gap:10px}.desk-kpis article{padding:20px 14px;gap:8px}.metric-icon{width:30px;height:30px;font-size:20px}.breakdown{white-space:normal}.completion{position:static;margin-left:auto}}@media(max-width:700px){.desk-kpis{grid-template-columns:1fr 1fr}.desk-toolbar{align-items:flex-start}.desk-toolbar label{display:grid}.desk-toolbar select{max-width:250px}.queue-filters{width:100%}.queue-filters input{flex:1;width:100px}.queue-toolbar{padding-inline:14px}}
table{table-layout:fixed;width:100%}.col-problem{width:40%}.col-product{width:22%}.col-kind{width:13%}.col-status{width:14%}.col-action{width:11%}th{padding-inline:14px}td{padding:16px 14px;min-width:0}.problem>button{width:100%;line-height:1.55;overflow-wrap:anywhere}.product-cell{overflow:hidden}.product-cell b,.product-cell small{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.kind-cell,.state-cell,.action-cell{white-space:nowrap}.status{font-size:11px;padding:5px 8px}.action-cell .button{max-width:100%}@media(max-width:700px){.col-problem{width:38%}.col-product{width:24%}.col-kind{width:14%}.col-status{width:14%}.col-action{width:10%}.table-scroll{overflow-x:auto}}
</style>
