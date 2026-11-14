import { beforeEach, expect, it, vi } from 'vitest'
import { createSSRApp,h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { request } from '../../src/api/client'
import { state,reset,createSingle,openItem,openSingle } from '../../src/s01'
import AiAnalysis from '../../src/components/AiAnalysis.vue'
import SkuPage from '../../src/pages/SkuPage.vue'
import { suggestedPurchaseQuantity } from '../../src/business'
vi.mock('../../src/api/client',async original=>({...await original<typeof import('../../src/api/client')>(),request:vi.fn()}))
const req=vi.mocked(request)
beforeEach(()=>{reset();req.mockReset();state.busy=false;state.batchId='batch';state.itemKey='a';state.item={entityKey:'a',sku:'one',name:'商品',identityVerified:true,quantity:null,analysisState:'NEEDS_REVIEW',procurementEligibility:{eligible:false,hardBlocks:[]},uncertainties:[]} as never})
it('shows immediate AI feedback and clears the previous explanation before POST returns',async()=>{
 let done!:(v:unknown)=>void;req.mockImplementationOnce(()=>new Promise(r=>{done=r}))
 state.singleReport={analysisReport:{ai:{status:'AVAILABLE'}}} as never
 const creating=createSingle(true)
 expect(state.singleLoading).toBe(true);expect(state.singleMode).toBe('ai');expect(state.singleReport).toBeNull()
 req.mockResolvedValueOnce({entityKey:'b',sku:'two'})
 await openItem('b');done({taskRef:{taskId:'late-a'}});await creating
 expect(state.itemKey).toBe('b');expect(state.singleId).toBe('');expect(req).toHaveBeenCalledTimes(2)
})
it('rejects an analysis belonging to a different warehouse instead of displaying its AI',async()=>{
 req.mockResolvedValueOnce({task:{state:'SUCCEEDED'},report:{dataReport:{item:{entityKey:'other'}}}})
 await openSingle('wrong');expect(state.singleReport).toBeNull();expect(state.singleError).toContain('不属于当前店仓')
})
it('always renders an analysis entry for a registered product without purchasing eligibility',async()=>{
 const html=await renderToString(createSSRApp({render:()=>h(SkuPage)}))
 expect(html).toContain('更新补货分析');expect(html).toContain('生成 AI 建议');expect(html).toContain('采购确认')
 expect(html).not.toContain('未生成');expect(html).not.toContain('暂无 AI 建议')
})
it('gives failed and unavailable AI a visible retry action',async()=>{
 const html=await renderToString(createSSRApp({render:()=>h(AiAnalysis,{ai:null,taskState:'FAILED',errorCode:'ERP_AUTH_REJECTED'})}))
 expect(html).toContain('重试 AI 建议');expect(html).toContain('这次没有生成 AI 建议')
})
it('keeps completed replenishment separate from an AI failure and gives its actual cause',async()=>{
 const html=await renderToString(createSSRApp({render:()=>h(AiAnalysis,{ai:{status:'UNAVAILABLE',reason:'INVALID_OUTPUT'},taskState:'SUCCEEDED'})}))
 expect(html).toContain('补货分析已更新，AI 建议未生成');expect(html).toContain('返回内容未通过校验');expect(html).toContain('重试 AI 建议')
})
it('uses the explicit conclusion, evidence and real actions instead of matching generic keywords',async()=>{
 const entry=(text:string,ref:string)=>({text,supportRefs:[ref]})
 const html=await renderToString(createSSRApp({render:()=>h(AiAnalysis,{ai:{status:'AVAILABLE',adviceVersion:'s01-purchase-advice-v2',explanation:{
  recommendationReasons:[entry('本仓缺货早于正常到货','conclusion')],keyEvidence:[entry('参考17件，按整箱候选20件','quantity-basis')],
  majorRisks:[entry('只有2个销售记录日，需求持续性尚未确认','sample-risk')],humanConfirmations:[entry('确认能否赶上缺货前到货','next-step')]}}})}))
 expect(html).toContain('本仓缺货早于正常到货');expect(html).toContain('参考17件，按整箱候选20件');expect(html).toContain('确认能否赶上缺货前到货')
 expect(html).not.toContain('建议先做');expect(html).not.toContain('接下来');expect(html).not.toContain('重点留意')
})
it('defaults a local proposal to the constrained candidate, then the reference demand when no candidate exists',()=>{
 const item={quantity:56,decision:{purchasableQuantity:56,referenceReplenishmentQuantity:53}} as never
 expect(suggestedPurchaseQuantity(item)).toBe(56)
 expect(suggestedPurchaseQuantity({quantity:null,decision:{purchasableQuantity:null,referenceReplenishmentQuantity:53}} as never)).toBe(53)
 expect(suggestedPurchaseQuantity({quantity:0,decision:{purchasableQuantity:0,referenceReplenishmentQuantity:0}} as never)).toBe(0)
})
