<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ModelUsage from '../components/ModelUsage.vue'
import { href } from '../router'
import { labelNames, type Asset } from './api'
const props = defineProps<{report:Asset; cases:Asset[]; busy:boolean}>()
const emit = defineEmits<{evidence:[id:string]; investigate:[value:{text:string; refs:string[]; productId:string}]; correct:[]}>()
const selected = ref(''), evidenceView = ref<'feedback'|'returns'|null>(null)
const products = computed(() => [...props.report.body.metrics.items].sort((a,b) => Number(b.finding==='NEEDS_INVESTIGATION')-Number(a.finding==='NEEDS_INVESTIGATION')))
watch(() => props.report.id, () => { selected.value=products.value[0]?.productId || ''; evidenceView.value=null }, {immediate:true})
const product = computed(() => products.value.find(p=>p.productId===selected.value))
const feedback = computed(() => props.report.body.feedback.filter((f:any)=>f.productId===selected.value).map((f:any)=>({...f,classification:[...(props.report.body.classificationCorrections || [])].reverse().find((c:any)=>c.feedbackId===f.feedbackId) || props.report.body.classifications.find((c:any)=>c.feedbackId===f.feedbackId)})))
const counts = computed(() => {
  const result:Record<string,number>={}
  for(const f of feedback.value)for(const label of new Set<string>(f.classification?.labels || ['UNKNOWN']))result[label]=(result[label] || 0)+1
  return Object.entries(result).sort((a,b)=>b[1]-a[1])
})
const ai = computed(() => props.report.body.productAI?.[selected.value])
const related = computed(() => props.cases.filter(c=>c.body.datasetId===props.report.body.datasetId && c.body.identity?.productId===selected.value))
const rate = (value:any) => value==null?'数据不足':value+'%'
function delta(value:any){return value==null?'暂无法比较':Number(value)>0?'上升 '+Number(value)+' 个百分点':Number(value)<0?'下降 '+Math.abs(Number(value))+' 个百分点':'与上期持平'}
function investigate(){emit('investigate',{text:ai.value?.output?.nextSteps?.join('；') || '核实'+product.value.name+'的客户反馈及退货原因',refs:feedback.value.map((f:any)=>f.feedbackId),productId:selected.value})}
</script>

