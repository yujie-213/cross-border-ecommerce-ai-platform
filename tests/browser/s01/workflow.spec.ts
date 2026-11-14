import { test, expect } from '../../../frontend/node_modules/@playwright/test/index.mjs'
import { mkdirSync,writeFileSync } from 'node:fs'
import path from 'node:path'
const root=path.resolve(import.meta.dirname,'../../..')
const output=path.join(root,'docs/evidence/S01-WORKFLOW-20261115')
test.use({storageState:path.join(root,'data/private/local-platform/workflow-browser-state.json'),actionTimeout:15000})
test('采购人员真实流程：发现风险、分仓分析、AI建议、ERP跟进',async({page})=>{
 test.skip(process.env.S01_WORKFLOW_LIVE!=='1','Explicit live ERP/model acceptance required')
 test.setTimeout(600000);mkdirSync(path.join(output,'screenshots'),{recursive:true})
 const errors:string[]=[],result:any={screens:[],newPurchaseWrites:0,modelRequests:0}
 page.on('pageerror',e=>errors.push(e.message))
 page.on('request',r=>{if(r.method()==='POST' && /\/requisition(?:$|\?)/.test(r.url()))result.newPurchaseWrites++})
 async function shot(name:string){await page.screenshot({path:path.join(output,'screenshots',name+'.png'),fullPage:true});result.screens.push(name)}
 async function find(sku:string){await page.goto('/#/suggestions');await page.getByLabel('查找商品',{exact:true}).fill(sku);await expect(page.locator('tbody tr')).toHaveCount(1,{timeout:30000});await expect(page.locator('tbody tr').first()).toContainText(sku);await expect(page.locator('tbody a')).toHaveAttribute('aria-disabled','false');await page.getByRole('link',{name:'分析商品 →',exact:true}).click();await expect(page.locator('.product-header')).toContainText(sku)}
 await page.goto('/#/home');await expect(page.getByRole('heading',{name:'工作首页',exact:true})).toBeVisible();await shot('01-platform-home')
 await page.getByRole('link',{name:/智能补货.*进入工作区/}).click();await expect(page.getByRole('heading',{name:'今天，先处理这些商品',exact:true})).toBeVisible();await expect(page.locator('.attention-row').first()).toBeVisible({timeout:45000});await shot('02-workbench')
 await page.getByRole('link',{name:'查看全部商品 →'}).click();await expect(page.locator('tbody tr')).toHaveCount(10,{timeout:30000});await shot('03-product-list')
 await find('HLX-USB-STABLE');await expect(page.locator('.warehouse-choice')).toHaveCount(2);await shot('04-usb-east')
 await page.locator('.warehouse-choice').filter({hasText:'西部仓'}).click();await expect(page.locator('.warehouse-choice.selected')).toContainText('西部仓');await expect(page.locator('.warehouse-choice.selected .warehouse-quantity strong')).toContainText('0');await shot('05-usb-west')
 await page.goBack();await expect(page.locator('.warehouse-choice.selected')).toContainText('东部仓');await page.reload();await expect(page.locator('.warehouse-choice.selected')).toContainText('东部仓');result.warehouseNavigation='PASS'
 await find('HLX-LAMP-SURGE');await expect(page.getByRole('button',{name:'更新补货分析',exact:true})).toBeEnabled();await shot('06-surge-before-ai')
 if(process.env.S01_WORKFLOW_MODELS==='1' && process.env.S01_WORKFLOW_SKIP_SURGE!=='1'){
  await page.getByRole('button',{name:'生成 AI 建议',exact:true}).click();result.modelRequests++
  await expect(page.getByRole('region',{name:'AI 行动建议'})).toHaveAttribute('data-state','running');await shot('07-ai-running')
  await expect(page.getByRole('region',{name:'AI 行动建议'})).not.toHaveAttribute('data-state','running',{timeout:240000})
  result.surgeAI=await page.getByRole('region',{name:'AI 行动建议'}).getAttribute('data-state');await shot('08-surge-ai-result')
  expect(result.surgeAI).toBe('ready')
 }
 await find('HLX-CASE-NOQUOTE');await expect(page.getByRole('button',{name:'更新补货分析',exact:true})).toBeEnabled();await expect(page.getByRole('button',{name:'确认并提交'})).toBeDisabled();await page.getByRole('button',{name:'更新补货分析',exact:true}).click();await expect(page.getByRole('region',{name:'AI 行动建议'})).toHaveAttribute('data-state','running');await expect(page.locator('.product-actions button')).toHaveText('更新补货分析',{timeout:240000});await shot('09-no-quote-analysis')
 if(process.env.S01_WORKFLOW_MODELS==='1'){
  await page.getByRole('button',{name:/生成 AI 建议|重试 AI 建议/,exact:true}).click();result.modelRequests++
  await expect(page.getByRole('region',{name:'AI 行动建议'})).toHaveAttribute('data-state','running');await expect(page.getByRole('region',{name:'AI 行动建议'})).not.toHaveAttribute('data-state','running',{timeout:240000})
  result.noQuoteSingle=page.url().split('single=')[1];result.noQuoteAI=await page.getByRole('region',{name:'AI 行动建议'}).getAttribute('data-state');await shot('10-no-quote-ai');expect(result.noQuoteAI).toBe('ready');await expect(page.getByRole('button',{name:'确认并提交'})).toBeDisabled()
 }
 await find('HLX-MAT-SPARSE');await expect(page.getByRole('region',{name:'AI 行动建议'})).not.toHaveAttribute('data-state','ready');await expect(page.getByRole('region',{name:'AI 行动建议'})).toContainText('HLX-MAT-SPARSE');await shot('11-sparse-history');result.crossSkuAI='PASS'
 await page.setViewportSize({width:1024,height:900});await shot('12-detail-1024');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
 await page.setViewportSize({width:1440,height:1000});await page.getByRole('link',{name:/请购管理/}).click();await expect(page.getByRole('heading',{name:'请购与采购跟进',exact:true})).toBeVisible();await expect(page.locator('tbody tr').first()).toBeVisible({timeout:90000});await expect(page.getByRole('button',{name:'刷新 ERP 状态'})).toBeEnabled({timeout:90000});await shot('13-erp-purchase-tracking')
 result.purchaseTracking=await page.locator('tbody tr').allInnerTexts();result.pageErrors=errors
 writeFileSync(path.join(output,'browser-result.json'),JSON.stringify(result,null,2));expect(errors).toEqual([]);expect(result.newPurchaseWrites).toBe(0)
})
