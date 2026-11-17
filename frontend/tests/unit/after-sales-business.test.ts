import { expect,it } from 'vitest'
import { createSSRApp,h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import CaseWorkspace from '../../src/afterSales/CaseWorkspace.vue'
import CaseProducts from '../../src/afterSales/CaseProducts.vue'
import { adviceResult,reviewData,storeLabel } from '../../src/afterSales/presentation'
import type { Asset } from '../../src/afterSales/api'
const asset=(reason?:string)=>({id:'case',kind:'CASE',revision:5,state:'OPEN',sourceNature:'TEACHING_ERP_OBSERVED',scope:{sourceTenant:'one'},body:{title:'袖口接缝松开',erpStoreName:'SIM-AS-20261116-R1-SHOP',identity:{name:'澄屿针织衫',sku:'KNIT-M',productId:'362',storeId:'13',orderId:'order'},messages:[{role:'CUSTOMER',text:'袖口开线，请帮我核实。',source:'CLAIM',at:'2026-11-16T12:00:00+08:00'}],evidence:{facts:[],missing:[]},advice:reason?[{version:1,caseRevision:5,ai:{status:'NOT_ATTEMPTED',reason}}]:[],reviews:[]}} as Asset)
it('does not call a completed no-op task a generated reply',()=>{
 expect(adviceResult(asset('CUSTOMER_MESSAGE_REQUIRED'))).toContain('补充客户的问题')
 expect(adviceResult(asset('POLICY_NOT_APPLICABLE'))).toContain('已发布政策')
 expect(adviceResult(asset('EVIDENCE_UNVERIFIED'))).toContain('重新核实')
 expect(adviceResult(asset('CATEGORY_UNSUPPORTED'))).toContain('这类商品')
 const a=asset();a.body.advice=[{ai:{status:'AVAILABLE'}}];expect(adviceResult(a)).toContain('回复已生成')
 expect(adviceResult(asset('INVALID_OUTPUT'))).toContain('未通过校验')
})
it('preserves review audit and records adoption only for the current available suggestion',()=>{
 const a=asset();expect(reviewData(a,'人工回复')).toEqual({adviceVersion:null,text:'人工回复',decision:'MANUAL',reason:'人工填写并核对回复后保存'})
 a.body.advice=[{version:1,caseRevision:5,ai:{status:'AVAILABLE'}}]
 expect(reviewData(a,'核对后修改')).toMatchObject({decision:'ACCEPT',reason:'人工核对当前AI建议及回复后保存'})
 a.revision=6;expect(reviewData(a,'新的人工稿').decision).toBe('MANUAL')
 expect(reviewData(a,'升级','ESCALATE','已核实安全信号')).toMatchObject({decision:'ESCALATE',reason:'已核实安全信号'})
 expect(()=>reviewData(a,'升级','ESCALATE','')).toThrow('请填写处理原因')
})
it('renders a conversation and editable reply beside a compact order summary',async()=>{
 const html=await renderToString(createSSRApp({render:()=>h(CaseWorkspace,{asset:asset('POLICY_NOT_APPLICABLE'),busy:false,modelEnabled:true,draft:'',message:'',attachments:'',reason:''})}))
 for(const text of ['客户问题与诉求','袖口开线，请帮我核实。','回复稿','确认并保存','订单摘要','客服补录','没有匹配'])expect(html).toContain(text)
 for(const text of ['ERP 仅提供工单标题','无需重复选择','审核 / 升级理由','b-case-grid'])expect(html).not.toContain(text)
 expect(html).toContain('更多处理');expect(html).not.toContain('升级处理</button>')
})
it('keeps generation visibly pending and disables double clicks while saving or generating',async()=>{
 const html=await renderToString(createSSRApp({render:()=>h(CaseWorkspace,{asset:asset(),busy:true,modelEnabled:true,draft:'',message:'',attachments:'',reason:''})}))
 expect(html).toContain('正在处理…');expect(html).toContain('disabled')
})
it('shows the actual customer problem distribution without inventing a return rate',async()=>{
 const html=await renderToString(createSSRApp({render:()=>h(CaseProducts,{cases:[asset(),{...asset(),id:'two'}]})}))
 expect(html).toContain('2 条');expect(html).toContain('袖口开线');expect(html).toContain('查看并调查');expect(html).not.toContain('退货率')
})
it('uses the approved batch display name while leaving unrelated store names unchanged',()=>{
 expect(storeLabel('SIM-AS-20261116-R1-SHOP')).toBe('澄屿生活馆 · 美国站')
 expect(storeLabel('Other Store')).toBe('Other Store')
})
it('keeps handled replies read only and does not claim ERP verification for legacy local records',async()=>{
 const a=asset();a.state='HANDLED';a.body.erpVoiceId='71'
 const html=await renderToString(createSSRApp({render:()=>h(CaseWorkspace,{asset:a,busy:false,modelEnabled:true,draft:'已核对的回复',message:'',attachments:'',reason:''})}))
 expect(html).toContain('readonly');expect(html).toContain('中台处理记录已保存')
 expect(html).not.toContain('ERP 处理记录已核验');expect(html).not.toContain('更正关联商品')
 a.body.confirmation={status:'CONFIRMED'}
 const verified=await renderToString(createSSRApp({render:()=>h(CaseWorkspace,{asset:a,busy:false,modelEnabled:true,draft:'已核对的回复',message:'',attachments:'',reason:''})}))
 expect(verified).toContain('ERP 处理记录已核验')
})
