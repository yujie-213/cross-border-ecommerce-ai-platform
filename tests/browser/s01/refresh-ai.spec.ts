import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs'
import {mkdirSync,writeFileSync} from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../../..')
const out=path.join(root,'docs/evidence/S01-WORKFLOW-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json')})

test('顶部更新补货分析实际生成AI，空状态不重复，刷新保留新结果',async({page})=>{
 test.skip(process.env.S01_REFRESH_AI_LIVE!=='1','Explicit live model verification only')
 test.setTimeout(300000)
 const errors:string[]=[];const requests:unknown[]=[];let purchaseWrites=0
 page.on('pageerror',e=>errors.push(e.message))
 await page.route('**/api/v1/s01/v2/singles/*/requisition',async route=>{
  if(route.request().method()==='POST'){purchaseWrites++;await route.abort();return}
  await route.continue()
 })
 page.on('request',r=>{if(r.method()==='POST' && r.url().endsWith('/s01/v2/singles'))requests.push(r.postDataJSON())})
 await page.goto('/#/suggestions')
 await page.getByLabel('查找商品',{exact:true}).fill('HLX-CASE-NOQUOTE')
 await expect(page.locator('tbody tr')).toHaveCount(1,{timeout:30000})
 await expect(page.locator('tbody tr')).toContainText('HLX-CASE-NOQUOTE')
 await page.getByRole('link',{name:'分析商品 →',exact:true}).click()
 const ai=page.getByRole('region',{name:'AI 行动建议'})
 await expect(ai).toHaveAttribute('data-state','idle')
 await expect(ai.getByText('未生成',{exact:true})).toHaveCount(0)
 await expect(ai.getByText('暂无 AI 建议',{exact:true})).toHaveCount(0)
 mkdirSync(path.join(out,'screenshots'),{recursive:true})
 await page.screenshot({path:path.join(out,'screenshots/29-ai-idle-clean.png'),fullPage:true})
 await page.getByRole('button',{name:'更新补货分析',exact:true}).click()
 await expect(ai).toHaveAttribute('data-state','running')
 await expect(page.getByRole('button',{name:'正在更新分析与 AI…',exact:true})).toBeDisabled()
 await expect(ai.getByRole('button',{name:'正在处理…',exact:true})).toBeDisabled()
 await page.screenshot({path:path.join(out,'screenshots/30-refresh-ai-running.png'),fullPage:true})
 await expect(ai).toHaveAttribute('data-state','ready',{timeout:240000})
 await expect(page.getByRole('button',{name:'更新补货分析',exact:true})).toBeEnabled()
 await expect(page.getByRole('button',{name:'人工确认并提交请购'})).toBeDisabled()
 const taskId=new URLSearchParams(page.url().split('?')[1]).get('single')
 expect(taskId).toBeTruthy()
 const response=await page.request.get('/api/v1/s01/v2/singles/'+taskId)
 expect(response.ok()).toBe(true)
 const result=await response.json(),model=result.report.analysisReport.ai
 expect(model.status).toBe('AVAILABLE');expect(model.usage.totalTokens).toBeGreaterThan(0)
 expect(requests).toHaveLength(1);expect(requests[0]).toMatchObject({explainAI:true})
 await page.reload();await expect(ai).toHaveAttribute('data-state','ready',{timeout:30000})
 await expect(ai).toContainText('HLX-CASE-NOQUOTE')
 await page.screenshot({path:path.join(out,'screenshots/31-refresh-ai-ready.png'),fullPage:true})
 expect(purchaseWrites).toBe(0);expect(errors).toEqual([])
 writeFileSync(path.join(out,'refresh-ai-result.json'),JSON.stringify({result:'PASS',taskId,sku:'HLX-CASE-NOQUOTE',
  trigger:'top-right update replenishment analysis',explainAI:true,newAnalysisRequests:requests.length,
  immediateRunning:true,duplicateIdleText:false,aiStatus:model.status,model:model.actualModelRevision||model.model,
  usage:model.usage,costStatus:model.costStatus,refreshRetainsResult:true,purchaseWrites,pageErrors:errors},null,2))
})
