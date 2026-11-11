// Documentation only. Markdown is the authority; this builds/checks its offline reading view.
// Build: node docs/agents/scripts/build_s01_reading.cjs
// Check: node docs/agents/scripts/build_s01_reading.cjs --check
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { createRequire } = require('module');
const { execFileSync } = require('child_process');
const { pathToFileURL } = require('url');
const assert = require('assert/strict');
const root = path.resolve(__dirname, '../../..');
const sourcePath = path.join(root, 'docs/agents/S01_补货Agent专项详细设计.md');
const outputPath = sourcePath.replace(/\.md$/, '.html');
const runtimePath = path.join(root, 'docs/agents/assets/mermaid-11.4.1.min.js');
const req = createRequire(process.env.PLAYWRIGHT_MODULE ||
  'C:/Users/Windows/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/package.json');
const { chromium } = req('playwright');
const sha = x => crypto.createHash('sha256').update(x).digest('hex');
const esc = x => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const css = `
:root{color-scheme:light;--bg:#f4f6f8;--paper:#fff;--ink:#202d3a;--muted:#5c6b79;--line:#dce4e8;--accent:#126b65;--soft:#e9f3f1;--code:#f2f5f7;--warm:#fff4e2;--warm-ink:#805013}
html[data-theme=dark]{color-scheme:dark;--bg:#101c26;--paper:#182934;--ink:#e3edf1;--muted:#b0c2cd;--line:#38505d;--accent:#85d1c4;--soft:#213e43;--code:#12222d;--warm:#3b3325;--warm-ink:#f2d3a2}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:32px}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.9 "Segoe UI","Microsoft YaHei",sans-serif}a{color:var(--accent);text-underline-offset:3px}button,input{font:inherit}button,a.button{border:1px solid var(--line);border-radius:6px;padding:7px 13px;background:var(--paper);color:var(--ink);cursor:pointer;line-height:1.6;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px}button:hover,a.button:hover{border-color:var(--accent);color:var(--accent)}:focus-visible{outline:3px solid #428fcb;outline-offset:3px}.skip{position:fixed;top:-80px;left:12px;z-index:10;background:var(--paper);padding:12px}.skip:focus{top:8px}
.cover{border-bottom:1px solid var(--line);background:var(--paper)}.cover-inner{max-width:1500px;margin:auto;padding:42px 38px 30px}.eyebrow{font-size:13px;letter-spacing:.05em;color:var(--muted);margin:0 0 10px}.cover h1{font-size:clamp(25px,3vw,36px);line-height:1.45;margin:0 0 12px;font-weight:650}.subtitle{color:var(--muted);margin:0 0 21px}.tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:14px}.tools .primary{background:#126b65;color:#fff;border-color:#126b65}.tools .primary:hover{background:#0b5651;color:#fff}.reading-note{max-width:1040px;font-size:13px;color:var(--muted);margin:18px 0 0}.reading-note code{font-size:12px}
.layout{display:grid;grid-template-columns:242px minmax(0,1fr);gap:26px;max-width:1500px;margin:auto;padding:30px 32px 70px}.sidebar{position:sticky;top:20px;align-self:start;max-height:calc(100vh - 40px);overflow:auto;padding-right:9px;scrollbar-width:thin}.nav-title{font-size:12px;font-weight:650;letter-spacing:.06em;color:var(--muted);margin:8px 0}.toc a,.diagrams-nav a{display:block;border-left:2px solid transparent;text-decoration:none;color:var(--muted);font-size:13px;line-height:1.55;padding:8px 10px}.toc a:hover,.toc a.active,.diagrams-nav a:hover{background:var(--soft);color:var(--accent);border-left-color:var(--accent)}.diagrams-nav{margin-top:24px;border-top:1px solid var(--line);padding-top:14px}.diagrams-nav a{font-size:12px;padding:6px 10px}.main{min-width:0;padding:30px 40px 46px;border:1px solid var(--line);background:var(--paper);border-radius:10px}.notice{padding:14px 18px;background:var(--soft);border-left:3px solid var(--accent);font-size:14px;margin:0 0 28px}.notice p{margin:0}article h2{font-size:25px;line-height:1.5;margin:48px 0 20px;padding-top:27px;border-top:1px solid var(--line)}article h2:first-of-type{margin-top:30px}article h3{font-size:19px;line-height:1.65;margin:32px 0 15px}p,li,td,th{overflow-wrap:anywhere}p{margin:13px 0}ul,ol{padding-left:25px}li{margin:7px 0}code{font-family:Consolas,monospace;font-size:.86em;padding:2px 4px;background:var(--code);border-radius:3px}pre{margin:18px 0;padding:20px;background:var(--code);border:1px solid var(--line);border-radius:7px;overflow:auto;white-space:pre;line-height:1.7;font-size:13px;tab-size:4}pre code{font-size:inherit;background:none;padding:0}pre:focus-visible{outline-offset:1px}.table-wrap{overflow-x:auto;margin:22px 0;border:1px solid var(--line);border-radius:7px;scrollbar-width:thin}table{width:100%;border-collapse:collapse;min-width:680px;font-size:14px;line-height:1.8}th,td{padding:12px 13px;vertical-align:top;text-align:left;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}th{background:var(--soft);font-weight:600}tr:last-child td{border-bottom:0}tr>*:last-child{border-right:0}blockquote{margin:20px 0;padding:8px 20px;border-left:3px solid var(--accent);background:var(--soft)}
.diagram{margin:24px 0;border:1px solid var(--line);border-radius:8px;overflow:hidden}.diagram-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;border-bottom:1px solid var(--line);font-size:14px}.diagram-head figcaption{font-weight:600}.diagram-head button{font-size:13px;white-space:nowrap;flex-shrink:0}.diagram-preview{background:#fff;color:#202d3a;padding:20px;overflow:hidden}.diagram-preview svg{display:block;width:100%;height:auto;max-width:100%}.diagram-hint{font-size:12px;color:var(--muted);padding:8px 16px;border-top:1px solid var(--line);margin:0}.source{border-top:1px solid var(--line);padding:9px 16px;font-size:13px}.source summary,.lecture summary{cursor:pointer}.source pre{max-height:430px}.copy-source{font-size:12px;margin-top:10px}.lecture{padding:16px 20px;background:var(--soft);border:1px solid var(--line);border-radius:8px;margin:20px 0 30px}.lecture summary{color:var(--accent);font-weight:650;font-size:15px}.lecture p{font-size:15px;line-height:2.05;margin:15px 0}.lecture p:last-child{margin-bottom:0}.footer{overflow-wrap:anywhere;font-size:12px;color:var(--muted);margin-top:40px;border-top:1px solid var(--line);padding-top:18px}.back-top{display:inline-block;margin-top:14px}.progress{height:3px;position:fixed;top:0;left:0;background:var(--accent);width:0;z-index:5}
dialog{width:calc(100vw - 36px);height:calc(100vh - 36px);max-width:none;max-height:none;border:1px solid var(--line);border-radius:10px;padding:0;background:var(--paper);color:var(--ink);overflow:hidden}dialog::backdrop{background:#0c1825b8}.modal-shell{display:flex;flex-direction:column;height:100%}.modal-bar{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:9px;flex-wrap:wrap}.modal-bar h2{font-size:15px;line-height:1.6;margin:0;flex:1;min-width:180px}.modal-controls{display:flex;gap:6px;align-items:center}.modal-controls button{font-size:13px;padding:5px 9px}.zoom-label{font-variant-numeric:tabular-nums;font-size:13px;min-width:43px;text-align:center}.modal-canvas{overflow:auto;flex:1;min-height:0;background:#fff;color:#202d3a;padding:24px;cursor:grab;touch-action:pan-x pan-y}.modal-canvas.dragging{cursor:grabbing;user-select:none}.modal-canvas svg{display:block;max-width:none;flex-shrink:0}.modal-help{margin:0;padding:7px 16px;font-size:12px;color:var(--muted);border-top:1px solid var(--line)}.sr-only{position:absolute;width:1px;height:1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:1120px){.layout{grid-template-columns:205px minmax(0,1fr);padding:24px 20px;gap:20px}.main{padding:24px}.cover-inner{padding:32px 25px}.sidebar{padding-right:0}.toc a{font-size:12px}body{font-size:15px}}
@media(max-width:800px){html{scroll-padding-top:18px}.layout{display:block;padding:18px 12px 35px}.sidebar{position:static;max-height:none;margin-bottom:18px;padding:14px;border:1px solid var(--line);border-radius:8px;background:var(--paper)}.toc{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px}.diagrams-nav{margin-top:13px;padding-top:8px}.diagrams-nav nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.main{padding:21px 18px}.cover-inner{padding:28px 20px 24px}.cover h1{font-size:26px}.subtitle{font-size:14px}.tools{font-size:13px}.reading-note{font-size:12px}article h2{font-size:22px;margin-top:36px}article h3{font-size:18px}.diagram-head{padding:10px 12px;align-items:flex-start}.diagram-head figcaption{font-size:13px}.diagram-head button{font-size:12px;padding:6px 8px}.diagram-preview{padding:10px}.lecture{padding:13px 15px}.lecture p{font-size:14px}pre{padding:14px;font-size:12px}dialog{width:calc(100vw - 12px);height:calc(100vh - 12px)}.modal-bar{padding:10px;gap:5px}.modal-bar h2{flex-basis:100%;min-width:0}.modal-controls{flex-wrap:wrap}.modal-help{font-size:11px}.modal-canvas{padding:15px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{.cover,.sidebar,.notice,.progress,.diagram-head button,.diagram-hint,.source,.tools,.back-top,dialog{display:none!important}.layout{display:block;padding:0}.main{border:0;padding:0}body{background:white;color:black;font:11pt/1.65 "Microsoft YaHei",sans-serif}article h2{break-after:avoid;font-size:18pt}article h3{break-after:avoid;font-size:14pt}.table-wrap{overflow:visible}table{min-width:0;font-size:9pt}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:9pt}.lecture{break-inside:auto;background:#f4f7f6}.lecture summary{list-style:none}.diagram{break-inside:avoid}.diagram-preview svg{max-height:235mm}.footer{font-size:8pt}}
`;
const readerJs = `
const root=document.documentElement,dialog=document.getElementById('diagram-modal'),canvas=document.getElementById('modal-canvas');
let scale=1,naturalWidth=1,naturalHeight=1,activeSvg=null,returnFocus=null;
const announce=text=>{document.getElementById('reader-status').textContent=text};
const setTheme=theme=>{root.dataset.theme=theme;document.getElementById('theme').textContent=theme==='dark'?'浅色阅读':'深色阅读';try{localStorage.setItem('s01-reading-theme',theme)}catch{}};
try{setTheme(localStorage.getItem('s01-reading-theme')||'light')}catch{setTheme('light')}
document.getElementById('theme').addEventListener('click',()=>setTheme(root.dataset.theme==='dark'?'light':'dark'));
function applyZoom(value){scale=Math.max(.15,Math.min(2,value));activeSvg.style.width=(naturalWidth*scale)+'px';activeSvg.style.height=(naturalHeight*scale)+'px';document.getElementById('zoom-label').textContent=Math.round(scale*100)+'%'}
function fit(){applyZoom((canvas.clientWidth-48)/naturalWidth);canvas.scrollLeft=0;canvas.scrollTop=0}
document.querySelectorAll('[data-open-diagram]').forEach(button=>button.addEventListener('click',()=>{
 const figure=document.getElementById(button.dataset.openDiagram),original=figure.querySelector('svg');
 returnFocus=button;canvas.replaceChildren();activeSvg=original.cloneNode(true);
 // Namespace the root, definitions, references and scoped CSS for this dialog instance.
 let markup=activeSvg.outerHTML;
 const ids=[original.id,...original.querySelectorAll('[id]')].map(node=>typeof node==='string'?node:node.id).filter(Boolean).sort((a,b)=>b.length-a.length);
 ids.forEach(id=>{markup=markup.split('id="'+id+'"').join('id="zoom-'+id+'"').split('url(#'+id+')').join('url(#zoom-'+id+')').split('href="#'+id+'"').join('href="#zoom-'+id+'"')});
 markup=markup.split('#'+original.id).join('#zoom-'+original.id);
 canvas.innerHTML=markup;activeSvg=canvas.querySelector('svg');activeSvg.style.maxWidth='none';const box=original.viewBox.baseVal;
 naturalWidth=box.width;naturalHeight=box.height;
 document.getElementById('modal-title').textContent=figure.querySelector('figcaption').textContent;
 dialog.showModal();fit();
 document.getElementById('close-diagram').focus();
}));
document.getElementById('zoom-in').addEventListener('click',()=>applyZoom(scale+.15));
document.getElementById('zoom-out').addEventListener('click',()=>applyZoom(scale-.15));
document.getElementById('zoom-fit').addEventListener('click',fit);
document.getElementById('zoom-original').addEventListener('click',()=>applyZoom(1));
document.getElementById('close-diagram').addEventListener('click',()=>dialog.close());
dialog.addEventListener('close',()=>{canvas.replaceChildren();activeSvg=null;returnFocus?.focus()});
let drag=null;
canvas.addEventListener('pointerdown',event=>{if(event.pointerType!=='mouse'||event.button!==0)return;drag={x:event.clientX,y:event.clientY,left:canvas.scrollLeft,top:canvas.scrollTop};canvas.setPointerCapture(event.pointerId);canvas.classList.add('dragging')});
canvas.addEventListener('pointermove',event=>{if(!drag)return;canvas.scrollLeft=drag.left+drag.x-event.clientX;canvas.scrollTop=drag.top+drag.y-event.clientY});
const endDrag=()=>{drag=null;canvas.classList.remove('dragging')};canvas.addEventListener('pointerup',endDrag);canvas.addEventListener('pointercancel',endDrag);
document.getElementById('lectures').addEventListener('click',event=>{const items=[...document.querySelectorAll('.lecture')],open=items.some(item=>!item.open);items.forEach(item=>item.open=open);event.currentTarget.textContent=open?'收起全部讲稿':'展开全部讲稿'});
document.querySelectorAll('.copy-source').forEach(button=>button.addEventListener('click',async()=>{const text=button.closest('.source').querySelector('code').textContent;try{await navigator.clipboard.writeText(text);button.textContent='已复制';announce('Mermaid图源已复制')}catch{const selection=getSelection(),range=document.createRange();range.selectNodeContents(button.closest('.source').querySelector('code'));selection.removeAllRanges();selection.addRange(range);button.textContent='已选中，请按 Ctrl+C';announce('图源已选中，可以手动复制')}}));
const sections=[...document.querySelectorAll('article h2')],toc=[...document.querySelectorAll('.toc a')];
function updatePosition(){const max=root.scrollHeight-innerHeight;document.getElementById('progress').style.width=(max>0?scrollY/max*100:0)+'%';const current=sections.filter(section=>section.getBoundingClientRect().top<140).at(-1)||sections[0];toc.forEach(link=>{const active=link.hash==='#'+current.id;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current')})}
addEventListener('scroll',updatePosition,{passive:true});updatePosition();
let printStates=[];addEventListener('beforeprint',()=>{printStates=[...document.querySelectorAll('.lecture')].map(item=>[item,item.open]);printStates.forEach(([item])=>item.open=true)});addEventListener('afterprint',()=>printStates.forEach(([item,open])=>item.open=open));
document.getElementById('print').addEventListener('click',()=>print());
`;

