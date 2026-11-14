/* 真实浏览器验收：CDP 驱动 Edge，执行点击/输入/截图，不依赖 DOM 模拟 */
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9333;
const URL = 'http://127.0.0.1:8765/prototypes/s01-workbench-v3/index.html';
const OUT = path.join(__dirname, 'screenshots');

const results = [];
function ok(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra === undefined ? '' : String(extra) }); }

const get = (u) => new Promise((res, rej) => {
  http.get(u, r => { let d = ''; r.on('data', c => d += c); r.on('end', () => res(d)); }).on('error', rej);
});
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const profile = path.join(os.tmpdir(), 'ux3-cdp-' + Date.now());
  const child = spawn(EDGE, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
    '--no-default-browser-check', '--disable-extensions',
    '--remote-debugging-port=' + PORT, '--user-data-dir=' + profile,
    '--window-size=1440,900', 'about:blank'
  ], { stdio: 'ignore' });

  let list;
  for (let i = 0; i < 60; i++) {
    try { list = JSON.parse(await get(`http://127.0.0.1:${PORT}/json/list`)); if (list.length) break; } catch (e) { }
    await sleep(200);
  }
  const page = list.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });

  let id = 0; const pend = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pend.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });

  const js = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result && r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 300));
    return r.result && r.result.result ? r.result.result.value : undefined;
  };

  const metrics = (w, h) => send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  const goto = async (hash) => {
    await send('Page.navigate', { url: URL + hash });
    for (let i = 0; i < 50; i++) { await sleep(80); if (await js('document.readyState') === 'complete') break; }
    await sleep(260);
  };
  // 真实鼠标点击：取元素中心坐标后派发按下/抬起
  const click = async (sel) => {
    const box = await js(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};})()`);
    if (!box) throw new Error('未找到元素: ' + sel);
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: 1 });
    await sleep(140);
  };
  const clickText = async (sel, text) => {
    const box = await js(`(()=>{const els=[...document.querySelectorAll(${JSON.stringify(sel)})];const e=els.find(x=>x.textContent.includes(${JSON.stringify(text)}));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};})()`);
    if (!box) throw new Error('未找到含文本元素: ' + sel + ' / ' + text);
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: 1 });
    await sleep(140);
  };
  const typeInto = async (sel, text) => {
    await click(sel);
    await js(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});e.value='';e.focus();return 1})()`);
    for (const ch of text) {
      await send('Input.dispatchKeyEvent', { type: 'char', text: ch });
    }
    await js(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});e.dispatchEvent(new Event('input',{bubbles:true}));return 1})()`);
    await sleep(120);
  };
  const hasText = (t) => js(`document.body.innerText.includes(${JSON.stringify(t)})`);
  const mainHas = (t) => js(`document.getElementById('main').innerText.includes(${JSON.stringify(t)})`);
  const count = (sel) => js(`document.querySelectorAll(${JSON.stringify(sel)}).length`);
  const url = () => js('location.hash');
  const shot = async (name) => {
    await js(`(()=>{const t=document.getElementById('toast');if(t)t.hidden=true;return 1})()`);
    await js('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(1))))');
    await sleep(80);
    const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false, fromSurface: true });
    fs.writeFileSync(path.join(OUT, name + '.png'), Buffer.from(r.result.data, 'base64'));
  };

  await send('Page.enable');
  await send('Runtime.enable');

  /* ---------------- 1440 ---------------- */
  await metrics(1440, 940);
  await goto('#/workbench');

  ok('工作台标题', await js(`document.querySelector('h1').textContent.trim()==='采购运营工作台'`));
  ok('四个待办指标', await count('.kpi') === 4);
  ok('状态分布条有分段', await count('.distbar i') >= 5, await count('.distbar i'));
  ok('分布条合计等于对象总数', await js(`[...document.querySelectorAll('.distbar')[0].children].length>0 && [...document.querySelectorAll('.legend b')].reduce((a,b)=>a+Number(b.textContent),0)===11`),
     await js(`[...document.querySelectorAll('.legend b')].reduce((a,b)=>a+Number(b.textContent),0)`)+'/11');
  ok('待处理队列有行', await count('.qrow') >= 5, await count('.qrow'));
  ok('队列含库存覆盖条', await count('.qrow .cov') >= 3, await count('.qrow .cov'));
  ok('无库存数据行不画空条', await count('.qrow .cov-num .muted') >= 1, await count('.qrow .cov-num .muted'));
  ok('首屏无演示横幅', !(await hasText('未连接 ERP')) && !(await hasText('UX v3')));
  ok('首屏无长说明段落', await js(`document.querySelectorAll('main p').length<=2`), await js(`document.querySelectorAll('main p').length`));
  await shot('after/01-工作台-1440');

  // 待确认 → 列表（带筛选跳转）
  await clickText('.kpi', '待确认数量');
  ok('点击待办跳到补货建议', (await url()).includes('suggestions'), await url());
  ok('状态筛选已应用', await js(`[...document.querySelectorAll('.seg button')].some(b=>b.getAttribute('aria-pressed')==='true'&&b.dataset.val==='待确认')`));
  ok('列表行数=待确认数 4', await count('#rows tr') === 4, await count('#rows tr'));

  /* ---------------- 列表筛选 ---------------- */
  await clickText('.seg button', '全部');
  ok('清空状态后 11 行', await count('#rows tr') === 11, await count('#rows tr'));
  await typeInto('#f-q', '收纳');
  ok('搜索收敛到 3 行', await count('#rows tr') === 3, await count('#rows tr'));
  ok('搜索显示行数文案', (await js(`document.getElementById('res-count').textContent`)).includes('3'), await js(`document.getElementById('res-count').textContent`));
  await shot('after/02-补货建议-1440');

  /* ---------------- 详情 ---------------- */
  await clickText('#rows tr a.prod', '旅行收纳包');
  ok('进入 SKU 详情路由', (await url()).includes('/sku/CB-1001'), await url());
  ok('详情含结存预测图', await count('.chart-wrap svg') === 1);
  ok('详情含销量柱状图', await count('.two svg') >= 1);
  ok('详情含建议口径', await hasText('建议口径'));
  ok('右侧请购栏存在', await count('.rail #qty') === 1);
  ok('目标库存与建议数量自洽（75/20）', await hasText('75') && await hasText('缺口 20'), '');
  await shot('after/03-SKU详情-1440');

  // Tab 路由
  await clickText('.tabs button', '依据与限制');
  ok('Tab 写入 URL', (await url()).includes('/quality'), await url());
  ok('依据页有检查项', await hasText('接口分时读取'));
  await clickText('.tabs button', '采购条件');
  ok('Tab 返回采购条件（默认路由不带后缀）', (await url()) === '#/sku/CB-1001', await url());
  ok('采购条件 Tab 处于选中态', await js(`[...document.querySelectorAll('.tabs button')].some(b=>b.getAttribute('aria-selected')==='true'&&b.textContent.includes('采购条件'))`));
  ok('采购条件含 MOQ', await hasText('最小起订量'));

  /* ---------------- 数量与提交 ---------------- */
  await typeInto('#qty', '25');
  ok('25 件提示整箱约束', await hasText('整箱 10 的整数倍'));
  ok('25 件提交禁用', await js(`document.getElementById('submit').disabled===true`));
  await typeInto('#qty', '30');
  ok('30 件出现原因输入', await js(`document.getElementById('reason-wrap').hidden===false`));
  ok('未填原因仍禁用', await js(`document.getElementById('submit').disabled===true`));
  await typeInto('#reason', '已有在途 36 件，本次只补一半');
  await click('#ack');
  ok('填原因+勾选后可提交', await js(`document.getElementById('submit').disabled===false`));
  await click('#submit');
  ok('提交后右栏切换为请购单', await js(`document.querySelector('.rail h2').textContent==='请购单'`), await js(`document.querySelector('.rail h2').textContent`));
  ok('提交后显示待 ERP 审批', await mainHas('待 ERP 审批'));
  ok('提交后右栏显示单据号', await mainHas('RQ-2026-0014'));
  ok('提交后表单不再出现数量输入', await count('.rail #qty') === 0);
  ok('提交后工作台计数同步', await js(`document.querySelector('nav a[href="#/suggestions"] .nav-count')!==null`));
  await shot('after/04-SKU详情-已提交-1440');

  /* ---------------- 返回保留筛选 ---------------- */
  await click('.back');
  ok('返回到列表', (await url()).includes('suggestions'));
  ok('返回后搜索词保留', await js(`document.getElementById('f-q').value==='收纳'`), await js(`document.getElementById('f-q').value`));
  ok('返回后行数仍为筛选结果', await count('#rows tr') === 3, await count('#rows tr'));

  /* ---------------- 批次切换 ---------------- */
  await clickText('.btn', '本次检查');
  ok('批次弹层打开', await js(`document.getElementById('dialog').open===true`));
  await clickText('#dialog button', '切换');
  await sleep(150);
  ok('批次已切换', (await hasText('11-13 07:58')) || (await js(`document.getElementById('foot-right').textContent`)).includes('11-13'), await js(`document.getElementById('foot-right').textContent`));
  await clickText('.btn', '清空');
  await typeInto('#f-q', 'CB-1001');
  ok('旧批次数值生效（可用 43）', await hasText('43 / 75'), await js(`document.querySelector('#rows tr .stockcell span:last-child')?.textContent`));
  ok('各批次建议数量自洽（目标-可用→取整）', (await js('window.__ux3check()')).length === 0, JSON.stringify(await js('window.__ux3check()')));
  await clickText('.btn', '本次检查');
  await clickText('#dialog button', '切换');
  await sleep(150);

  /* ---------------- 请购管理 ---------------- */
  await clickText('nav a', '请购管理');
  ok('进入请购管理', (await url()).includes('requisitions'));
  ok('请购表含新提交单据（4 行）', await count('#main tbody tr') === 4, await count('#main tbody tr'));
  ok('新单据已进入台账', await mainHas('RQ-2026-0014'));
  ok('请购页状态分布图存在', await count('#main .distbar i') >= 2, await count('#main .distbar i'));
  ok('双状态列存在', await hasText('平台状态') && await hasText('ERP 状态'));
  ok('无大段蓝色说明框', await count('.alert-row') === 1, await count('.alert-row'));
  await shot('after/05-请购管理-1440');

  await clickText('tbody tr a.btn', '核对');
  ok('进入请购单详情', (await url()).includes('RQ-2026-0012'), await url());
  ok('步骤条 4 段', await count('.step') === 4);
  ok('UNKNOWN 仅一块警示', await count('.alert-row') === 1, await count('.alert-row'));
  await shot('after/06-请购单-待核对-1440');

  /* ---------------- 1024 ---------------- */
  await metrics(1024, 900);
  await goto('#/workbench');
  await sleep(200);
  ok('1024 无横向溢出', await js('document.documentElement.scrollWidth<=window.innerWidth+1'), await js('document.documentElement.scrollWidth+" vs "+window.innerWidth'));
  await shot('after/07-工作台-1024');
  await goto('#/sku/BT-2003');
  await sleep(200);
  ok('1024 详情操作栏在内容下', await js(`getComputedStyle(document.querySelector('.detail')).gridTemplateColumns.split(' ').length===1`), await js(`getComputedStyle(document.querySelector('.detail')).gridTemplateColumns`));
  ok('1024 详情无横向溢出', await js('document.documentElement.scrollWidth<=window.innerWidth+1'));
  await shot('after/08-SKU详情-1024');

  /* ---------------- 820 ---------------- */
  await metrics(820, 900);
  await goto('#/suggestions');
  ok('820 导航转为顶部', await js(`getComputedStyle(document.querySelector('.sidebar')).position==='static'`));
  ok('820 列表无页面级横向溢出', await js('document.documentElement.scrollWidth<=window.innerWidth+1'), await js('document.documentElement.scrollWidth+" vs "+window.innerWidth'));
  ok('820 操作列未被裁切', await js(`(()=>{const b=document.querySelector('#rows tr a.btn');if(!b)return false;const r=b.getBoundingClientRect();return r.right<=window.innerWidth+1&&r.width>20})()`),
     await js(`(()=>{const b=document.querySelector('#rows tr a.btn');return b?Math.round(b.getBoundingClientRect().right)+'/'+window.innerWidth:'no-btn'})()`));
  await shot('after/09-补货建议-820');

  await goto('#/sku/LT-3021');
  ok('820 进入数据不足 SKU', (await js(`document.querySelector('main h1').textContent`)).includes('折叠桌面灯'), await js(`document.querySelector('main h1').textContent`));
  ok('820 数据不足不显示数量', await mainHas('未形成'));
  ok('820 草案标注未生效', await mainHas('未生效') || await mainHas('政策草案未生效'));
  await shot('after/10-SKU详情-数据不足-820');

  await goto('#/requisitions');
  ok('820 台账无横向溢出', await js('document.documentElement.scrollWidth<=window.innerWidth+1'), await js('document.documentElement.scrollWidth+" vs "+window.innerWidth'));
  await shot('after/11-请购管理-820');

  /* ---------------- 无控制台错误 ---------------- */
  const errs = await js('window.__errs ? window.__errs.length : 0');
  ok('无脚本异常', errs === 0, errs);

  fs.writeFileSync(path.join(__dirname, '_e2e-result.json'), JSON.stringify(results, null, 1));
  const pass = results.filter(r => r.pass).length;
  console.log(results.map(r => `${r.pass ? 'PASS' : 'FAIL'}  ${r.name}${r.pass ? '' : '   [' + r.extra + ']'}`).join('\n'));
  console.log(`\n${pass}/${results.length} 通过`);

  ws.close();
  child.kill();
  setTimeout(() => { try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) { } process.exit(pass === results.length ? 0 : 1); }, 500);
})().catch(e => { console.error('E2E ERROR:', e.message); process.exit(2); });
