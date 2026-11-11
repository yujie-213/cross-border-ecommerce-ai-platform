/* 仅渲染本轮文档的Mermaid；不启动业务服务、不执行应用代码。 */
const fs=require('fs'),path=require('path');
const {createRequire}=require('module');
const req=createRequire(process.env.PLAYWRIGHT_MODULE||require.resolve('playwright/package.json'));
const {chromium}=req('playwright');
const root=path.resolve(__dirname,'../../..'), out=path.join(root,'docs/agents');
const {pathToFileURL}=require('url');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1800,height:1200}});
 const runtimeErrors=[];page.on('pageerror',e=>runtimeErrors.push(String(e)));
 await page.goto(pathToFileURL(path.join(out,'assets/render.html')).href);
 await page.addScriptTag({path:path.join(out,'assets/mermaid-11.4.1.min.js')});
 await page.evaluate(()=>mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',fontFamily:'Microsoft YaHei, sans-serif',themeVariables:{fontSize:'16px',primaryColor:'#edf6f3',primaryTextColor:'#17283c',primaryBorderColor:'#348b80',lineColor:'#536c7d',secondaryColor:'#f4f6fa',tertiaryColor:'#fef7e8'},flowchart:{htmlLabels:false,curve:'linear',nodeSpacing:36,rankSpacing:50,useMaxWidth:false},sequence:{useMaxWidth:false,wrap:true,actorMargin:45,messageMargin:38,noteMargin:18,diagramMarginX:24,diagramMarginY:24},maxTextSize:120000}));
 const manifest=JSON.parse(fs.readFileSync(path.join(out,'mermaid-manifest.json'),'utf8'));
 const results=[];
 for(const d of manifest){
   const source=fs.readFileSync(path.join(out,d.source),'utf8');
   try{
     const oldSource=path.join(out,'../../archive/ai-review-d01-d05/before/mermaid',path.basename(d.source));
     if(fs.existsSync(oldSource)&&fs.existsSync(path.join(out,d.svg))&&source===fs.readFileSync(oldSource,'utf8')){
       await page.evaluate(async s=>await mermaid.parse(s),source);
       const prior=JSON.parse(fs.readFileSync(path.join(out,'../../archive/ai-review-d01-d05/pre-revision-manifest.json'),'utf8'));
       const old=prior.find(x=>x.path.replace(/\\/g,'/')==='ai-design/'+d.svg);
       const bytes=fs.readFileSync(path.join(out,d.svg));
       if(!old||require('crypto').createHash('sha256').update(bytes).digest('hex')!==old.sha256)throw Error('Unchanged SVG no longer matches pre-revision bytes');
       results.push({id:d.id,status:'pass',mode:'unchanged-source-parsed-svg-preserved',bytes:bytes.length});
       console.log(d.id+' preserved / parse pass');continue;
     }
     const svg=await page.evaluate(async({id,source})=>(await mermaid.render('diagram_'+id.replace(/-/g,'_'),source)).svg,{id:d.id,source});
     if(svg.includes('Syntax error in text'))throw Error('rendered error SVG');
     fs.writeFileSync(path.join(out,d.svg),svg,'utf8');
     results.push({id:d.id,status:'pass',mode:'rendered',bytes:Buffer.byteLength(svg)});
     console.log(d.id+' pass');
   }catch(e){results.push({id:d.id,status:'fail',error:String(e)});console.error(d.id+' '+String(e));}
 }
 await browser.close();
 const report={renderer:'Mermaid 11.4.1 / local Edge headless',status:results.every(x=>x.status==='pass')&&runtimeErrors.length===0?'pass':'fail',runtimeErrors,diagrams:results};
 fs.writeFileSync(path.join(out,'review/mermaid-render-check.json'),JSON.stringify(report,null,2),'utf8');
 if(report.status!=='pass')process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
