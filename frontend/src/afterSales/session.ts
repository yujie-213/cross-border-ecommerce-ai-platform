import { reactive, ref, watch } from 'vue'
import type { Asset, Workbench, Workspace } from './api'
import { get } from './api'
import { errorText, request } from '../api/client'

// Page results live only in the current signed-in browser session. Explicit
// refresh reads ERP again; navigating between pages only restores these views.
export interface ResultPage {
  data?: any
  loading: boolean
  error: string
  updated: string
}
export const workspace = ref<Workspace>()
export const workbench = ref<Workbench>()
export const details = reactive<Record<string, Asset>>({})
export const desk = reactive({ store: '', query: '', queue: 'TODO', kind: 'ALL', scroll: 0 })
export const returns = reactive({ store: '', query: '', view: 'returns' as 'returns'|'monitor', windowDays: 7, endDate: localDate(), scroll: 0, selected: '', selectedSku: '' })
export const pages = reactive<Record<string, ResultPage>>({})
export const sources = reactive<Record<string, any>>({})
export const opening = reactive<Record<string, boolean>>({})
export const pending = ref<{ key:string; path:string; body?:unknown }>()
export interface RunningTask { id:string; assetId:string; action:string; investigationId?:string; startedAt?:number; state:string; error:string; report?:any }
export const tasks = reactive<Record<string, RunningTask>>({})
let epoch = 0
let indexRequest: Promise<void> | undefined
const requests = new Map<string, Promise<void>>()
const polling = new Set<string>()

function localDate() { const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}` }
export function resultPage(key:string) {
  if(!pages[key])pages[key]={loading:false,error:'',updated:''}
  return pages[key]
}
export function remember(asset:Asset) {
  details[asset.id]=asset
  const index=workbench.value?.[asset.kind.toLowerCase() as keyof Workbench]
  if(index){const i=index.items.findIndex(a=>a.id===asset.id);if(i>=0)index.items[i]=asset;else index.items.unshift(asset)}
}
export function loadIndex(force=false):Promise<void> {
  if(indexRequest)return indexRequest
  if(!force && workspace.value && workbench.value)return Promise.resolve()
  const own=epoch
  indexRequest=Promise.all([get<Workspace>('/workspace'),get<Workbench>('/workbench')]).then(([w,index])=>{
    if(own===epoch){workspace.value=w;workbench.value=index}
  }).finally(()=>{if(own===epoch)indexRequest=undefined})
  return indexRequest
}
export function loadPage(key:string,loader:()=>Promise<any>,force=false):Promise<void> {
  const active=requests.get(key);if(active)return active
  const page=resultPage(key);if(!force && (page.data || page.error))return Promise.resolve()
  const own=epoch;page.loading=true;page.error=''
  const promise=loader().then(data=>{if(own===epoch){page.data=data;page.updated=new Date().toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})}})
    .catch(e=>{if(own===epoch)page.error=errorText(e)})
    .finally(()=>{if(own===epoch){page.loading=false;requests.delete(key)}})
  requests.set(key,promise);return promise
}
export const taskKey=(assetId:string,action:string,investigationId='')=>[assetId,action,investigationId].join(':')
export const taskRunning=(task?:RunningTask)=>!!task && !['SUCCEEDED','FAILED','CANCELLED'].includes(task.state)
// Only opaque task references survive a reload. Customer content stays in
// memory; every restored reference is authorized again by the task/asset APIs.
watch(tasks,()=>{
  if(typeof sessionStorage==='undefined')return
  const active=Object.values(tasks).filter(taskRunning).map(({id,assetId,action,investigationId,startedAt})=>({id,assetId,action,investigationId,startedAt}))
  sessionStorage.setItem('b-active-tasks',JSON.stringify(active))
},{deep:true})
export function restoreTasks() {
  if(typeof sessionStorage==='undefined')return
  try {
    const saved=JSON.parse(sessionStorage.getItem('b-active-tasks') || '[]')
    if(!Array.isArray(saved))return
    for(const t of saved.slice(0,100)){
      if(!t || ![t.id,t.assetId].every(v=>typeof v==='string' && /^[\w-]{1,128}$/.test(v)) || !['evidence-jobs','advice-jobs','investigation-jobs'].includes(t.action)
        || t.investigationId!=null && (typeof t.investigationId!=='string' || !/^[\w-]{1,128}$/.test(t.investigationId)))continue
      const key=taskKey(t.assetId,t.action,t.investigationId)
      tasks[key] ||= {...t,state:'QUEUED',error:''}
    }
  }catch { sessionStorage.removeItem('b-active-tasks') }
}
export function followTask(key:string) {
  const task=tasks[key];if(!task || polling.has(task.id) || !taskRunning(task))return
  const own=epoch;polling.add(task.id)
  void (async()=>{
    try {
      while(own===epoch && taskRunning(task)) {
        const current=await request<any>('/analysis-tasks/'+encodeURIComponent(task.id))
        if(own!==epoch)return
        // Publish completion only after the saved asset has been read back.
        if(current.state==='SUCCEEDED') {
          const [asset,report]=await Promise.all([get<Asset>('/cases/'+task.assetId),request<any>('/analysis-tasks/'+task.id+'/report')])
          if(own!==epoch)return
          remember(asset);task.report=report;task.state='SUCCEEDED';task.error='';return
        }
        task.state=current.state
        if(['FAILED','CANCELLED'].includes(task.state)){task.error='分析未完成，请重试。';return}
        task.error='';await new Promise(resolve=>setTimeout(resolve,1000))
      }
    } catch(e){if(own===epoch)task.error=errorText(e)}
    finally{if(own===epoch)polling.delete(task.id)}
  })()
}
export function resetAfterSalesSession() {
  epoch++;workspace.value=undefined;workbench.value=undefined;pending.value=undefined;indexRequest=undefined;requests.clear();polling.clear()
  for(const record of [details,pages,sources,opening,tasks])for(const key of Object.keys(record))delete record[key]
  Object.assign(desk,{store:'',query:'',queue:'TODO',kind:'ALL',scroll:0})
  Object.assign(returns,{store:'',query:'',view:'returns',windowDays:7,endDate:localDate(),scroll:0,selected:'',selectedSku:''})
  if(typeof sessionStorage!=='undefined'){sessionStorage.removeItem('b-pending-command');sessionStorage.removeItem('b-active-tasks')}
}
if(typeof window!=='undefined'){
  window.addEventListener('commerce:unauthenticated',resetAfterSalesSession)
  window.addEventListener('commerce:session-ended',resetAfterSalesSession)
}
export const sessionEpoch=()=>epoch
