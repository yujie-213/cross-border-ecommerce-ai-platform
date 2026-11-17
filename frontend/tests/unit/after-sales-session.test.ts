import { computed } from 'vue'
import { afterEach, expect, it, vi } from 'vitest'
import { desk, returns, pages, tasks, details, workbench, workspace, loadPage, loadIndex, resultPage, resetAfterSalesSession, followTask } from '../../src/afterSales/session'
import { request } from '../../src/api/client'
vi.mock('../../src/api/client',async original=>({...await original<typeof import('../../src/api/client')>(),request:vi.fn()}))
const deferred=<T>()=>{let resolve!:(v:T)=>void;let reject!:(e:Error)=>void;const promise=new Promise<T>((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}}
afterEach(()=>{resetAfterSalesSession();vi.clearAllMocks()})

it('deduplicates slow reads and restores a view without issuing a second ERP request',async()=>{
  const data=deferred<any>(),load=vi.fn(()=>data.promise)
  const first=loadPage('desk:A',load);const view=computed(()=>resultPage('desk:A').data?.items || []);expect(view.value).toEqual([]);const returning=loadPage('desk:A',load)
  expect(load).toHaveBeenCalledOnce();expect(resultPage('desk:A').loading).toBe(true)
  data.resolve({items:['one']});await Promise.all([first,returning]);expect(view.value).toEqual(['one']);await loadPage('desk:A',load)
  expect(load).toHaveBeenCalledOnce();expect(pages['desk:A'].data.items).toEqual(['one'])
  desk.query='袖口';desk.queue='ALL';desk.scroll=640;returns.selected='902:SKU'
  expect({...desk}).toMatchObject({query:'袖口',queue:'ALL',scroll:640});expect(returns.selected).toBe('902:SKU')
})
it('retains the previous list while refreshing and after an error',async()=>{
  await loadPage('returns:A',async()=>({items:['old']}))
  const data=deferred<any>();const refresh=loadPage('returns:A',()=>data.promise,true)
  expect(resultPage('returns:A').data.items).toEqual(['old'])
  data.reject(new Error('offline'));await refresh
  expect(resultPage('returns:A').data.items).toEqual(['old']);expect(resultPage('returns:A').error).not.toBe('')
})
it('keeps late store responses in their own view and rejects pre-logout results',async()=>{
  const data=deferred<any>();const first=loadPage('desk:A',()=>data.promise)
  await loadPage('desk:B',async()=>({items:['B']}));data.resolve({items:['A']});await first
  expect(pages['desk:B'].data.items).toEqual(['B'])
  const old=deferred<any>();const late=loadPage('old',()=>old.promise)
  resetAfterSalesSession();old.resolve({items:['private']});await late
  expect(Object.keys(pages)).toEqual([]);expect(desk.query).toBe('')
})
it('shares the lightweight workspace/index across repeated entries',async()=>{
  vi.mocked(request).mockResolvedValue({sourceStores:[],case:{items:[]}})
  await Promise.all([loadIndex(),loadIndex()]);await loadIndex()
  expect(request).toHaveBeenCalledTimes(2);expect(workspace.value).toBeDefined()
  await loadIndex(true);expect(request).toHaveBeenCalledTimes(4)
})
it('finishes a background task once and updates only its own saved case',async()=>{
  const asset={id:'A',kind:'CASE',revision:2,body:{advice:['new']}} as any
  workbench.value={case:{items:[{id:'A'},{id:'B',body:{text:'unchanged'}}],nextCursor:null}} as any
  const done=deferred<any>()
  vi.mocked(request).mockImplementation(async path=>path.includes('/cases/')?asset:path.endsWith('/report')?{analysisReport:{}}:done.promise)
  tasks.key={id:'job',assetId:'A',action:'advice-jobs',state:'QUEUED',error:''}
  followTask('key');followTask('key');expect(request).toHaveBeenCalledOnce()
  done.resolve({state:'SUCCEEDED'})
  await vi.waitFor(()=>expect(tasks.key.state).toBe('SUCCEEDED'))
  expect(request).toHaveBeenCalledTimes(3);expect(details.A.revision).toBe(2)
  expect(workbench.value?.case.items[1].body.text).toBe('unchanged')
})
