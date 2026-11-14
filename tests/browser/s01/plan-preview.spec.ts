import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs'
import {readFileSync,writeFileSync} from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../../..'),out=path.join(root,'docs/evidence/S01-WORKFLOW-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json')})

test('数量与到货日驱动真实B01曲线；缺报价仍不可提交，迟到响应不串SKU',async({page})=>{
 test.skip(process.env.S01_PLAN_PREVIEW_CHECK!=='1','Explicit existing local session required')
 test.setTimeout(150000)
 const saved=JSON.parse(readFileSync(path.join(out,'buyer-advice-final-result.json'),'utf8'))
 const lamp=saved.results.find((r:any)=>r.sku==='HLX-LAMP-SURGE'),noquote=saved.results.find((r:any)=>r.sku==='HLX-CASE-NOQUOTE')
 const errors:string[]=[],previews:any[]=[];let modelRequests=0,purchaseWrites=0,otherWrites=0
 page.on('pageerror',e=>errors.push(e.message))
 await page.route('**/api/**',async route=>{
  const r=route.request()
  if(['GET','HEAD','OPTIONS'].includes(r.method()))return route.continue()
  if(r.url().endsWith('/plan-preview')){previews.push(r.postDataJSON());return route.continue()}
  if(r.url().endsWith('/singles'))modelRequests++
  else if(r.url().endsWith('/requisition'))purchaseWrites++
  else otherWrites++
  await route.abort()
 })
 const chart=page.locator('.plan-chart'),curve=chart.locator('[data-curve="plan"]'),quantity=page.getByLabel('采购数量',{exact:true})
 const submit=page.getByRole('button',{name:'确认并提交',exact:true})
 const waitPreview=()=>page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/plan-preview')&&r.ok())
 const initialResponse=waitPreview();await page.goto(lamp.url)
 const startingPlan=await(await initialResponse).json()
 await expect(curve).toBeVisible({timeout:30000});await expect(quantity).toHaveValue('56')
 await expect(page.locator('.arrival-value')).toHaveText('11/17')
 await expect(page.getByLabel('到货日期',{exact:true})).toHaveCount(0)
 await expect(chart).toContainText('按计划补货')
 for(const copy of ['仅用于库存试算','提交至 ERP 待审批。','人工确认并提交请购'])await expect(page.getByText(copy,{exact:true})).toHaveCount(0)
 await page.screenshot({path:path.join(out,'screenshots/42-plan-known-arrival.png'),fullPage:true})
 const defaultD=await curve.getAttribute('d')
 let response=waitPreview();await quantity.fill('60');let plan=await(await response).json()
 await expect(curve).toBeVisible();expect(plan.quantity).toBe(60)
 expect(Number(plan.evaluation.closingBalance)-Number(startingPlan.evaluation.closingBalance)).toBeCloseTo(4)
 await expect(curve).not.toHaveAttribute('d',defaultD!)
 await expect(page.getByLabel('调整原因',{exact:true})).toBeVisible()
 await expect(submit).toBeDisabled()
 await page.getByLabel('调整原因',{exact:true}).fill('采购数量按整箱增加')
 await page.getByRole('checkbox',{name:'已核对当前店仓、数量、已有采购和来源限制'}).check()
 await expect(submit).toBeEnabled()
 await page.getByRole('button',{name:'调整',exact:true}).click()
 const date=page.getByLabel('到货日期',{exact:true})
 response=waitPreview();await date.fill('2026-11-20');plan=await(await response).json()
 await expect(chart).toContainText('假设补货后');await expect(submit).toBeDisabled()
 expect(plan.evaluation.firstShortageDate).toBe('2026-11-17')
 await expect(chart).toContainText('11-17 起仍有缺口')
 response=waitPreview();await page.getByRole('button',{name:'恢复',exact:true}).click();await response
 await expect(chart).toContainText('按计划补货')
 await page.goto(noquote.url);await expect(quantity).toHaveValue('53');await expect(date).toBeVisible()
 await expect(date).toHaveValue('');await expect(curve).toHaveCount(0)
 await expect(chart).toContainText('填写到货日后查看补货效果')
 response=waitPreview();await date.fill('2026-11-20');const noquotePlan=await(await response).json()
 await expect(curve).toBeVisible();await expect(chart).toContainText('假设补货后')
 await page.getByRole('checkbox',{name:'已核对当前店仓、数量、已有采购和来源限制'}).check();await expect(submit).toBeDisabled()
 await page.screenshot({path:path.join(out,'screenshots/43-plan-assumed-arrival.png'),fullPage:true})
 // Fail a read-only preview explicitly; stale successful plans must disappear.
 await page.route('**/plan-preview',route=>route.fulfill({status:503,json:{code:'LOCAL_API_UNAVAILABLE'}}))
 await quantity.fill('60');await expect(page.locator('.plan-field-error')).toBeVisible();await expect(curve).toHaveCount(0)
 await page.unroute('**/plan-preview')
 response=waitPreview();await chart.getByRole('button',{name:'重试',exact:true}).click();await response;await expect(curve).toBeVisible()
 await date.fill('2026-12-30');await expect(page.locator('.plan-field-error')).toContainText('到货日期须在');await expect(curve).toHaveCount(0)
 response=waitPreview();await date.fill('2026-11-20');await response;await expect(curve).toBeVisible()
 await page.setViewportSize({width:820,height:1000});await quantity.scrollIntoViewIfNeeded()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
 await page.screenshot({path:path.join(out,'screenshots/44-plan-mobile.png'),fullPage:true})
 // Hold a real response from SKU A while navigating to SKU B.
 let started!:()=>void,release!:()=>void;const startedPromise=new Promise<void>(r=>started=r),gate=new Promise<void>(r=>release=r)
 await page.route('**/plan-preview',async route=>{const result=await route.fetch();started();await gate;try{await route.fulfill({response:result})}catch{/* request aborted by new context */}})
 await quantity.fill('64');await startedPromise
 await page.goto(lamp.url);release();await page.unroute('**/plan-preview')
 await expect(quantity).toHaveValue('56');await expect(chart).toContainText('56 件 · 11-17');await expect(chart).not.toContainText('64 件')
 await page.reload();await expect(curve).toBeVisible();await expect(quantity).toHaveValue('56')
 expect(errors).toEqual([]);expect(modelRequests).toBe(0);expect(purchaseWrites).toBe(0);expect(otherWrites).toBe(0)
 writeFileSync(path.join(out,'plan-preview-result.json'),JSON.stringify({result:'PASS',source:'Existing registered teaching reports and real local B01 preview API; no new ERP acquisition or models',
  knownDefault:{quantity:56,date:'2026-11-17'},changedQuantity:60,changedDate:'2026-11-20',noquotePlan,
  checks:['quantity changes curve','date changes shortage risk','restore quote date','missing quote preview without submit','removed redundant copy','controlled 503 clears old curve and retries','out-of-window rejected','820px no overflow','late response isolated across SKU','reload restores defaults'],
  controlledFailure:'503 explicitly injected; not a live ERP/model failure',previewRequests:previews.length,modelRequests,purchaseWrites,otherWrites,pageErrors:errors},null,2))
})
