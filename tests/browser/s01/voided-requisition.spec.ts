import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs'
import {mkdirSync,writeFileSync} from 'node:fs'
import path from 'node:path'

const root=path.resolve(import.meta.dirname,'../../..')
const out=path.join(root,'docs/evidence/S01-VOIDED-REQUISITION-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json')})

test('verified void offers a fresh analysis without AI or procurement writes; status colors match business meaning',async({page})=>{
 test.skip(process.env.S01_VOIDED_CHECK!=='1','Explicit existing teaching session required')
 test.setTimeout(180000);mkdirSync(out,{recursive:true})
 const errors:string[]=[],analyses:unknown[]=[];let purchaseWrites=0
 page.on('pageerror',e=>errors.push(e.message))
 await page.route('**/api/**',async route=>{
  const request=route.request()
  if(['GET','HEAD','OPTIONS'].includes(request.method())||request.url().endsWith('/plan-preview'))return route.continue()
  if(request.url().endsWith('/singles')){
   const body=request.postDataJSON();expect(body.explainAI).toBe(false);analyses.push(body);return route.continue()
  }
  purchaseWrites++;await route.abort()
 })
 const response=await page.request.get('/api/v1/s01/v2/batches')
 expect(response.status(),'Existing saved local session must still be valid').toBe(200)
 const batches=await response.json()
 const batch=batches.items.find((row:any)=>row.state==='SUCCEEDED'&&row.analysisRange==='OWNED_REGISTERED').taskRef.taskId
 await page.goto('/#/suggestions?batch='+batch)
 const colors={red:'rgb(173, 55, 51)',yellow:'rgb(138, 81, 11)',green:'rgb(36, 102, 75)',blue:'rgb(36, 91, 156)'}
 await expect(page.locator('tbody .chip.confirm').first()).toHaveCSS('color',colors.red)
 await expect(page.locator('tbody .chip.review').first()).toHaveCSS('color',colors.yellow)
 await expect(page.locator('tbody .chip.none').first()).toHaveCSS('color',colors.green)
 await page.screenshot({path:path.join(out,'replenishment-colors.png'),fullPage:true})
 await page.goto('/#/requisitions?batch='+batch)
 for(const [label,color] of [['待审核',colors.yellow],['待下单',colors.blue],['已作废',colors.red]]){
  await expect(page.locator('tbody .chip').filter({hasText:label}).first()).toHaveCSS('color',color,{timeout:90000})
 }
 await page.screenshot({path:path.join(out,'purchase-colors.png'),fullPage:true})
 const history=await(await page.request.get('/api/v1/s01/v2/singles')).json()
 let original:any
 for(const row of history.items.filter((row:any)=>row.sku==='HLX-USB-STABLE'&&row.state==='SUCCEEDED')){
  const receipt=await(await page.request.get('/api/v1/s01/v2/singles/'+row.taskRef.taskId+'/requisition')).json()
  if(receipt?.reorderAllowed){original={...row,receipt};break}
 }
 expect(original,'Existing verified voided teaching order').toBeTruthy()
 await page.goto('/#/sku/'+original.entityKey+'?batch='+batch+'&single='+original.taskRef.taskId)
 const reorder=page.getByRole('button',{name:'重新分析并采购',exact:true})
 await expect(reorder).toBeEnabled({timeout:60000})
 await expect(page.locator('.saved-purchase')).toContainText('已作废')
 await expect(page.locator('.saved-purchase .chip')).toHaveCSS('color',colors.red)
 await page.screenshot({path:path.join(out,'voided-can-reorder.png'),fullPage:true})
 const created=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/singles'))
 await reorder.click();const task=await(await created).json()
 const submit=page.getByRole('button',{name:'确认并提交',exact:true})
 await expect(submit).toBeVisible({timeout:90000})
 await expect(page.getByLabel('采购数量',{exact:true})).toHaveValue('40')
 await page.getByRole('checkbox',{name:'已核对当前店仓、数量、已有采购和来源限制'}).check()
 await expect(submit).toBeEnabled()
 expect(await(await page.request.get('/api/v1/s01/v2/singles/'+task.taskRef.taskId+'/requisition')).json()).toBeNull()
 await page.screenshot({path:path.join(out,'fresh-analysis-ready.png'),fullPage:true})
 await page.setViewportSize({width:820,height:1000})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
 expect(analyses).toHaveLength(1);expect(purchaseWrites).toBe(0);expect(errors).toEqual([])
 writeFileSync(path.join(out,'browser-result.json'),JSON.stringify({result:'PASS',source:'Real local browser, existing registered teaching order, exact ERP readback and one new analysis',
  originalReport:original.taskRef.taskId,newReport:task.taskRef.taskId,colors,analyses:analyses.length,modelCalls:0,purchaseWrites,pageErrors:errors},null,2))
})