<template>
  <section class="panel product-table">
    <div class="section-head"><h2>哪些商品需要优先关注？</h2><small>相同来源与口径 · 异常优先</small></div>
    <div class="table-scroll"><table><thead><tr><th>商品</th><th>本期退货率</th><th>上期退货率</th><th>变化</th><th>建议关注程度</th></tr></thead>
      <tbody><tr v-for="p in products" :key="p.productId+p.storeId" :class="{selected:selected===p.productId}"><td><button class="text-button" @click="selected=p.productId;evidenceView=null">{{p.name}}</button><small>{{p.sku}}</small></td><td><b>{{rate(p.groups[1].ratePercent)}}</b></td><td>{{rate(p.groups[0].ratePercent)}}</td><td>{{delta(p.deltaPercentagePoints)}}</td><td><span class="chip" :class="p.finding==='NEEDS_INVESTIGATION'?'warning':'plain'">{{p.finding==='NEEDS_INVESTIGATION'?'优先调查':p.finding==='UNKNOWN'?'待补数据':'常规观察'}}</span></td></tr></tbody>
    </table></div>
  </section>
  <section v-if="product" class="panel product-focus">
    <div class="section-head"><div><h2>{{product.name}} · {{product.finding==='NEEDS_INVESTIGATION'?'退货明显上升，建议优先调查':product.finding==='UNKNOWN'?'数据不足，先核实证据':'未触发退货异常'}}</h2><p>退货率{{Number(product.deltaPercentagePoints)===0 || product.deltaPercentagePoints==null?'':'较上期'}}{{delta(product.deltaPercentagePoints)}}；异常是调查线索。</p></div><span class="chip plain">{{ai?.status==='AVAILABLE'?'AI 已分析':'事实与反馈'}}</span></div>
    <div class="focus-grid">
      <div>
        <h3>客户主要反馈什么？</h3>
        <div class="insight"><template v-if="counts.length"><p v-for="[label,count] in counts.slice(0,3)" :key="label">{{labelNames[label] || label}}：{{count}} / {{feedback.length}} 条商品反馈</p></template><p v-else>当前没有已定位到此商品的反馈。</p></div>
        <small>主题来自反馈分类，可多选；反馈条数不计入退货件数。</small>
        <div class="actions"><button class="button small" @click="evidenceView=evidenceView==='feedback'?null:'feedback'">查看评价与反馈原文</button><button class="button small" @click="emit('correct')">修订反馈主题</button></div>
        <details v-if="related.length"><summary>相关售后记录（{{related.length}}）</summary><a v-for="c in related" :key="c.id" :href="href('/after-sales/cases',{id:c.id})">{{c.body.title}}</a></details>
        <h3>已核实的事实</h3>
        <p>本期实收退货 {{product.groups[1].numerator}} 件，对应实际发货 {{product.groups[1].denominator}} 件；上期为 {{product.groups[0].numerator}} / {{product.groups[0].denominator}} 件。</p>
        <p v-if="product.finding==='UNKNOWN'" class="gap">{{product.groups.flatMap((g:any)=>g.unresolved || []).join('；') || '观察期或样本条件未满足，暂时无法判断。'}}</p>
        <button class="button small" @click="evidenceView=evidenceView==='returns'?null:'returns'">查看本期与上期退货证据</button>
      </div>
      <div>
        <h3>可能原因与待核实信息</h3>
        <template v-if="ai?.status==='AVAILABLE'"><div class="insight"><p v-for="line in ai.output.hypotheses.slice(0,3)" :key="line">{{line}}</p></div><h3>建议下一步</h3><p v-for="line in ai.output.nextSteps.slice(0,3)" :key="line">{{line}}</p><details><summary>其他解释与待补证</summary><p v-for="line in [...ai.output.alternativeExplanations,...ai.output.missingEvidence]" :key="line">{{line}}</p></details></template>
        <p v-else class="gap">{{ai?'本次 AI 建议未生成，已核事实仍可使用。':'此历史报告尚无逐商品原因分析，可调整分析范围后更新；当前保留原始统计和反馈。'}}</p>
        <button class="button primary" :disabled="busy || !feedback.length" @click="investigate">发起调查</button><small class="action-note">调查后由人工确认风险，才会形成补货提醒。</small>
        <ModelUsage v-if="ai" :ai="ai" />
      </div>
    </div>
    <div v-if="evidenceView==='feedback'" class="evidence-list"><h3>客户反馈原文 · {{product.name}}</h3><article v-for="f in feedback" :key="f.feedbackId"><p>{{f.text}}</p><small>{{f.classification?.labels.map((l:string)=>labelNames[l] || l).join('、')}} · {{f.lineId?'已关联订单明细':'商品已核实'}}</small></article><p v-if="!feedback.length">此商品尚无可回查反馈。</p></div>
    <div v-if="evidenceView==='returns'" class="evidence-list"><h3>发货与退货依据 · {{product.name}}</h3><div v-for="(g,index) in product.groups" :key="index"><h4>{{index===0?'上期':'本期'}} · 实收 {{g.numerator}} / 实发 {{g.denominator}} 件</h4><div class="actions"><button v-for="(id,n) in g.evidenceRefs" :key="id" class="button small" :disabled="busy" @click="emit('evidence',id)">查看依据 {{Number(n)+1}}</button></div></div></div>
    <details class="advanced"><summary>指标说明 / 数据依据 / 高级详情</summary><p>{{report.body.metrics.definition}}</p><p>按实际发货完成后观察，样本、期间及规则来自当前已核对资料。</p><div v-for="(g,index) in product.groups" :key="index"><h4>{{index===0?'上期':'本期'}}</h4><p>满足观察期的订单商品 {{g.matureOrders}} / {{g.orders}}；实发 {{g.denominator}} 件，实收 {{g.numerator}} 件。</p><p>实际退款：{{Object.entries(g.refundAmounts).map(([currency,amount])=>amount+' '+currency).join('；') || '未提供'}}；期外事件 {{g.outsideWindow.length}} 条。</p></div><slot name="advanced" /></details>
  </section>
</template>

<style scoped>
h2{font-size:18px;margin:0}h3{font-size:15px;margin:20px 0 10px}p{line-height:1.75;margin:8px 0}small{display:block;color:#71818b;font-size:12px;line-height:1.7}.product-table,.product-focus{margin:20px 0;overflow:hidden}.section-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px;border-bottom:1px solid #e2e8ed}.section-head p{font-size:13px;color:#71818b;margin-bottom:0}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:13px}th{padding:14px 18px;background:#f7f9fb;color:#71818b;font-size:12px;font-weight:500}td{padding:19px 18px;border-top:1px solid #e8edf0}tr.selected{background:#f5faf8}.text-button{padding:0;border:0;background:none;color:#176f69;cursor:pointer;font:inherit;font-weight:600;text-align:left}.focus-grid{display:grid;grid-template-columns:1fr 1fr;gap:28px;padding:2px 22px 24px}.insight{background:#f1f7f4;border-left:3px solid #93bcb2;padding:10px 14px;font-size:14px}.gap{color:#846027;font-size:13px}.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.action-note{margin-top:10px}details{margin:15px 0}summary{cursor:pointer;color:#36666a;font-size:13px}.advanced,.evidence-list{border-top:1px solid #e2e8ed;padding:18px 22px;margin:0}.evidence-list article{border-bottom:1px solid #e8edf0;padding:8px 0}.evidence-list h3{margin-top:0}details a{display:block;padding:8px 0;color:#176f69}@media(max-width:850px){.focus-grid{grid-template-columns:1fr;gap:0}.section-head{align-items:start}.section-head>.chip{flex-shrink:0}th,td{padding:12px;white-space:nowrap}}
</style>
