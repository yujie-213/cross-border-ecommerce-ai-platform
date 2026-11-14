import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs'
import {readFileSync,writeFileSync} from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../../..'),out=path.join(root,'docs/evidence/S01-WORKFLOW-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json'),actionTimeout:15000})
test('获准开启采购后：人工确认与MOQ整箱仍强制，不执行提交',async({page})=>{
 test.skip(process.env.S01_REQUISITION_ENABLED_CHECK!=='1','Explicit purchase capability authorization required')
 test.setTimeout(90000);let writes=0
 await page.route('**/api/v1/s01/v2/singles/*/requisition',async r=>{if(r.request().method()==='POST'){writes++;await r.abort()}else await r.continue()})
 await page.goto('/#/home');const options=await(await page.request.get('/api/v1/s01/v2/options')).json();expect(options.canSubmit).toBe(true)
 const history=await(await page.request.get('/api/v1/s01/v2/batches')).json();const batch=history.items.find((r:any)=>r.state==='SUCCEEDED'&&r.analysisRange==='OWNED_REGISTERED').taskRef.taskId
 const models=JSON.parse(readFileSync(path.join(out,'models.json'),'utf8'));const lamp=models.results.find((r:any)=>r.sku==='HLX-LAMP-SURGE')
 await page.goto(`/#/sku/${lamp.entityKey}?batch=${batch}&single=${lamp.taskId}`)
 const quantity=page.getByLabel('采购数量',{exact:true}),check=page.getByRole('checkbox',{name:'已核对当前店仓、数量、已有采购和来源限制'}),submit=page.getByRole('button',{name:'确认并提交'})
 await expect(quantity).toHaveValue('56');await expect(page.locator('.purchase-state')).toContainText('可继续人工确认');await expect(submit).toBeDisabled();await check.check();await expect(submit).toBeEnabled()
 await quantity.fill('60');await check.check();await expect(submit).toBeDisabled();await page.getByLabel('调整原因',{exact:true}).fill('验收：调整计划量，不执行提交');await expect(submit).toBeEnabled()
 await quantity.fill('58');await check.check();await expect(submit).toBeDisabled();await expect(page.locator('.purchase-panel')).toContainText('整箱倍数')
 await quantity.fill('56');await check.check();await expect(submit).toBeEnabled();await page.screenshot({path:path.join(out,'screenshots/21-authorized-human-confirmation.png'),fullPage:true})
 const blocked=models.results.find((r:any)=>r.sku==='HLX-CASE-NOQUOTE');await page.goto(`/#/sku/${blocked.entityKey}?batch=${batch}&single=${blocked.taskId}`);await expect(quantity).toHaveValue('53');await expect(page.locator('.purchase-state')).toContainText('没有唯一有效供应商报价');await check.check();await expect(submit).toBeDisabled()
 expect(writes).toBe(0);writeFileSync(path.join(out,'permission-result.json'),JSON.stringify({result:'PASS',localCapabilityEnabled:true,manualAcknowledgementRequired:true,changeReasonRequired:true,cartonMultipleEnforced:true,missingQuoteStillBlocked:true,erpSubmissions:0},null,2))
})
