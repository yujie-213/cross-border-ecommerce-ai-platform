import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs'
import {mkdirSync,writeFileSync} from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../../..')
const out=path.join(root,'docs/evidence/S01-WORKFLOW-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json')})

test('日常AI策略：真实点击生成建议并刷新保留结果',async({page})=>{
 test.skip(process.env.S01_DAILY_AI_LIVE!=='1','Requires explicit paid daily AI verification')
 test.setTimeout(300000)
 const errors:string[]=[];let purchaseWrites=0,analysisRequests=0
 page.on('pageerror',e=>errors.push(e.message))
 await page.route('**/api/v1/s01/v2/singles/*/requisition',async route=>{
  if(route.request().method()==='POST'){purchaseWrites++;await route.abort();return}
  await route.continue()
 })
 page.on('request',r=>{if(r.method()==='POST' && r.url().endsWith('/s01/v2/singles'))analysisRequests++})
 await page.goto('/#/suggestions')
 await page.getByLabel('查找商品',{exact:true}).fill('HLX-CASE-NOQUOTE')
 await expect(page.locator('tbody tr')).toHaveCount(1,{timeout:30000})
 await expect(page.locator('tbody tr')).toContainText('HLX-CASE-NOQUOTE')
 await page.getByRole('link',{name:'分析商品 →',exact:true}).click()
 const ai=page.getByRole('region',{name:'AI 行动建议'})
 await page.getByRole('button',{name:/生成 AI 建议|重试 AI 建议|重新生成 AI 建议/,exact:true}).click()
 await expect(ai).toHaveAttribute('data-state','running')
 await expect(ai).toHaveAttribute('data-state','ready',{timeout:240000})
 await expect(page.getByRole('button',{name:'确认并提交'})).toBeDisabled()
 const taskId=new URLSearchParams(page.url().split('?')[1]).get('single')
 expect(taskId).toBeTruthy()
 const response=await page.request.get('/api/v1/s01/v2/singles/'+taskId)
 expect(response.ok()).toBe(true)
 const result=await response.json(),model=result.report.analysisReport.ai
 expect(model.status).toBe('AVAILABLE')
 await page.reload();await expect(ai).toHaveAttribute('data-state','ready',{timeout:30000})
 await expect(ai).toContainText('HLX-CASE-NOQUOTE')
 mkdirSync(path.join(out,'screenshots'),{recursive:true})
 await page.screenshot({path:path.join(out,'screenshots/22-daily-ai-unlimited.png'),fullPage:true})
 expect(analysisRequests).toBe(1);expect(purchaseWrites).toBe(0);expect(errors).toEqual([])
 writeFileSync(path.join(out,'daily-ai-result.json'),JSON.stringify({result:'PASS',authorization:'s01-local-daily-use-20261115',taskId,
  sku:'HLX-CASE-NOQUOTE',aiStatus:model.status,model:model.model,usage:model.usage,costStatus:model.costStatus,
  newAnalysisRequests:analysisRequests,purchaseWrites,pageErrors:errors,refreshRetainsResult:true},null,2))
})
