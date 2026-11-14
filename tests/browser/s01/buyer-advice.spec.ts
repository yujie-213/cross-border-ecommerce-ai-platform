import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs'
import {mkdirSync,writeFileSync} from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../../..'),out=path.join(root,'docs/evidence/S01-WORKFLOW-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json')})

test('采购建议按商品解释数量与交期，并区分补货成功和AI失败',async({page})=>{
 test.skip(process.env.S01_BUYER_ADVICE_LIVE!=='1','Explicit real model verification only')
 test.setTimeout(600000)
 const errors:string[]=[],results:any[]=[],requests:any[]=[];let purchaseWrites=0
 page.on('pageerror',e=>errors.push(e.message))
 page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/s01/v2/singles'))requests.push(r.postDataJSON())})
 await page.route('**/api/v1/s01/v2/singles/*/requisition',async r=>{if(r.request().method()==='POST'){purchaseWrites++;await r.abort()}else await r.continue()})
 mkdirSync(path.join(out,'screenshots'),{recursive:true})
 for(const [index,sku] of ['HLX-STAND-NEW','HLX-CASE-NOQUOTE','HLX-LAMP-SURGE'].entries()){
  await page.goto('/#/suggestions');await page.getByLabel('查找商品',{exact:true}).fill(sku)
  await expect(page.locator('tbody tr')).toHaveCount(1,{timeout:30000})
  await expect(page.locator('tbody tr')).toContainText(sku)
  await page.getByRole('link',{name:'分析商品 →',exact:true}).click()
  const ai=page.getByRole('region',{name:'AI 行动建议'})
  await page.getByRole('button',{name:'更新补货分析',exact:true}).click()
  await expect(ai).toHaveAttribute('data-state','running')
  await expect(page.getByRole('button',{name:'正在更新分析与 AI…',exact:true})).toBeDisabled()
  await expect(ai).toHaveAttribute('data-state','ready',{timeout:240000})
  const taskId=new URLSearchParams(page.url().split('?')[1]).get('single')!
  const response=await page.request.get('/api/v1/s01/v2/singles/'+taskId)
  expect(response.ok()).toBe(true)
  const report=(await response.json()).report,model=report.analysisReport.ai,item=report.dataReport.item
  expect(model.adviceVersion).toBe('s01-purchase-advice-v3');expect(model.status).toBe('AVAILABLE')
  expect(model.explanation.recommendationReasons).toHaveLength(1)
  if(sku==='HLX-LAMP-SURGE')expect(model.explanation.majorRisks.flatMap((x:any)=>x.supportRefs)).toContain('sales-change')
  expect(model.explanation.majorRisks.flatMap((x:any)=>x.supportRefs)).not.toContain('arrival-risk')
  const refs=model.explanation.keyEvidence.flatMap((x:any)=>x.supportRefs)
  expect(refs).toContain('stock-basis')
  if(item.decision.purchasableQuantity!==null&&item.decision.purchasableQuantity!==item.decision.referenceReplenishmentQuantity)expect(refs).toContain('quantity-basis')
  await expect(ai.locator('h3')).toHaveText(model.explanation.recommendationReasons[0].text)
  for(const text of ['建议先做','接下来','重点留意'])await expect(ai.getByText(text,{exact:true})).toHaveCount(0)
  expect(model.usage.totalTokens).toBeGreaterThan(0)
  if(sku==='HLX-CASE-NOQUOTE'){
   await expect(ai.locator('h3')).toContainText('报价')
   await expect(page.getByRole('button',{name:'人工确认并提交请购'})).toBeDisabled()
  }
  await page.reload();await expect(ai).toHaveAttribute('data-state','ready',{timeout:30000})
  await expect(ai).toContainText(sku)
  const screenshot=`${37+index}-buyer-advice-final-${sku}.png`
  await page.screenshot({path:path.join(out,'screenshots',screenshot),fullPage:true})
  await expect(ai.getByRole('button',{name:'核对采购条件 →'})).toHaveCount(0)
  await expect(page.getByLabel('最终采购数量',{exact:true})).toBeVisible()
  results.push({sku,taskId,url:page.url(),screenshot,conclusion:model.explanation.recommendationReasons[0].text,
   explanation:model.explanation,usage:model.usage,costStatus:model.costStatus,model:model.actualModelRevision,
   reference:item.decision.referenceReplenishmentQuantity,candidate:item.decision.purchasableQuantity,
   purchaseEligible:item.procurementEligibility.eligible,refreshRetained:true,purchasePanelVisible:true})
 }
 expect(new Set(results.map(r=>r.conclusion)).size).toBeGreaterThan(1)
 const first=results[0],response=await page.request.get('/api/v1/s01/v2/singles/'+first.taskId),failure=await response.json()
 failure.report.analysisReport.ai={status:'UNAVAILABLE',reason:'MODEL_TIMEOUT'}
 await page.route('**/api/v1/s01/v2/singles/'+first.taskId,r=>r.fulfill({json:failure}))
 await page.goto(first.url)
 const ai=page.getByRole('region',{name:'AI 行动建议'})
 await expect(ai).toHaveAttribute('data-state','failed')
 await expect(ai).toContainText('补货分析已更新，AI 建议未生成')
 await expect(ai).toContainText('超时')
 await expect(ai.getByRole('button',{name:'重试 AI 建议'})).toBeEnabled()
 await expect(page.getByRole('region',{name:'各仓补货判断'})).toBeVisible()
 await page.screenshot({path:path.join(out,'screenshots/40-buyer-ai-final-partial-failure.png'),fullPage:true})
 await page.unroute('**/api/v1/s01/v2/singles/'+first.taskId)
 await page.reload();await expect(ai).toHaveAttribute('data-state','ready',{timeout:30000})
 await page.setViewportSize({width:820,height:1000})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
 await page.screenshot({path:path.join(out,'screenshots/41-buyer-advice-final-820.png'),fullPage:true})
 expect(requests).toHaveLength(3);for(const body of requests)expect(body.explainAI).toBe(true)
 expect(purchaseWrites).toBe(0);expect(errors).toEqual([])
 writeFileSync(path.join(out,'buyer-advice-final-result.json'),JSON.stringify({result:'PASS',results,newModelRequests:requests.length,
  explainAI:true,purchaseWrites,pageErrors:errors,controlledResponseChecks:['AI timeout after successful replenishment retains facts and retry'],
  mobile820:true,notes:'Three real model calls; failure branch is explicitly injected, not a real provider timeout.'},null,2))
})
