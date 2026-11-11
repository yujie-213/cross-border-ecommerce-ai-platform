// Documentation-only renderer. MERMAID_RENDER_JS may override the existing pinned local documentation bundle.
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{createRequire}=require('module'),{pathToFileURL}=require('url');
const root=path.resolve(__dirname,'../..');
const req=createRequire(process.env.PLAYWRIGHT_MODULE||require.resolve('playwright/package.json'));
const {chromium}=req('playwright');const executablePath=process.env.BROWSER_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const d=path.join(__dirname,'diagrams'),source=fs.readFileSync(path.join(d,'plan-flow.mmd'),'utf8');
 if(!process.argv.includes('--browser-only')){
 const b=await chromium.launch({headless:true,executablePath});const p=await b.newPage();
 await p.setContent('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><body></body></html>');
 await p.addScriptTag({path:process.env.MERMAID_RENDER_JS||path.join(root,'docs/agents/assets/mermaid-11.4.1.min.js')});
 await p.evaluate(()=>mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',fontFamily:'Microsoft YaHei, sans-serif',themeVariables:{fontSize:'17px',primaryColor:'#edf6f3',primaryTextColor:'#172a3b',primaryBorderColor:'#278b7c',lineColor:'#526e80'},flowchart:{htmlLabels:false,useMaxWidth:false,curve:'linear',rankSpacing:55,nodeSpacing:45}}));
 const svg=await p.evaluate(async source=>(await mermaid.render('plan_flow_v2',source)).svg,source);if(svg.includes('Syntax error'))throw Error('Mermaid rendering error');
 fs.writeFileSync(path.join(d,'plan-flow.svg'),svg,'utf8');fs.writeFileSync(path.join(d,'render-receipt.json'),JSON.stringify({renderer:'Mermaid 11.4.1 / local headless Edge',sourceSha256:hash(Buffer.from(source)),svgSha256:hash(Buffer.from(svg)),status:'pass'},null,2));
 await b.close();console.log('Mermaid plan flow rendered');
 }
 const browser=await chromium.launch({headless:true,executablePath});const page=await browser.newPage();
 const target=path.join(root,'docs/PLAN.html');
 if(fs.existsSync(target)&&(process.argv.includes('--browser-check')||process.argv.includes('--browser-only'))){
  const errors=[],remote=[];page.on('pageerror',e=>errors.push(String(e)));await page.route(/^https?:\/\//,r=>{remote.push(r.request().url());r.abort()});await page.goto(pathToFileURL(target).href);const checks=[];
  for(const v of [{width:1440,height:900},{width:1920,height:1080},{width:390,height:844}]){await page.setViewportSize(v);for(const theme of ['light','dark']){await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);const x=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,svg:document.querySelectorAll('figure svg').length,sections:document.querySelectorAll('article h2').length}));checks.push({...x,viewport:v,theme,pass:x.width>=x.scrollWidth&&x.svg===1});}}
  await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.documentElement.dataset.theme='light');const local=path.join(__dirname,'local');fs.mkdirSync(local,{recursive:true});await page.screenshot({path:path.join(local,'plan-top.png')});await page.locator('figure').screenshot({path:path.join(local,'plan-flow.png')});
  fs.writeFileSync(path.join(__dirname,'browser-check.json'),JSON.stringify({status:checks.every(x=>x.pass)&&!errors.length&&!remote.length?'pass':'fail',htmlSha256:hash(fs.readFileSync(target)),checks,errors,remoteRequests:remote,visualReview:'recorded separately'},null,2));
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
