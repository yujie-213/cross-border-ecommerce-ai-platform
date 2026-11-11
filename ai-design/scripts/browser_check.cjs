/* 对本轮静态HTML做本地浏览器检查；非业务界面自动化。 */
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const {createRequire}=require('module');
const req=createRequire('C:/Users/Windows/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const {chromium}=req('playwright');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'ai-design');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage();const errors=[],remote=[];
 page.on('pageerror',e=>errors.push(String(e)));
 await page.route('https://**/*',r=>{remote.push(r.request().url());r.abort()});
 await page.route('http://**/*',r=>{remote.push(r.request().url());r.abort()});
 const target=path.join(root,'智慧中台AI应用项目_AI模块详细开发设计文档.html');
 await page.goto(pathToFileURL(target).href);await page.waitForLoadState('load');
 const checks=[];
 for(const viewport of [{width:1440,height:900},{width:1920,height:1080},{width:390,height:844}]){
   await page.setViewportSize(viewport);
   for(const theme of ['light','dark']){
     await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);
     const m=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,svg:document.querySelectorAll('figure svg').length,tables:document.querySelectorAll('table').length,headings:document.querySelectorAll('article h2,article h3').length,theme:document.documentElement.dataset.theme,brokenFigures:[...document.querySelectorAll('figure svg')].filter(s=>s.getBoundingClientRect().height<=0).length}));
     checks.push({viewport,theme,...m,status:m.scrollWidth<=m.width&&m.svg===19&&m.brokenFigures===0?'pass':'fail'});
   }
 }
 await page.setViewportSize({width:1440,height:1000});
 await page.evaluate(()=>document.documentElement.dataset.theme='light');
 await page.getByLabel('章节目录 · 17章 / 19图').fill('缓存');
 const filtered=await page.locator('nav a:visible').count();
 const filterCorrect=await page.locator('nav a:visible').evaluateAll(links=>links.length>0&&links.every(a=>a.textContent.includes('缓存')));
 await page.getByLabel('章节目录 · 17章 / 19图').fill('');
 await page.locator('#theme').click();
 const toggle=await page.evaluate(()=>document.documentElement.dataset.theme==='dark');
 await page.screenshot({path:path.join(out,'review/reading-dark-top.png')});
 await page.locator('#theme').click();
 await page.screenshot({path:path.join(out,'review/reading-light-top.png')});
 await page.locator('#figure-05').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'review/cache-diagram.png')});
 await page.locator('#figure-04').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'review/agent-loop-d02.png')});
 await page.locator('#figure-18').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'review/pause-resume-d03.png')});
 await page.locator('#figure-19').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'review/voc-contract-d05.png')});
 await page.locator('#figure-10').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'review/s03-workflow.png')});
 await page.locator('#figure-02').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'review/runtime-boundary.png')});
 await page.locator('#figure-07').scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'review/llmops-loop.png')});
 await page.locator('h3').filter({hasText:'9.4 缓存准入'}).scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(out,'review/cache-matrix.png')});
 const report={artifact:target,sha256:require('crypto').createHash('sha256').update(fs.readFileSync(target)).digest('hex'),status:checks.every(c=>c.status==='pass')&&errors.length===0&&remote.length===0&&filterCorrect&&toggle?'pass':'fail',checks,errors,remoteRequests:remote,interactions:{tocFilterMatches:filtered,filterCorrect,themeToggle:toggle},visualReview:'pending',screenshots:['reading-dark-top.png','reading-light-top.png','cache-diagram.png','s03-workflow.png','runtime-boundary.png','llmops-loop.png','cache-matrix.png']};
 fs.writeFileSync(path.join(out,'review/browser-check.json'),JSON.stringify(report,null,2),'utf8');
 await browser.close();console.log(JSON.stringify({status:report.status,measurements:checks.length,errors,remoteRequests:remote,filtered,toggle}));
 if(report.status!=='pass')process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
