<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { type Asset, type Workspace } from './api'
import { storeLabel } from './presentation'
import { ApiError, errorText, request } from '../api/client'

const props=defineProps<{workspace:Workspace;cases:Asset[];investigations:Asset[];disabled:boolean}>()
const emit=defineEmits<{openInvestigation:[id:string];investigateReturn:[body:{store:string;returnId:string;sku:string}];investigateSku:[body:{store:string;sku:string;endDate:string;windowDays:number}]}>()
const localDate=()=>{const now=new Date();return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`}
const view=ref<'returns'|'monitor'>('returns'),store=ref(''),windowDays=ref(7),endDate=ref(localDate())
const data=ref<any>(),loading=ref(false),error=ref(''),selected=ref<any>(),query=ref(''),generation=ref(0)
const selectedSku=ref<any>()
const visibleReturns=computed(()=> (data.value?.items||[]).filter((r:any)=>!query.value || [r.returnNo,r.orderNumber,r.productName,r.sku,r.reason].some((v:any)=>String(v||'').toLowerCase().includes(query.value.toLowerCase()))))
const flagged=(row:any)=>row.evaluated && row.anomalyReasons?.length>0
const stateNames:Record<string,string>={draft:'草稿',authorized:'已授权',received:'已实收',refunded:'已退款',cancelled:'已取消'}
async function load(){
  const own=++generation.value;loading.value=true;error.value='';data.value=undefined;selected.value=undefined
  selectedSku.value=undefined
  try{const q=new URLSearchParams({store:store.value,endDate:endDate.value,windowDays:String(windowDays.value)});const result=await request<any>('/return-analysis?'+q,{},undefined,120000,'/api/b/v1')
    if(own===generation.value)data.value=result
  }catch(e){if(own===generation.value)error.value=e instanceof ApiError && e.code==='OWNED_SCOPE_REQUIRED'?'当前店铺没有已登记的商品销售范围。':errorText(e)}finally{if(own===generation.value)loading.value=false}
}
watch(()=>props.workspace.sourceStores,stores=>{if(!stores.includes(store.value))store.value=stores[0]||''},{immediate:true})
watch([store,endDate,windowDays],()=>{if(store.value)void load()},{immediate:true})
function relatedInvestigation(row:any,kind:'return'|'monitor'){
  const sources=props.cases.filter(c=>c.body.erpStoreName===store.value && c.body.identity?.sku===row.sku && (kind==='monitor' || c.body.erpReturnId===row.id))
  return props.investigations.find(i=>sources.some(c=>i.body.origin.id===c.id || i.body.relatedSources?.some((r:any)=>r.id===c.id)))
}
const investigationLabel=(inv:Asset)=>({OPEN:'调查中',NEEDS_EVIDENCE:'待补证',SUPPORTED:'证据支持',REJECTED:'已排除'} as Record<string,string>)[inv.state] || '已有调查'
function investigateReturn(row:any){const inv=relatedInvestigation(row,'return');if(inv){emit('openInvestigation',inv.id);return}emit('investigateReturn',{store:store.value,returnId:row.id,sku:row.sku})}
function investigateSku(row:any){const inv=relatedInvestigation(row,'monitor');if(inv){emit('openInvestigation',inv.id);return}emit('investigateSku',{store:store.value,sku:row.sku,endDate:endDate.value,windowDays:windowDays.value})}
const percent=(n:any)=>n==null?'—':`${Number(n).toFixed(1)}%`
</script>

<template>
  <div class="analysis">
    <div class="filters">
      <label>店铺<select v-model="store" :disabled="disabled || loading"><option v-for="s in workspace.sourceStores" :key="s" :value="s">{{storeLabel(s)}}</option></select></label>
      <template v-if="view==='monitor'"><label>窗口天数<select v-model.number="windowDays"><option :value="7">7 天</option><option :value="14">14 天</option><option :value="30">30 天</option></select></label><label>截至日期<input v-model="endDate" type="date"></label></template>
      <button class="button small" :disabled="disabled || loading" @click="load">{{loading?'读取中…':'刷新'}}</button>
    </div>
    <nav class="views" aria-label="退货与商品分析"><button :class="{active:view==='returns'}" @click="view='returns'">退货订单 <span>{{data?.items?.length ?? '—'}}</span></button><button :class="{active:view==='monitor'}" @click="view='monitor'">商品监测 <span>{{data?.monitor?.length ?? '—'}}</span></button></nav>
    <p v-if="error" class="error" role="alert">{{error}}</p>
    <p v-else-if="data && !data.complete" class="warning">ERP 读取不完整，本次结果不用于判断异常。</p>
    <template v-if="view==='returns'">
      <div class="table-tools"><input v-model="query" placeholder="搜索退货单、商品或原因" aria-label="搜索退货单"><span>{{visibleReturns.length}} 条</span></div>
      <div v-if="loading" class="empty">正在读取退货记录…</div>
      <div v-else-if="!error && !visibleReturns.length" class="empty">暂无已登记订单的退货记录</div>
      <div v-else-if="!error" class="table-wrap"><table class="return-table"><colgroup><col class="col-return"><col class="col-product"><col class="col-reason"><col class="col-quantity"><col class="col-state"><col class="col-action"></colgroup><thead><tr><th>退货单 / 订单</th><th>商品</th><th>客户原因</th><th>数量</th><th>状态</th><th></th></tr></thead><tbody><tr v-for="r in visibleReturns" :key="r.id+':'+r.sku" :class="{chosen:selected?.id===r.id && selected?.sku===r.sku}" @click="selected=r"><td><b>{{r.returnNo || `退货 ${r.id}`}}</b><small>{{r.orderNumber || r.orderId}}</small></td><td><b class="clip" :title="r.productName">{{r.productName}}</b><small>{{r.sku}}</small></td><td><span class="clip reason" :title="r.reason">{{r.reason || '未填写原因'}}</span></td><td>{{r.quantity}}</td><td><span class="state" :class="r.state">{{stateNames[r.state] || r.state}}</span></td><td><button class="button small" :disabled="disabled" @click.stop="investigateReturn(r)">{{relatedInvestigation(r,'return')?'查看调查':'发起调查'}}</button><small v-if="relatedInvestigation(r,'return')">{{investigationLabel(relatedInvestigation(r,'return')!)}}</small></td></tr></tbody></table></div>
      <section v-if="selected" class="detail"><div><h3>{{selected.productName}} · {{selected.sku}}</h3><p>{{selected.reason || '未填写退货原因'}}</p><small>退货单 {{selected.returnNo || selected.id}} · 订单 {{selected.orderNumber || selected.orderId}} · {{selected.quantity}} 件</small></div><dl><div><dt>退货状态</dt><dd>{{stateNames[selected.state] || selected.state}}</dd></div><div v-if="selected.receivedAt"><dt>实收时间</dt><dd>{{selected.receivedAt}}</dd></div><div v-if="selected.quality?.length"><dt>收货检查</dt><dd>{{selected.quality.filter((q:any)=>q.sku===selected.sku).map((q:any)=>`${q.sku}: 合格 ${q.good_qty} / 异常 ${q.bad_qty}`).join('；')}}</dd></div></dl></section>
    </template>
    <template v-else>
      <div v-if="data?.window" class="window-head"><span>{{data.window.previousStart}} 至 {{data.window.endDate}}</span><span>销售批次对比 · 低星 ≤ 2 星</span></div>
      <div v-if="loading" class="empty">正在比较商品趋势…</div>
      <div v-else-if="!error && !data?.monitor?.length" class="empty">没有可比较的已发货商品</div>
      <div v-else-if="!error && data?.monitor?.length" class="table-wrap"><table class="monitor-table"><colgroup><col class="col-product"><col class="col-samples"><col class="col-rates"><col class="col-reviews"><col class="col-signal"><col class="col-action"></colgroup><thead><tr><th>商品</th><th>批次发货件数<br><small>上期 / 本期</small></th><th>实收退货率<br><small>上期 / 本期</small></th><th>低星评价<br><small>数量 / 占比</small></th><th>判断</th><th></th></tr></thead><tbody><tr v-for="r in data.monitor" :key="r.sku" :class="{chosen:selectedSku?.sku===r.sku}" @click="selectedSku=r"><td><b class="clip" :title="r.name">{{r.name}}</b><small>{{r.sku}}</small></td><td>{{r.previous}} / {{r.current}}<small>订单 {{r.previousOrders}} / {{r.currentOrders}}</small></td><td>{{percent(r.previousReturnRate)}} / {{percent(r.currentReturnRate)}}<small>实收 {{r.previousReturns}} / {{r.currentReturns}}</small></td><td>{{r.previousLowReviews}} / {{r.currentLowReviews}}<small>{{percent(r.previousLowReviewRate)}} / {{percent(r.currentLowReviewRate)}}</small></td><td><span v-if="!r.evaluated" class="state draft">{{data.complete?'样本不足':'数据待核实'}}</span><span v-else-if="flagged(r)" class="state received">需调查</span><span v-else class="state refunded">未见明显异常</span><small v-if="r.anomalyReasons?.length">{{r.anomalyReasons.join('、')}}</small></td><td><button class="button small" :disabled="disabled || !data.complete" @click.stop="investigateSku(r)">{{relatedInvestigation(r,'monitor')?'查看调查':'发起调查'}}</button><small v-if="relatedInvestigation(r,'monitor')">{{investigationLabel(relatedInvestigation(r,'monitor')!)}}</small></td></tr></tbody></table></div>
      <section v-if="selectedSku" class="sku-detail">
        <div class="detail-title"><h3>{{selectedSku.name}} · {{selectedSku.sku}}</h3><span>{{selectedSku.anomalyReasons?.join('、') || (selectedSku.evaluated?'未见明显异常':data.complete?'样本不足':'数据待核实')}}</span></div>
        <div class="rate-chart" role="img" :aria-label="`实收退货率：上期 ${percent(selectedSku.previousReturnRate)}，本期 ${percent(selectedSku.currentReturnRate)}`">
          <div v-for="period in ['previous','current']" :key="period"><span>{{period==='previous'?'上期':'本期'}}</span><div class="rate-track"><i :style="{width:Math.max(0,Math.min(100,selectedSku[period+'ReturnRate'] || 0))+'%'}"></i></div><b>{{percent(selectedSku[period+'ReturnRate'])}}</b></div>
        </div>
        <h4>退货与评价记录</h4><p v-if="!selectedSku.evidenceItems?.length" class="muted">暂无对应记录</p>
        <article v-for="item in selectedSku.evidenceItems" :key="item.sourceRef" class="source-record"><span>{{item.kind==='RETURN'?'退货':'评价'}}</span><div><p>{{item.text}}</p><small>{{item.businessDate}} · {{item.sourceRef}}</small></div></article>
      </section>
    </template>
  </div>
</template>

<style scoped>
.analysis{background:#fff;border:1px solid #dce5eb;min-width:0}.filters{display:flex;align-items:end;gap:12px;padding:16px 18px;border-bottom:1px solid #e4ebef;flex-wrap:wrap}.filters label{display:grid;gap:5px;font-size:12px;color:#657b88}.filters select,.filters input,.table-tools input{border:1px solid #d5e0e6;border-radius:5px;padding:8px 10px;background:#fff;color:#243b4b;font:inherit;min-width:0}.views{display:flex;gap:24px;padding:0 18px;border-bottom:1px solid #e4ebef}.views button{padding:14px 0;border:0;border-bottom:2px solid transparent;background:none;color:#637985;font:inherit;cursor:pointer}.views button.active{color:#176f69;border-color:#176f69;font-weight:600}.views span{padding-left:6px;color:#83939c;font-size:12px}.table-tools{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;color:#788a94;font-size:12px}.table-tools input{width:min(340px,70vw)}.table-wrap{width:100%;overflow:auto}table{width:100%;table-layout:fixed;border-collapse:collapse;text-align:left;font-size:13px}th{padding:12px 14px;background:#f6f8f9;color:#738590;font-size:12px;font-weight:500}td{padding:14px;border-top:1px solid #e7ecef;vertical-align:middle;min-width:0}td b,td small{display:block}td b{font-weight:550;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}td small{margin-top:5px;font-size:11px;color:#83929b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.return-table .col-return{width:17%}.return-table .col-product{width:19%}.return-table .col-reason{width:31%}.return-table .col-quantity{width:8%}.return-table .col-state{width:12%}.return-table .col-action{width:13%}.monitor-table .col-product{width:23%}.monitor-table .col-samples{width:15%}.monitor-table .col-rates{width:22%}.monitor-table .col-reviews{width:17%}.monitor-table .col-signal{width:12%}.monitor-table .col-action{width:11%}.clip{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}.reason{line-height:1.5;white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}.state{display:inline-block;padding:5px 8px;border-radius:4px;white-space:nowrap;font-size:11px;background:#edf2f5;color:#5c727e}.state.received{background:#fff1e7;color:#9b572d}.state.refunded{background:#eaf4ef;color:#36755b}.state.draft{background:#fff5df;color:#8a6b2e}.chosen{background:#f5faf8}.detail{display:grid;grid-template-columns:minmax(0,1fr) minmax(240px,35%);gap:24px;padding:18px;border-top:1px solid #dfe8eb}.detail h3{margin:0;font-size:14px}.detail p{margin:8px 0;line-height:1.7;white-space:pre-wrap}.detail small,.window-head{color:#7b8c96;font-size:12px}.detail dl{margin:0;font-size:12px}.detail dl>div{display:flex;justify-content:space-between;gap:10px;padding:5px 0}.detail dt{color:#7b8c96}.detail dd{margin:0;text-align:right}.window-head{display:flex;justify-content:space-between;gap:12px;padding:14px 18px;flex-wrap:wrap}.empty{text-align:center;padding:48px 16px;color:#748893;font-size:13px}.error,.warning{margin:14px 18px;padding:10px 12px;background:#fff3ee;color:#934f35;font-size:13px}.warning{background:#fff7e4;color:#86672e}.sku-detail{padding:20px;border-top:1px solid #dfe8eb}.detail-title{display:flex;align-items:center;justify-content:space-between;gap:16px}.detail-title h3{font-size:14px;margin:0}.detail-title span,.muted{color:#788a94;font-size:12px}.rate-chart{max-width:600px;display:grid;gap:12px;margin:24px 0}.rate-chart>div{display:flex;align-items:center;gap:12px;font-size:12px}.rate-chart b{width:60px;text-align:right}.rate-track{height:12px;flex:1;background:#edf2f4;border-radius:4px;overflow:hidden}.rate-track i{display:block;height:100%;background:#6ba39a}.rate-chart>div:last-child i{background:#cb8957}.source-record{display:flex;gap:16px;padding:12px 0;border-top:1px solid #e7ecef;font-size:13px}.source-record>span{flex-shrink:0;color:#738590}.source-record p{margin:0 0 6px;white-space:pre-wrap}.source-record small{color:#83929b}tr{cursor:pointer}tr td:last-child{cursor:default}@media(max-width:760px){.detail{grid-template-columns:1fr}.return-table{min-width:880px}.monitor-table{min-width:920px}}
</style>
