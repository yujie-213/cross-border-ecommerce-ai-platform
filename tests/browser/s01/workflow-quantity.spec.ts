import {test,expect} from '../../../frontend/node_modules/@playwright/test/index.mjs'
import {readFileSync,writeFileSync} from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../../..'),out=path.join(root,'docs/evidence/S01-WORKFLOW-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json'),actionTimeout:15000})
test('真实商品：预填建议数量、允许先调整、只在改量后显示原因且不放开采购',async({page})=>{
 test.skip(process.env.S01_WORKFLOW_LIVE!=='1','Explicit real local session required');test.setTimeout(90000)
 const models=JSON.parse(readFileSync(path.join(out,'models.json'),'utf8'));let writes=0
 page.on('request',r=>{if(r.method()==='POST'&&/\/requisition(?:$|\?)/.test(r.url()))writes++})
 await page.goto('/#/home');const all=await(await page.request.get('/api/v1/s01/v2/batches')).json();const batch=all.items.find((r:any)=>r.state==='SUCCEEDED'&&r.analysisRange==='OWNED_REGISTERED').taskRef.taskId
 const noquote=models.results.find((r:any)=>r.sku==='HLX-CASE-NOQUOTE')
 await page.goto(`/#/sku/${noquote.entityKey}?batch=${batch}&single=${noquote.taskId}`)
 const input=page.getByLabel('采购数量',{exact:true})
 await expect(input).toHaveValue('53');await expect(input).toBeEnabled();await expect(page.getByLabel('调整原因',{exact:true})).toHaveCount(0)
 await input.fill('52');await expect(page.getByLabel('调整原因',{exact:true})).toBeVisible();await page.getByLabel('调整原因',{exact:true}).fill('先调整计划量，补齐有效报价后再核实')
 await expect(page.getByRole('button',{name:'确认并提交'})).toBeDisabled()
 await page.screenshot({path:path.join(out,'screenshots/19-editable-reference-proposal.png'),fullPage:true})
 await input.fill('53');await expect(page.getByLabel('调整原因',{exact:true})).toHaveCount(0)
 await page.getByRole('checkbox',{name:'已核对当前店仓、数量、已有采购和来源限制'}).check();await expect(page.getByRole('button',{name:'确认并提交'})).toBeDisabled()
 const lamp=models.results.find((r:any)=>r.sku==='HLX-LAMP-SURGE')
 await page.goto(`/#/sku/${lamp.entityKey}?batch=${batch}&single=${lamp.taskId}`)
 await expect(input).toHaveValue('56');await expect(page.getByLabel('调整原因',{exact:true})).toHaveCount(0)
 await input.fill('60');await expect(page.getByLabel('调整原因',{exact:true})).toBeVisible();await page.getByLabel('调整原因',{exact:true}).fill('按整箱调整计划量，提交前再核对')
 await page.screenshot({path:path.join(out,'screenshots/20-manual-quantity-reason.png'),fullPage:true})
 await page.reload();await expect(input).toHaveValue('56');await expect(page.getByLabel('调整原因',{exact:true})).toHaveCount(0)
 expect(writes).toBe(0)
 writeFileSync(path.join(out,'quantity-feedback-result.json'),JSON.stringify({result:'PASS',noQuoteReferenceDefault:53,constrainedCandidateDefault:56,editableWithoutSubmitPermission:true,reasonOnlyWhenChanged:true,reasonHidesAfterRestore:true,submitStillDisabled:true,erpWrites:0},null,2))
})