async function build(browser, source) {
  const page = await browser.newPage();
  await page.route(/^https?:\/\//, route => route.abort());
  await page.setContent('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><body></body></html>');
  await page.addScriptTag({ path: runtimePath });
  await page.evaluate(() => mermaid.initialize({
    startOnLoad: false, securityLevel: 'strict', theme: 'base',
    fontFamily: 'Microsoft YaHei, sans-serif',
    themeVariables: { primaryColor: '#e9f3f1', primaryTextColor: '#202d3a', primaryBorderColor: '#5b938a', lineColor: '#536c7d', actorBkg: '#e9f3f1', actorTextColor: '#202d3a', actorBorder: '#5b938a', noteBkgColor: '#fff4e2', noteTextColor: '#614b2d', noteBorderColor: '#b99259' },
    flowchart: { htmlLabels: false, useMaxWidth: false, curve: 'linear', nodeSpacing: 32, rankSpacing: 45 },
    sequence: { useMaxWidth: false, wrap: true, actorMargin: 35, messageMargin: 32, noteMargin: 15 }, maxTextSize: 120000
  }));
  let converted = '', last = 0;
  const diagrams = [];
  for (const [index, match] of [...source.matchAll(/```mermaid\s*\n([\s\S]*?)```/g)].entries()) {
    const heading = source.slice(0, match.index).match(/^### 图 (\w+)：(.+)$/gm).at(-1);
    const [, id, name] = /^### 图 (\w+)：(.+)$/.exec(heading);
    const svg = await page.evaluate(async ({ text, index }) => {
      await mermaid.parse(text);
      return (await mermaid.render('s01_reading_' + index, text)).svg;
    }, { text: match[1], index });
    assert(!svg.includes('Syntax error'), id + ' rendered error');
    const title = '图 ' + id + ' · ' + name;
    const figure = `<figure class="diagram" id="figure-${id}" data-source-sha256="${sha(match[1])}"><div class="diagram-head"><figcaption>${esc(title)}</figcaption><button type="button" data-open-diagram="figure-${id}" aria-label="放大查看${esc(title)}">放大查看 ↗</button></div><div class="diagram-preview">${svg}</div><p class="diagram-hint">图内文字较多，建议放大查看；支持缩放、拖动与滚动。</p><details class="source"><summary>查看可编辑的 Mermaid 图源</summary><button class="copy-source" type="button">复制图源</button><pre tabindex="0"><code>${esc(match[1])}</code></pre></details></figure>`;
    converted += source.slice(last, match.index) + '\n\n' + figure + '\n\n';
    last = match.index + match[0].length;
    diagrams.push({ id, title });
  }
  converted += source.slice(last);
  await page.close();
  assert.equal(diagrams.length, 9);
  const python = 'import sys,markdown; sys.stdout.reconfigure(encoding="utf-8"); print(markdown.markdown(sys.stdin.read(),extensions=["tables","fenced_code","sane_lists"]))';
  let body = execFileSync(process.env.PYTHON_EXECUTABLE || 'python', ['-X', 'utf8', '-c', python], {
    input: converted, encoding: 'utf8', maxBuffer: 12 * 1024 * 1024, windowsHide: true
  });
  body = body.replace(/<h1>.*?<\/h1>/, '');
  const toc = [];
  let ordinal = 0;
  body = body.replace(/<h([23])>([\s\S]*?)<\/h\1>/g, (all, level, text) => {
    const id = 'section-' + (++ordinal);
    if (level === '2') toc.push(`<a href="#${id}">${text}</a>`);
    return `<h${level} id="${id}">${text}</h${level}>`;
  });
  body = body.replace(/<table>[\s\S]*?<\/table>/g, table => '<div class="table-wrap" tabindex="0" role="region" aria-label="可横向滚动的数据表">' + table + '</div>');
  body = body.replace(/<p><strong>逐字讲解稿（(\w+)）<\/strong><\/p>\s*((?:<p>[\s\S]*?<\/p>\s*)+)/g,
    (all, id, text) => `<details class="lecture" open id="lecture-${id}"><summary>逐字讲解稿（${id}）</summary>${text}</details>`);
  body = body.replace(/<pre>/g, '<pre tabindex="0">');
  const sourceHash = sha(fs.readFileSync(sourcePath));
  const diagramNav = diagrams.map(d => `<a href="#figure-${d.id}">${esc(d.title)}</a>`).join('');
  const output = `<!doctype html>
<html lang="zh-CN" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="source-sha256" content="${sourceHash}"><meta name="generator" content="build_s01_reading.cjs / Markdown-derived offline view"><meta name="generator-sha256" content="${sha(fs.readFileSync(__filename))}"><title>S01 补货 Agent 专项详细设计 · 阅读版</title><style>${css}</style></head>
<body id="top"><a class="skip" href="#main">跳到正文</a><div class="progress" id="progress" aria-hidden="true"></div>
<header class="cover"><div class="cover-inner"><p class="eyebrow">跨境电商智慧 AI 平台 / S01 专项设计</p><h1>S01 补货 Agent 专项详细设计</h1><p class="subtitle">第一阶段 · 设计评审稿　/　11 章 · 9 张图 · 9 份逐字讲解稿</p><div class="tools"><a class="button primary" href="#main">开始阅读 ↓</a><a class="button" href="${esc(path.basename(sourcePath))}">Markdown 正文</a><button type="button" id="theme">深色阅读</button><button type="button" id="lectures">收起全部讲稿</button><button type="button" id="print">打印</button></div><p class="reading-note">可离线打开；图表已内嵌。侧栏按章节和图号跳转，浏览器 Ctrl+F 可查找正文。Markdown 是唯一设计正文，本页由它生成。</p></div></header>
<div class="layout"><aside class="sidebar" aria-label="阅读导航"><p class="nav-title">章节目录</p><nav class="toc" aria-label="章节">${toc.join('')}</nav><div class="diagrams-nav"><p class="nav-title">图表速查</p><nav aria-label="9张图表">${diagramNav}</nav></div></aside><main class="main" id="main"><div class="notice"><p>这是负责人追加要求的 HTML 阅读版，设计结论与评审状态保持原样。原文中“不生成 HTML”等表述记录上一轮设计交付范围；本次仅追加阅读形式。</p></div><article>${body}</article><footer class="footer">派生来源：${esc(path.basename(sourcePath))}<br>源文件 SHA-256：<code>${sourceHash}</code><br>重新生成：<code>node docs/agents/scripts/build_s01_reading.cjs</code>。设计修改请先改 Markdown，再生成本页。<br><a class="back-top" href="#top">返回页首 ↑</a></footer></main></div>
<dialog id="diagram-modal" aria-labelledby="modal-title"><div class="modal-shell"><div class="modal-bar"><h2 id="modal-title">图表</h2><div class="modal-controls"><button id="zoom-out" type="button" aria-label="缩小图表">−</button><span class="zoom-label" id="zoom-label" aria-live="polite">100%</span><button id="zoom-in" type="button" aria-label="放大图表">＋</button><button id="zoom-fit" type="button">适宽</button><button id="zoom-original" type="button">100%</button><button id="close-diagram" type="button">关闭 ×</button></div></div><div class="modal-canvas" id="modal-canvas" tabindex="0" aria-label="图表，可拖动或滚动查看"></div><p class="modal-help">拖动图表或滚动查看；适宽可看全貌，100% 可读原尺寸文字；按 Esc 关闭。</p></div></dialog><div class="sr-only" id="reader-status" role="status" aria-live="polite"></div>
<script>${readerJs}</script></body></html>`;
  fs.writeFileSync(outputPath, output, 'utf8');
  return { diagrams: diagrams.length, chapters: toc.length, sourceHash, htmlSha256: sha(Buffer.from(output)) };
}

async function check(browser, source) {
  const html = fs.readFileSync(outputPath, 'utf8');
  assert(html.includes('content="' + sha(fs.readFileSync(sourcePath)) + '"'), 'HTML is stale');
  assert(html.includes('name="generator-sha256" content="' + sha(fs.readFileSync(__filename)) + '"'), 'HTML reader build is stale');
  const page = await browser.newPage();
  const errors = [], remote = [], layouts = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.route(/^https?:\/\//, route => { remote.push(route.request().url()); route.abort(); });
  await page.goto(pathToFileURL(outputPath).href);
  assert.equal(await page.locator('article h2').count(), 11);
  assert.equal(await page.locator('.diagram-preview svg').count(), 9);
  assert.equal(await page.locator('.lecture').count(), 9);
  const blocks = [...source.matchAll(/```mermaid\s*\n([\s\S]*?)```/g)].map(m => m[1]);
  const sources = await page.locator('.source code').allTextContents();
  assert.deepEqual(sources, blocks, 'Mermaid source drift');
  const pseudo = [...source.matchAll(/```python\s*\n([\s\S]*?)```/g)].map(m => m[1].trim());
  assert.deepEqual((await page.locator('code.language-python').allTextContents()).map(x => x.trim()), pseudo);
  const dimensions = await page.locator('.diagram-preview svg').evaluateAll(nodes => nodes.map(svg => {
    const box = svg.viewBox.baseVal;
    return { width: box.width, height: box.height, texts: svg.querySelectorAll('text').length, errors: svg.querySelectorAll('.error-icon,.error-text').length };
  }));
  assert(dimensions.every(x => x.width > 0 && x.height > 0 && x.texts > 0 && !x.errors));
  for (const width of [1440, 1920, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const theme of ['light', 'dark']) {
      await page.evaluate(t => document.documentElement.dataset.theme = t, theme);
      const data = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
      assert(data.scrollWidth <= data.width + 1, 'Page overflow at ' + width + '/' + theme);
      layouts.push({ width, theme, result: 'PASS' });
    }
  }
  await page.locator('#theme').click();
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), 'light');
  await page.locator('#theme').click();
  await page.reload();
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), 'dark');
  assert.equal(await page.locator('#theme').textContent(), '浅色阅读');
  await page.setViewportSize({ width: 1440, height: 1000 });
  for (let i = 0; i < 9; i++) {
    await page.locator('[data-open-diagram]').nth(i).click();
    assert(await page.locator('#diagram-modal').evaluate(d => d.open));
    await page.locator('#zoom-original').click();
    assert.equal(await page.locator('#zoom-label').textContent(), '100%');
    if (i === 0) {
      await page.mouse.move(900, 450); await page.mouse.down();
      await page.mouse.move(400, 450, { steps: 5 }); await page.mouse.up();
      assert(await page.locator('#modal-canvas').evaluate(e => e.scrollLeft > 100), 'Diagram drag failed');
    }
    await page.locator('#zoom-in').click();
    assert.equal(await page.locator('#zoom-label').textContent(), '115%');
    await page.locator('#zoom-fit').click();
    assert(await page.locator('#modal-canvas').evaluate(e => e.scrollWidth <= e.clientWidth + 1));
    await page.keyboard.press('Escape');
    assert(!(await page.locator('#diagram-modal').evaluate(d => d.open)));
    assert.equal(await page.evaluate(() => document.activeElement.dataset.openDiagram), 'figure-' + ['A01','I01','I02','I03','T01','T02','T03','T04','T05'][i]);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('[data-open-diagram]').first().click();
  assert(await page.locator('#diagram-modal').evaluate(d => d.open && d.getBoundingClientRect().right <= innerWidth));
  await page.locator('#close-diagram').click();
  await page.locator('#lectures').click();
  assert.equal(await page.locator('.lecture[open]').count(), 0);
  await page.locator('#lectures').click();
  assert.equal(await page.locator('.lecture[open]').count(), 9);
  await page.locator('.source summary').first().click();
  assert(await page.locator('.source').first().evaluate(e => e.open));
  const hrefs = await page.locator('a[href^="#"]').evaluateAll(nodes => nodes.map(a => a.getAttribute('href').slice(1)));
  assert(await page.evaluate(ids => ids.every(id => document.getElementById(id)), hrefs));
  assert.equal(errors.length, 0, errors.join('\n'));
  assert.equal(remote.length, 0);
  await page.close();
  return { result: 'PASS', sourceSha256: sha(fs.readFileSync(sourcePath)), htmlSha256: sha(Buffer.from(html)), diagrams: 9, lectures: 9, pseudocodeBlocks: pseudo.length, chapterLinks: 11, layouts, diagramDialogs: '9/9 zoom/fit/Esc/focus PASS', themeToggleAndPersistence: 'PASS', diagramDragAndMobileDialog: 'PASS', lectureToggle: 'PASS', sourceToggle: 'PASS', internalLinks: 'PASS', browserErrors: errors, remoteRequests: remote };
}

(async () => {
  const before = fs.readFileSync(sourcePath);
  const source = before.toString('utf8').replace(/\r\n/g, '\n');
  const browser = await chromium.launch({ headless: true, executablePath: process.env.BROWSER_EXECUTABLE || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe' });
  try {
    if (!process.argv.includes('--check')) console.log(JSON.stringify({ build: await build(browser, source) }));
    console.log(JSON.stringify(await check(browser, source)));
    assert(before.equals(fs.readFileSync(sourcePath)), 'Authoritative Markdown modified');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
