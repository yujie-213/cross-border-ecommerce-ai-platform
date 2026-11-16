<script setup lang="ts">
import { computed,ref } from 'vue'
import type { Asset } from './api'
import { href } from '../router'
const props=defineProps<{cases:Asset[]}>()
const emit=defineEmits<{open:[id:string]}>()
const selected=ref('')
const products=computed(()=>{
  const groups=new Map<string,{key:string;name:string;sku:string;cases:Asset[]}>()
  for(const c of props.cases){const i=c.body.identity;if(!i)continue;const key=[c.scope.sourceTenant,i.storeId,i.productId].join(':');if(!groups.has(key))groups.set(key,{key,name:i.name,sku:i.sku,cases:[]});groups.get(key)!.cases.push(c)}
  return [...groups.values()].sort((a,b)=>b.cases.length-a.cases.length)
})
const focus=computed(()=>products.value.find(p=>p.key===selected.value) || products.value[0])
</script>
<template>
 <section class="panel case-products"><div class="section-title"><h2>商品问题分布</h2><small>已接入售后记录</small></div>
  <div v-if="products.length" class="table-scroll"><table><thead><tr><th>商品</th><th>客户问题</th><th>待处理</th><th></th></tr></thead><tbody><tr v-for="p in products" :key="p.key" :class="{selected:focus?.key===p.key}"><td><b>{{p.name}}</b><small>{{p.sku}}</small></td><td>{{p.cases.length}} 条</td><td>{{p.cases.filter(c=>c.state!=='HANDLED').length}} 条</td><td><button class="button small" @click="selected=p.key">查看问题</button></td></tr></tbody></table></div>
  <p v-else class="empty">接入售后记录后，可在这里查看商品问题。</p>
 </section>
 <section v-if="focus" class="panel customer-issues"><div class="section-title"><h2>{{focus.name}}</h2><small>{{focus.cases.length}} 条售后记录</small></div><article v-for="c in focus.cases" :key="c.id"><div><h3>{{c.body.title}}</h3><p>{{c.body.messages.at(-1)?.text || c.body.title}}</p></div><a class="button small" :href="href('/after-sales/cases',{id:c.id,source:'ERP'})">查看并调查</a></article></section>
</template>
<style scoped>
.case-products,.customer-issues{margin:20px 0;overflow:hidden}.section-title{padding:20px;display:flex;justify-content:space-between;gap:18px;align-items:center}.section-title h2{margin:0;font-size:17px}small{color:#71818b;font-size:12px}table{width:100%;border-collapse:collapse;font-size:13px;text-align:left}th{padding:14px 20px;font-weight:500;color:#71818b;background:#f7f9fa}td{padding:18px 20px;border-top:1px solid #e4eaee}td small{display:block;margin-top:6px}.selected{background:#f3f8f6}.table-scroll{overflow:auto}.customer-issues article{display:flex;gap:24px;align-items:center;justify-content:space-between;padding:20px;border-top:1px solid #e5ebef}.customer-issues article>div{min-width:0}.customer-issues h3{font-size:14px;margin:0 0 10px}.customer-issues p{font-size:13px;line-height:1.8;margin:0;white-space:pre-wrap}.customer-issues a{flex-shrink:0}.empty{padding:0 20px 20px;color:#71818b;font-size:13px}@media(max-width:760px){.customer-issues article{align-items:start;flex-direction:column}td,th{padding:12px}}
</style>
