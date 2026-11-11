// Documentation migration checks. No product implementation, network or deployment.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const {createRequire}=require('module'),{pathToFileURL}=require('url');
const req=createRequire(process.env.PLAYWRIGHT_MODULE||require.resolve('playwright/package.json'));
const {chromium}=req('playwright'),root=path.resolve(__dirname,'../..'),out=path.join(__dirname,'local');
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage();const checks=[],errors=[],remote=[];
 page.on('pageerror',e=>errors.push(String(e)));
 await page.route(/^https?:\/\//,r=>{remote.push(r.request().url());r.abort();});
 try{
  for(const rel of ['docs/requirements/REQUIREMENTS.html','docs/requirements/BUSINESS_GUIDE.html','docs/architecture/ARCHITECTURE.html','docs/architecture/DEVELOPMENT_DESIGN.html','docs/agents/AI_DETAILED_DESIGN.html','docs/reports/FEASIBILITY.html']){
   await page.goto(pathToFileURL(path.join(root,rel)).href);
   for(const width of [1440,1024,390]){
    await page.setViewportSize({width,height:1000});
    const m=await page.evaluate(()=>({width:innerWidth,content:document.documentElement.scrollWidth,heading:!!document.querySelector('h1'),brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.getAttribute('src'))}));
    assert(m.content<=m.width,`${rel}: ${width} content ${m.content}`);assert(m.heading);assert.deepEqual(m.brokenImages,[]);
    checks.push({page:rel,width,result:'PASS'});
   }
   if(rel.endsWith('ARCHITECTURE.html')){
    await page.setViewportSize({width:1440,height:1000});const b=page.locator('button[data-command="fit"]').first();await b.click();assert.notEqual(await page.locator('.diagram-stage').first().getAttribute('data-scale'),'1');
   }
  }
  assert.deepEqual(errors,[]);assert.deepEqual(remote,[]);
  const result={status:'PASS',scope:'LOCAL_DOCUMENT_MIGRATION_ONLY',checks,errors,remoteRequests:remote};
  fs.writeFileSync(path.join(out,'document-browser-check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({status:'PASS',layoutChecks:checks.length,errors:errors.length,remoteRequests:remote.length}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
