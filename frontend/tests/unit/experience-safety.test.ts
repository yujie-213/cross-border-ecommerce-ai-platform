import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { ApiError, request } from '../../src/api/client'
import { state, reset, readRequisition, submitRequisition } from '../../src/s01'
import WorkbenchPage from '../../src/pages/WorkbenchPage.vue'
import HomePage from '../../src/pages/HomePage.vue'

vi.mock('../../src/api/client', async original => ({ ...await original<typeof import('../../src/api/client')>(), request:vi.fn() }))
const req=vi.mocked(request)
beforeEach(()=>{reset();req.mockReset();state.busy=false;state.pending=null;state.requisitionLoading=false;state.requisitionReadState='idle';state.options={canSubmit:true} as never;state.singleId='new-analysis';state.item={entityKey:'same-object',procurementEligibility:{eligible:true}} as never})

describe('experience procurement exclusion',()=>{
  it('blocks POST until a successful read, including slow and failed reads',async()=>{
    let done!:(value:null)=>void
    req.mockImplementationOnce(()=>new Promise(resolve=>{done=resolve as typeof done}))
    const reading=readRequisition()
    await submitRequisition(48,'')
    expect(req).toHaveBeenCalledTimes(1)
    expect(state.requisitionReadState).toBe('loading')
    done(null);await reading
    expect(state.requisitionReadState).toBe('ready')
    req.mockRejectedValueOnce(new ApiError(409,'BUSINESS_CONFLICT'))
    await readRequisition();await submitRequisition(48,'')
    expect(state.requisitionReadState).toBe('error')
    expect(req).toHaveBeenCalledTimes(2)
  })
  it('ignores a late empty read for the previous analysis',async()=>{
    let done!:(value:null)=>void
    req.mockImplementationOnce(()=>new Promise(resolve=>{done=resolve as typeof done}))
    const reading=readRequisition();state.singleId='another-analysis';state.requisition={state:'CREATE_UNKNOWN'} as never
    done(null);await reading
    expect((state.requisition as {state:string} | null)?.state).toBe('CREATE_UNKNOWN')
  })
  it('ignores an older empty read for the same analysis',async()=>{
    let done!:(value:null)=>void
    req.mockImplementationOnce(()=>new Promise(resolve=>{done=resolve as typeof done}))
    const old=readRequisition()
    req.mockResolvedValueOnce({state:'CREATE_UNKNOWN'})
    await readRequisition();done(null);await old
    expect(state.requisition?.state).toBe('CREATE_UNKNOWN')
    expect(state.requisitionReadState).toBe('ready')
  })
  it('cannot bypass a pending command with a new analysis of the same object',async()=>{
    state.requisitionReadState='ready';state.pending={singleId:'previous-analysis',entityKey:'same-object'} as never
    await submitRequisition(48,'');expect(req).not.toHaveBeenCalled()
  })
  it('keeps a conflicting operation returned from another report',async()=>{
    req.mockResolvedValueOnce({reportId:'previous-analysis',state:'SUBMIT_UNKNOWN',blockedByOtherAnalysis:true})
    await readRequisition();await submitRequisition(48,'')
    expect(req).toHaveBeenCalledTimes(1);expect(state.requisition?.state).toBe('SUBMIT_UNKNOWN')
  })
})

describe('platform and business workspace separation',()=>{
  it('shows only the available agent and actual recent tasks on the homepage',async()=>{
    const html=await renderToString(createSSRApp({render:()=>h(HomePage)}))
    expect(html).toContain('业务能力');expect(html).toContain('智能补货');expect(html).toContain('近期任务')
    expect(html).not.toContain('补货概览');expect(html).not.toContain('已预测 SKU')
  })
  it('shows an actionable risk queue and one set of business counts',async()=>{
    state.batchId='owned';state.progress={task:{state:'SUCCEEDED'},summary:{discoveredSkuCount:2,scopeObjectCount:2,replenishSkuCount:1,noReplenishmentSkuCount:1}} as never
    const html=await renderToString(createSSRApp({render:()=>h(WorkbenchPage)}))
    expect(html).toContain('需要补货');expect(html).toContain('暂不补货');expect(html).not.toContain('不同 SKU');expect(html).not.toContain('已预测 SKU')
    expect(html).toContain('从风险最高的店仓开始');expect((html.match(/class="attention-summary"/g)||[]).length).toBe(1)
  })
})
