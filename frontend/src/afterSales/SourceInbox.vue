<script setup lang="ts">
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { storeLabel } from './presentation'
import { request, errorText } from '../api/client'
const props=defineProps<{stores:string[]; initialKind?:string; disabled?:boolean; embedded?:boolean}>()
const emit=defineEmits<{open:[record:any]}>()
const store=ref(''),kind=ref(props.initialKind || 'tickets'),loading=ref(false),error=ref(''),result=ref<any>(),search=ref('')
const expanded=ref(false)
const selectedProduct=ref('')
const products=computed(()=>{
 const groups=new Map<string,{key:string;name:string;sku:string;items:any[]}>()
 for(const r of rows.value){const key=r.identity?[r.identity.sourceTenant,r.identity.storeId,r.identity.productId].join(':'):'unresolved';if(!groups.has(key))groups.set(key,{key,name:r.identity?.name || '商品待核实',sku:r.identity?.sku || '',items:[]});groups.get(key)!.items.push(r)}
 return [...groups.values()].sort((a,b)=>Number(a.key==='unresolved')-Number(b.key==='unresolved'))
})
const visibleRows=computed(()=>expanded.value?rows.value:rows.value.slice(0,4))
const from=ref(''),to=ref('');let generation=0
const rows=computed(()=>(result.value?.items || []).filter((r:any)=>!search.value || [r.title,r.text,r.identity?.name,r.identity?.sku,r.ticketNumber].some(v=>v?.includes(search.value))))
async function load(){
 const own=++generation;result.value=undefined;expanded.value=false;selectedProduct.value='';error.value='';if(!store.value)return
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
 <section class="panel inbox" :class="{embedded}">
  <div class="inbox-head"><div><h2>{{kind==='tickets'?'新到客户问题':'商品评价与客户反馈'}}</h2></div><button class="button small" :disabled="loading || disabled || !store" @click="load">更新记录</button></div>
  <div class="filters"><label>店铺<select v-model="store" :disabled="loading"><option v-for="s in stores" :key="s">{{storeLabel(s)}}</option></select></label><label v-if="initialKind==='reviews'">业务记录<select v-model="kind"><option value="reviews">商品评价</option><option value="feedback">订单反馈</option></select></label><label>查找当前记录<input v-model="search" placeholder="商品、SKU 或问题关键词"></label></div>
  <details v-if="kind!=='tickets'"><summary>按反馈日期筛选</summary><form class="filters" @submit.prevent="load"><label>开始日期<input type="date" v-model="from"></label><label>结束日期<input type="date" v-model="to" :min="from"></label><button class="button" :disabled="loading">查看这段时间</button></form></details>
  <p v-if="!stores.length" class="banner warning">暂无可用店铺。</p>
  <p v-if="loading" role="status">正在读取客户问题…</p>
  <p v-if="error" class="banner danger" role="alert">{{error}}，请稍后重试。</p>
  <template v-if="result"><p class="source-boundary">本次读取 {{result.items.length}} 条记录{{result.complete?'':' · 当前为部分查询'}} · {{new Date(result.observedAt).toLocaleString()}}</p>
   <template v-if="kind==='reviews'"><div class="table-scroll"><table><thead><tr><th>商品</th><th>本次反馈</th><th>需要关注的问题</th><th></th></tr></thead><tbody><tr v-for="p in products" :key="p.key"><td><b>{{p.name}}</b><small>{{p.sku}}</small></td><td>{{p.items.length}} 条</td><td>{{p.items[0].title}}<small>{{p.items[0].text.slice(0,55)}}</small></td><td><button class="button small" @click="selectedProduct=selectedProduct===p.key?'':p.key">查看商品反馈</button></td></tr></tbody></table></div><div v-if="selectedProduct" class="product-voices"><h3>{{products.find(p=>p.key===selectedProduct)?.name}} · 客户反馈原文</h3><article v-for="r in products.find(p=>p.key===selectedProduct)?.items || []" :key="r.recordId" class="source-record"><div><p>{{r.text}}</p><small>{{r.rating==null?'未提供评分':r.rating+' / 5 分'}} · {{r.businessDate || '日期未提供'}}</small></div><button class="button small" :disabled="disabled" @click="emit('open',{...r,kind,storeName:store})">打开处理</button></article></div></template>
   <div v-else class="table-scroll"><table><thead><tr><th>客户问题</th><th>业务关联</th><th>下一步</th></tr></thead><tbody><tr v-for="r in visibleRows" :key="r.ticketId || r.recordId"><td><b>{{r.title}}</b><small v-if="r.text">{{r.text.slice(0,80)}}</small></td><td><small>{{r.association || (r.orderLinked?'已关联订单':'订单待核实')}}</small></td><td><button class="button small" :disabled="disabled || loading" @click="emit('open',{...r,kind,storeName:store})">打开处理 →</button></td></tr></tbody></table></div>
   <button v-if="rows.length>4" class="button small" @click="expanded=!expanded">{{expanded?'收起其他记录':'展开本次其余 '+(rows.length-4)+' 条记录'}}</button><p v-if="!rows.length" class="empty-inline">当前读取范围内没有符合条件的记录，可更换店铺或日期。</p>
  </template>
 </section>
</template>
<style scoped>
.inbox{padding:20px;margin:20px 0}.inbox.embedded{margin:0;border:0;border-radius:0;box-shadow:none}td:first-child{max-width:330px}td>b{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.7}.inbox-head,.source-record{display:flex;align-items:center;justify-content:space-between;gap:18px}.inbox-head h2{font-size:17px;margin:0 0 6px}.inbox-head p,.source-boundary{color:#71818b;font-size:12px;line-height:1.7}.filters{display:flex;gap:12px;align-items:end;flex-wrap:wrap}.filters label{display:grid;gap:7px;flex:1;min-width:140px;font-size:12px;color:#42616b;margin:12px 0}.filters input,.filters select{padding:8px;border:1px solid #cad7dd;border-radius:5px;min-width:0;width:100%;font:inherit}.source-record{padding:14px 0;border-top:1px solid #e2e9ed;font-size:13px}.source-record small,td small{display:block;color:#71818b;font-size:12px;line-height:1.7;margin-top:5px}.source-record button{flex-shrink:0}.table-scroll{overflow:auto}table{width:100%;text-align:left;font-size:13px;border-collapse:collapse}th{font-size:12px;color:#71818b;background:#f7f9fb;padding:12px;font-weight:500}td{padding:16px 12px;border-top:1px solid #e4ebef}summary{color:#42636b;cursor:pointer;margin:10px 0;font-size:12px}.product-voices{padding-top:12px}.product-voices h3{font-size:15px}@media(max-width:750px){.source-record,.inbox-head{align-items:start;flex-direction:column}.inbox{padding:18px}}
</style>
