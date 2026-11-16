<script setup lang="ts">
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { request, errorText } from '../api/client'
const props=defineProps<{stores:string[]; initialKind?:string; disabled?:boolean}>()
const emit=defineEmits<{open:[record:any]}>()
const store=ref(''),kind=ref(props.initialKind || 'tickets'),loading=ref(false),error=ref(''),result=ref<any>(),search=ref('')
const expanded=ref(false)
const visibleRows=computed(()=>expanded.value?rows.value:rows.value.slice(0,4))
const from=ref(''),to=ref('');let generation=0
const rows=computed(()=>(result.value?.items || []).filter((r:any)=>!search.value || [r.title,r.text,r.identity?.name,r.identity?.sku,r.ticketNumber].some(v=>v?.includes(search.value))))
async function load(){
 const own=++generation;result.value=undefined;expanded.value=false;error.value='';if(!store.value)return
 loading.value=true
 const q=new URLSearchParams({store:store.value,kind:kind.value});if(from.value)q.set('dateFrom',from.value);if(to.value)q.set('dateTo',to.value)
 try{const value=await request<any>('/source-inbox?'+q,{},undefined,60000,'/api/b/v1');if(own===generation)result.value=value}
 catch(e){if(own===generation)error.value=errorText(e)}finally{if(own===generation)loading.value=false}
}
watch(()=>props.stores,stores=>{if(!stores.includes(store.value))store.value=stores[0] || ''},{immediate:true})
watch([store,kind],load,{immediate:true})
onBeforeUnmount(()=>generation++)
</script>
<template>
 <section class="panel inbox">
  <div class="inbox-head"><div><h2>{{kind==='tickets'?'从 ERP 待办开始':'从商品评价与客户反馈开始'}}</h2><p>教学 ERP 只读数据 · 与中台独立教学资料分开使用</p></div><button class="button" :disabled="loading || disabled || !store" @click="load">更新 ERP 记录</button></div>
  <div class="filters"><label>店铺<select v-model="store" :disabled="loading"><option v-for="s in stores" :key="s">{{s}}</option></select></label><label>业务记录<select v-model="kind"><option value="tickets">售后工单</option><option value="reviews">商品评价</option><option value="feedback">订单反馈</option></select></label><label>查找当前记录<input v-model="search" placeholder="商品、SKU 或问题关键词"></label></div>
  <details v-if="kind!=='tickets'"><summary>按反馈日期筛选</summary><form class="filters" @submit.prevent="load"><label>开始日期<input type="date" v-model="from"></label><label>结束日期<input type="date" v-model="to" :min="from"></label><button class="button" :disabled="loading">查看这段时间</button></form></details>
  <p v-if="!stores.length" class="banner warning">尚未配置可读 ERP 店铺，请联系管理员；可在独立教学资料中体验完整流程。</p>
  <p v-if="loading" role="status">正在读取 ERP 记录并核实商品关联…</p>
  <p v-if="error" class="banner danger" role="alert">{{error}}。本次记录未读取成功，请稍后更新；不代表没有业务问题。</p>
  <template v-if="result"><p class="source-boundary">本次显示 {{result.items.length}} 条{{result.complete?'，已读完当前筛选范围':'，仅为有界查询的一部分'}} · {{new Date(result.observedAt).toLocaleString()}}<br v-if="kind!=='tickets'"><span v-if="kind!=='tickets'">{{result.limitation}}</span></p>
   <article v-for="r in visibleRows" :key="r.ticketId || r.recordId" class="source-record"><div><span class="chip plain">{{kind==='tickets'?'ERP 工单':kind==='reviews'?'ERP 商品评价':'ERP 订单反馈'}}</span><span v-if="r.rating!=null" class="rating">{{r.rating}} / 5 分</span><h3>{{r.title}}</h3><p v-if="r.text" class="voice-text">{{r.text}}</p><p v-if="r.identity"><b>{{r.identity.name}}</b> · {{r.identity.sku}}</p><small>{{r.association || (r.orderLinked?'已有订单线索，打开后自动核实商品明细':'订单缺失，打开后保留问题并补证')}}</small><small v-if="r.businessDate">反馈日期 {{r.businessDate}}</small></div><button class="button primary" :disabled="disabled || loading" @click="emit('open',{...r,kind,storeName:store})">{{kind==='tickets'?'打开处理':'查看商品与分析'}}</button></article>
   <button v-if="rows.length>4" class="button small" @click="expanded=!expanded">{{expanded?'收起其他记录':'展开本次其余 '+(rows.length-4)+' 条记录'}}</button><p v-if="!rows.length" class="empty-inline">当前读取范围内没有符合条件的记录，可更换店铺或日期。</p>
  </template>
 </section>
</template>
<style scoped>
.inbox{padding:24px;margin:22px 0}.inbox-head,.source-record{display:flex;align-items:center;justify-content:space-between;gap:22px}.inbox-head h2{font-size:19px;margin:0 0 8px}.inbox-head p,.source-boundary{color:#687c88;font-size:13px;line-height:1.7}.filters{display:flex;gap:16px;align-items:end;flex-wrap:wrap}.filters label{display:grid;gap:8px;flex:1;min-width:150px;font-size:14px;color:#42616b;margin:12px 0}.filters input,.filters select{padding:10px;border:1px solid #cad7dd;border-radius:6px;min-width:0;width:100%;font:inherit}.source-record{padding:20px 0;border-top:1px solid #e2e9ed}.source-record>div{min-width:0}.source-record h3{font-size:16px;line-height:1.6;margin:10px 0}.source-record p{line-height:1.7}.source-record small{display:block;color:#687c88;line-height:1.7}.source-record button{flex-shrink:0}.voice-text{white-space:pre-wrap;overflow-wrap:anywhere;max-height:160px;overflow:auto}.rating{font-size:13px;color:#855b16;margin-left:12px}summary{color:#42636b;cursor:pointer;margin:12px 0}@media(max-width:750px){.source-record,.inbox-head{align-items:start;flex-direction:column}.inbox{padding:18px}}
</style>
