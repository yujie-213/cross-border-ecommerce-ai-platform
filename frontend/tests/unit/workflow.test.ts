import { beforeEach, expect, it, vi } from 'vitest'
import { createSSRApp,h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { request } from '../../src/api/client'
import { state,reset,createSingle,openItem,openSingle } from '../../src/s01'
import AiAnalysis from '../../src/components/AiAnalysis.vue'
import SkuPage from '../../src/pages/SkuPage.vue'
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
 expect(html).toContain('更新补货分析');expect(html).toContain('生成 AI 建议');expect(html).toContain('采购前再核实')
})
it('gives failed and unavailable AI a visible retry action',async()=>{
 const html=await renderToString(createSSRApp({render:()=>h(AiAnalysis,{ai:null,taskState:'FAILED',errorCode:'ERP_AUTH_REJECTED'})}))
 expect(html).toContain('重试 AI 建议');expect(html).toContain('这次没有生成 AI 建议')
})
