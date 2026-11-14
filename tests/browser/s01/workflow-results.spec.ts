import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs'
import {readFileSync,writeFileSync} from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../../..'),out=path.join(root,'docs/evidence/S01-WORKFLOW-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json'),actionTimeout:15000})
test('读取已完成真实AI结果、最终布局与刷新后的ERP状态，不再调用模型',async({page})=>{
 test.skip(process.env.S01_WORKFLOW_LIVE!=='1','Explicit real session required');test.setTimeout(150000)
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message))
 await page.goto('/#/home');await expect(page.getByRole('heading',{name:'工作首页',exact:true})).toBeVisible()
 await page.screenshot({path:path.join(out,'screenshots/01-platform-home.png'),fullPage:true})
 const batches=await(await page.request.get('/api/v1/s01/v2/batches')).json()
 const batch=batches.items.find((r:any)=>r.state==='SUCCEEDED'&&r.analysisRange==='OWNED_REGISTERED').taskRef.taskId
 const models=JSON.parse(readFileSync(path.join(out,'models.json'),'utf8'))
 for(const model of models.results){
  await page.goto(`/#/sku/${model.entityKey}?batch=${batch}&single=${model.taskId}`)
  await expect(page.getByRole('region',{name:'AI 行动建议'})).toHaveAttribute('data-state','ready',{timeout:30000})
  await expect(page.getByRole('region',{name:'AI 行动建议'})).toContainText(model.sku)
  const name=model.sku==='HLX-LAMP-SURGE'?'08-surge-ai-result':'10-no-quote-ai'
  await page.screenshot({path:path.join(out,'screenshots/'+name+'.png'),fullPage:true})
  if(model.sku==='HLX-CASE-NOQUOTE')await expect(page.getByRole('button',{name:'人工确认并提交请购'})).toBeDisabled()
 }
 await page.setViewportSize({width:820,height:1000});await page.screenshot({path:path.join(out,'screenshots/17-detail-820.png'),fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
 await page.setViewportSize({width:1440,height:1000});await page.goto('/#/requisitions')
 await expect(page.getByRole('button',{name:'刷新 ERP 状态'})).toBeEnabled({timeout:90000});await expect(page.locator('tbody tr')).toHaveCount(3,{timeout:90000})
 const pending=page.waitForResponse(r=>r.url().includes('/purchase-status?')&&r.request().method()==='GET')
 await page.getByRole('button',{name:'刷新 ERP 状态'}).click();const live=await(await pending).json();expect(live.failedCount).toBe(0);expect(live.items.every((r:any)=>r.verified)).toBe(true)
 await expect(page.getByRole('button',{name:'刷新 ERP 状态'})).toBeEnabled();await page.screenshot({path:path.join(out,'screenshots/13-erp-purchase-tracking.png'),fullPage:true})
 writeFileSync(path.join(out,'live-purchase-tracking.json'),JSON.stringify(live,null,2))
 writeFileSync(path.join(out,'final-browser-result.json'),JSON.stringify({result:'PASS',realModelsViewed:models.results.map((r:any)=>r.sku),newModelCalls:0,erpBusinessWrites:0,livePurchaseStates:live.items.map((r:any)=>({id:r.erpId,status:r.status,verifiedAt:r.verifiedAt})),pageErrors:errors},null,2))
 expect(errors).toEqual([])
})
