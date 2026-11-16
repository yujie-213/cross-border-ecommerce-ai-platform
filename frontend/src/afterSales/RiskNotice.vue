<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import type { QualityRiskAdvisory } from '../api/v2'
import { route, href } from '../router'
const props=defineProps<{advisory?:QualityRiskAdvisory;history?:QualityRiskAdvisory;histories?:QualityRiskAdvisory[];scopes?:QualityRiskAdvisory[];compact?:boolean}>()
const tick=ref(Date.now());let timer:ReturnType<typeof setInterval>
onMounted(()=>{timer=setInterval(()=>{tick.value=Date.now()},5000)})
onBeforeUnmount(()=>clearInterval(timer))
const values=computed(()=>props.scopes?.length?props.scopes:props.advisory?[props.advisory]:[])
const fresh=computed(()=>values.value.length>0 && values.value.every(a=>Number.isFinite(Date.parse(a.checkedAt)) && tick.value>=Date.parse(a.checkedAt) && tick.value-Date.parse(a.checkedAt)<60000))
const past=computed(()=>props.histories?.length?props.histories:props.history?[props.history]:[])
const historicalRefs=computed(()=>past.value.flatMap(p=>p.riskRefs))
const refs=computed(()=>fresh.value?values.value.flatMap(a=>a.status==='MATCHED'?a.riskRefs.filter(r=>tick.value<Date.parse(r.validUntil)):[]):[])
const unknown=computed(()=>values.value.length>0 && (!fresh.value || values.value.some(a=>a.status==='UNVERIFIED')))
const back=computed(()=>route.value.path+(Object.keys(route.value.query).length?'?'+new URLSearchParams(route.value.query).toString():''))
</script>
<template><aside v-if="refs.length" class="quality-risk" :class="{compact}"><b>售后质量风险提醒</b><div v-for="r in refs" :key="r.riskId+r.version"><a :href="href('/after-sales/risks',{id:r.riskId,returnTo:back})">{{r.reason}} →</a><small v-if="!compact">{{r.sourceNature==='MIDDLEWARE_TEACHING_DATA'?'教学风险演示':'已人工确认'}} · {{r.limitations}} · 有效至 {{r.validUntil}}</small></div></aside><p v-if="unknown" class="small muted" role="status">售后风险查询未完成，当前状态未核实，请刷新核查。</p><details v-if="historicalRefs.length" class="quality-risk"><summary>分析时保存的历史风险（与当前状态分列）</summary><p>当时核查：{{past.map(p=>p.checkedAt).join('、')}}</p><p v-for="r in historicalRefs" :key="r.riskId">{{r.reason}} · 版本 {{r.version}}，请以当前核查结果判断是否仍有效。</p></details></template>
<style scoped>.quality-risk{margin:15px 0;padding:16px;background:#fff7e8;border:1px solid #eed8ad;border-radius:8px;font-size:14px;color:#79511f}.quality-risk a{display:block;color:#8e5816;margin-top:8px}.quality-risk small{display:block;margin-top:8px;font-size:12px;line-height:1.7}.quality-risk.compact{padding:7px 9px;font-size:12px;margin:8px 0;max-width:260px}.quality-risk.compact a{margin-top:4px}</style>
