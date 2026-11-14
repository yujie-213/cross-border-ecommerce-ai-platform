/* V3.2 真实浏览器验收：CDP 驱动 Edge，真实鼠标/键盘事件 + 三档宽度截图 */
const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9333;
const BASE = 'http://127.0.0.1:8766/prototypes/s01-workbench-v3/index.html';
const OUT = path.join(__dirname, 'screenshots', 'after');

const results = [];
function ok(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra === undefined ? '' : String(extra) }); }
const get = (u) => new Promise((res, rej) => { http.get(u, r => { let d = ''; r.on('data', c => d += c); r.on('end', () => res(d)); }).on('error', rej); });
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const profile = path.join(os.tmpdir(), 'ux3v32-' + Date.now());
  const child = spawn(EDGE, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
    '--no-default-browser-check', '--disable-extensions', '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + profile, '--window-size=1440,940', 'about:blank'], { stdio: 'ignore' });

  let list;
  for (let i = 0; i < 60; i++) { try { list = JSON.parse(await get(`http://127.0.0.1:${PORT}/json/list`)); if (list.length) break; } catch (e) { } await sleep(200); }
  const page = list.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });

  let id = 0; const pend = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pend.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  const js = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result && r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 240));
    return r.result && r.result.result ? r.result.result.value : undefined;
  };
  const metrics = (w, h) => send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  let seq = 0;
  const goto = async (hash, v) => {
    await send('Page.navigate', { url: `${BASE}?v=${v || 'c'}&t=${++seq}${hash}` });
    for (let i = 0; i < 60; i++) { await sleep(80); if (await js('document.readyState') === 'complete') break; }
    await sleep(320);
  };
  const box = async (sel, text) => await js(`(()=>{const els=[...document.querySelectorAll(${JSON.stringify(sel)})];
    const e=${text ? `els.find(x=>x.textContent.includes(${JSON.stringify(text)}))` : 'els[0]'};if(!e)return null;
    e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()`);
  const click = async (sel, text) => {
    const b = await box(sel, text); if (!b) throw new Error('未找到 ' + sel + (text ? ' / ' + text : ''));
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: b.x, y: b.y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: b.x, y: b.y, button: 'left', clickCount: 1 });
    await sleep(160);
  };
  const typeInto = async (sel, text) => {
    await click(sel);
    await js(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});e.value='';e.focus();return 1})()`);
    for (const ch of text) await send('Input.dispatchKeyEvent', { type: 'char', text: ch });
    await js(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});e.dispatchEvent(new Event('input',{bubbles:true}));return 1})()`);
    await sleep(120);
  };
  const nav = async (hash) => { await js(`location.hash=${JSON.stringify(hash)}`); await sleep(420); };
  const waitFor = async (expr, ms = 4000) => {
    for (let i = 0; i < ms / 100; i++) { if (await js(expr)) return true; await sleep(100); }
    return false;
  };
  const mainHas = (t) => js(`document.getElementById('main').innerText.includes(${JSON.stringify(t)})`);
  const count = (sel) => js(`document.querySelectorAll(${JSON.stringify(sel)}).length`);
  const url = () => js('location.hash');
  const shot = async (name) => {
    await js(`(()=>{const t=document.getElementById('toast');if(t)t.hidden=true;return 1})()`);
    await js('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(()=>r(1))))');
    await sleep(70);
    const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false, fromSurface: true });
    fs.writeFileSync(path.join(OUT, name + '.png'), Buffer.from(r.result.data, 'base64'));
  };

  await send('Page.enable'); await send('Runtime.enable');

  /* ================= 1440：工作台 ================= */
  await metrics(1440, 940);
  await goto('#/workbench');

  ok('工作台标题', await js(`document.querySelector('h1').textContent.trim()==='采购运营工作台'`));
  ok('四个待办指标', await count('.kpi') === 4);
  ok('环形图已渲染（1 底环 + 4 组）', await count('.donut svg circle') === 5, await count('.donut svg circle'));
  ok('环形分段数与图例一致', await js(`document.querySelectorAll('.donut svg circle').length-1===document.querySelectorAll('.dlegend span').length && document.querySelectorAll('.dlegend span').length===4`));
  ok('环形图合计=对象总数', await js(`[...document.querySelectorAll('.dlegend b')].reduce((a,b)=>a+Number(b.textContent),0)===12`),
    await js(`[...document.querySelectorAll('.dlegend b')].reduce((a,b)=>a+Number(b.textContent),0)`));
  ok('环形图支持悬停数值', await count('.donut svg title') >= 4, await count('.donut svg title'));
  ok('页面已无堆叠条', await count('.distbar') === 0, await count('.distbar'));
  ok('队列无横向条形', await count('.qrow .cov') === 0, await count('.qrow .cov'));
  ok('待处理队列有行', await count('.qrow') >= 5, await count('.qrow'));
  ok('待核对对象排在最前（排序缺陷）', await js(`document.querySelector('.qrow .prod').textContent.includes('行李箱束带')`),
    await js(`document.querySelector('.qrow .prod')&&document.querySelector('.qrow .prod').textContent`));
  ok('零库存显示 0 天而非未知', await js(`[...document.querySelectorAll('.qrow')].some(r=>r.textContent.includes('CB-1040')&&r.textContent.includes('0 天'))`));
  ok('覆盖最短卡展示 0 天', await js(`[...document.querySelectorAll('.rank-row')].some(r=>r.textContent.includes('CB-1040')&&r.textContent.includes('0 天'))`));
  await shot('01-工作台-1440');

  await click('.kpi', '待确认数量');
  ok('待办跳转到列表', (await url()).includes('suggestions'), await url());
  ok('列表行数=待确认 5', await count('#rows tr') === 5, await count('#rows tr'));

  /* ================= 列表 ================= */
  await click('.seg button', '全部');
  ok('清空后 12 行', await count('#rows tr') === 12, await count('#rows tr'));
  ok('列表无条形图', await count('#rows .cov') === 0, await count('#rows .cov'));
  ok('列表显示覆盖天数', await mainHas('覆盖 4.9 天'));
  ok('零库存行显示 0 天', await js(`[...document.querySelectorAll('#rows tr')].some(r=>r.textContent.includes('CB-1040')&&r.textContent.includes('0 天'))`));
  ok('风险标签存在', await mainHas('低于交期'));
  await typeInto('#f-q', '收纳');
  ok('搜索收敛到 3 行', await count('#rows tr') === 3, await count('#rows tr'));
  await shot('02-补货建议-1440');
  await click('.btn', '清空');

  /* ================= SKU 详情：AI 未生成 ================= */
  await goto('#/sku/CB-1001');
  ok('详情进入', (await js(`document.querySelector('main h1').textContent`)).includes('旅行收纳包'));
  ok('AI 分区存在', await count('.ai-panel') === 1);
  ok('AI 位于结论条与图表之间', await js(`(()=>{const ai=document.querySelector('.ai-panel').getBoundingClientRect().top;
      const ch=document.querySelector('.chart-wrap').getBoundingClientRect().top;
      const v=document.querySelector('.verdict').getBoundingClientRect().top;return v<ai&&ai<ch})()`),
    await js(`(()=>{const ai=document.querySelector('.ai-panel').getBoundingClientRect().top;
      const ch=document.querySelector('.chart-wrap').getBoundingClientRect().top;return Math.round(ai)+'/'+Math.round(ch)})()`));
  ok('AI 未生成显示入口', await mainHas('生成 AI 解读'));
  ok('AI 状态为未生成', await js(`document.querySelector('.ai-head .chip').textContent.trim()==='未生成'`));
  ok('AI 入口在首屏内', await js(`document.querySelector('.ai-panel').getBoundingClientRect().bottom < innerHeight`),
    await js(`Math.round(document.querySelector('.ai-panel').getBoundingClientRect().bottom)+'/'+innerHeight`));
  ok('底部操作条存在', await count('.actionbar') === 1);
  ok('首次短缺与曲线一致（11-15）', await js(`document.querySelector('.verdict').innerText.includes('11-15')`),
    await js(`document.querySelector('.verdict').innerText.replace(/\\s+/g,' ')`));
  await shot('03-SKU详情-AI未生成-1440');

  /* AI 生成流程 */
  await click('.ai-panel .btn', '生成 AI 解读');
  ok('生成中状态出现', await waitFor(`document.querySelector('.ai-head .chip').textContent.includes('生成中')`, 1500));
  ok('生成完成后出现四段结构', await waitFor(`(()=>{const t=document.querySelector('.ai-panel').innerText;return t.includes('关键事实')&&t.includes('风险与不确定')&&t.includes('建议人工核实')})()`, 5000));
  ok('AI 元信息含 Token 与边界说明', await mainHas('Token') && await mainHas('仅解读，不改动规则建议数量'));
  ok('AI 未改写建议数量', await js(`document.querySelector('.verdict').innerText.includes('20')`));
  await shot('04-SKU详情-AI已生成-1440');

  /* Tab 路由 */
  await click('.tabs button', '依据与限制');
  ok('Tab 写入 URL', (await url()).includes('/quality'), await url());
  await click('.tabs button', '采购条件');
  ok('Tab 返回默认路由', (await url()) === '#/sku/CB-1001', await url());

  /* ================= 布局对比 ================= */
  await goto('#/sku/BT-2003', 'a');
  ok('方案A：右栏操作卡、无底部条', await count('.actionbar') === 0 && await count('.rail .btn') > 0);
  ok('方案A：AI 在图表之后', await js(`document.querySelector('.ai-panel').getBoundingClientRect().top > document.querySelector('.chart-wrap').getBoundingClientRect().top`));
  await shot('05-布局A-AI全宽分区-1440');

  await goto('#/sku/BT-2003', 'b');
  ok('方案B：右栏 AI 单列', await js(`(()=>{const p=document.querySelector('.rail .ai-panel');return !!p&&getComputedStyle(p.querySelector('.ai-grid')).gridTemplateColumns.split(' ').length===1})()`),
    await js(`(()=>{const p=document.querySelector('.rail .ai-panel');return p?getComputedStyle(p.querySelector('.ai-grid')).gridTemplateColumns:'none'})()`));
  await shot('06-布局B-AI右栏-1440');

  await goto('#/sku/BT-2003', 'c');
  ok('方案C：AI 前置 + 底部操作条', await js(`(()=>{const ai=document.querySelector('.ai-panel').getBoundingClientRect().top;
      const ch=document.querySelector('.chart-wrap').getBoundingClientRect().top;return ai<ch&&!!document.querySelector('.actionbar')})()`));
  await shot('07-布局C-AI前置-1440');

  /* ================= 数量校验与提交 ================= */
  await goto('#/sku/CB-1001', 'c');
  await typeInto('#qty', '25');
  ok('25 件提示整箱约束', await mainHas('整箱 10 的整数倍'));
  ok('25 件禁用提交', await js(`document.getElementById('submit').disabled===true`));
  await typeInto('#qty', '30');
  ok('改量出现原因输入', await js(`document.getElementById('reason-wrap').hidden===false`));
  ok('未填原因禁用', await js(`document.getElementById('submit').disabled===true`));
  await typeInto('#reason', '已有在途，本次只补一半');
  await click('#ack');
  ok('校验通过后可提交', await js(`document.getElementById('submit').disabled===false`));
  await click('#submit');
  ok('提交后操作条转为请购状态', await mainHas('待 ERP 审批') && await js(`document.querySelector('.actionbar').innerText.includes('RQ-2026-0013')`),
    await js(`document.querySelector('.actionbar').innerText.replace(/\\s+/g,' ')`));

  /* ================= ERP 参考建议提交链路 ================= */
  await nav('#/sku/LT-3012');
  ok('ERP 参考可进入待确认', await js(`document.querySelector('.sku-meta').innerText.includes('待确认')`));
  ok('ERP 参考标注来源', await js(`document.querySelector('.actionbar').innerText.includes('ERP 参考')`));
  ok('ERP 参考带 AI 解读', await mainHas('关键事实') && await mainHas('ERP 建议记录'));
  await click('.tabs button', '依据与限制');
  ok('来源限制可见（ERP 计算依据未核实）', await mainHas('ERP 计算依据未核实'));
  await shot('08-SKU详情-ERP参考-1440');
  await click('.tabs button', '采购条件');
  ok('采购条件含最小起订量 5', await mainHas('最小起订量'));
  await click('#ack');
  ok('ERP 参考核对后可提交', await js(`document.getElementById('submit').disabled===false`));
  await click('#submit');
  ok('ERP 参考提交成功并生成新单', await mainHas('待 ERP 审批') && await mainHas('RQ-2026-0014'),
    await js(`document.querySelector('.actionbar')?document.querySelector('.actionbar').innerText.replace(/\\s+/g,' '):''`));

  /* ================= 请购台账 ================= */
  await nav('#/requisitions');
  ok('台账 5 行', await count('#main tbody tr') === 5, await count('#main tbody tr'));
  ok('台账单条警示', await count('.alert-row') === 1, await count('.alert-row'));
  ok('台账无装饰性分布图', await count('#main .distbar') === 0 && await count('#main .donut') === 0);
  ok('双状态列存在', await mainHas('平台状态') && await mainHas('ERP 状态'));
  await shot('09-请购管理-1440');

  await click('#main tbody tr a.btn', '核对');
  ok('进入待核对单据', (await url()).includes('RQ-2026-0012'), await url());
  ok('待核对仅一处警示', await count('.alert-row') === 1, await count('.alert-row'));
  ok('第二步为待核对状态', await js(`document.querySelectorAll('.step')[1].classList.contains('wait')`),
    await js(`document.querySelectorAll('.step')[1].className`));
  await shot('10-请购单-待核对-1440');

  /* ================= 数据自洽 ================= */
  ok('建议数量与目标库存自洽', (await js('window.__ux3check()')).length === 0, JSON.stringify(await js('window.__ux3check()')));
  ok('首次短缺与结存曲线自洽', (await js('window.__ux3check2()')).length === 0, JSON.stringify(await js('window.__ux3check2()')));

  /* ================= 1024 ================= */
  await metrics(1024, 900);
  await goto('#/workbench', 'c');
  ok('1024 工作台无横向溢出', await js('document.documentElement.scrollWidth<=innerWidth+1'), await js('document.documentElement.scrollWidth+" vs "+innerWidth'));
  await shot('11-工作台-1024');

  await goto('#/sku/BT-2003', 'c');
  ok('1024 AI 两列', await js(`getComputedStyle(document.querySelector('.ai-grid')).gridTemplateColumns.split(' ').length===2`),
    await js(`getComputedStyle(document.querySelector('.ai-grid')).gridTemplateColumns`));
  ok('1024 操作条主按钮在首行', await js(`(()=>{const b=document.getElementById('submit').getBoundingClientRect();
      const bar=document.querySelector('.actionbar').getBoundingClientRect();return b.top<bar.top+bar.height*0.6})()`));
  ok('1024 详情无溢出', await js('document.documentElement.scrollWidth<=innerWidth+1'));
  await shot('12-SKU详情-1024');

  /* ================= 820 ================= */
  await metrics(820, 900);
  await goto('#/suggestions', 'c');
  ok('820 导航转顶部', await js(`getComputedStyle(document.querySelector('.sidebar')).position==='static'`));
  ok('820 列表操作列可见', await js(`(()=>{const b=document.querySelector('#rows tr a.btn');if(!b)return false;const r=b.getBoundingClientRect();return r.right<=innerWidth+1&&r.width>20})()`),
    await js(`(()=>{const b=document.querySelector('#rows tr a.btn');return b?Math.round(b.getBoundingClientRect().right)+'/'+innerWidth:'none'})()`));
  await shot('13-补货建议-820');

  await goto('#/sku/BT-2003', 'c');
  ok('820 AI 单列', await js(`getComputedStyle(document.querySelector('.ai-grid')).gridTemplateColumns.split(' ').length===1`),
    await js(`getComputedStyle(document.querySelector('.ai-grid')).gridTemplateColumns`));
  ok('820 提交按钮完整可见', await js(`(()=>{const b=document.getElementById('submit').getBoundingClientRect();return b.right<=innerWidth+1&&b.width>40})()`),
    await js(`(()=>{const b=document.getElementById('submit').getBoundingClientRect();return Math.round(b.right)+'/'+innerWidth})()`));
  ok('820 详情无溢出', await js('document.documentElement.scrollWidth<=innerWidth+1'));
  await shot('14-SKU详情-820');

  await goto('#/requisitions', 'c');
  ok('820 台账无溢出', await js('document.documentElement.scrollWidth<=innerWidth+1'));
  await shot('15-请购管理-820');

  /* ================= 其余状态 ================= */
  await metrics(1440, 940);
  await goto('#/sku/LT-3021', 'c');
  ok('数据不足不形成数量', await mainHas('未形成'));
  ok('数据不足 AI 为无可用事实', await js(`document.querySelector('.ai-head .chip').textContent.trim()==='无可用事实'`));
  ok('草案标注未生效', await mainHas('政策草案未生效'));
  await shot('16-SKU详情-数据不足-1440');

  await goto('#/sku/CB-1023', 'c');
  ok('AI 失败态可重试', await js(`document.querySelector('.ai-head .chip').textContent.trim()==='生成失败'`) && await mainHas('重试'));
  ok('失败不影响规则结论', await js(`document.querySelector('.verdict').innerText.includes('50')`));
  await shot('17-SKU详情-AI失败-1440');

  const errs = await js('window.__errs ? window.__errs.length : 0');
  ok('无脚本异常', errs === 0, errs);

  fs.writeFileSync(path.join(__dirname, '_e2e-result.json'), JSON.stringify(results, null, 1));
  const pass = results.filter(r => r.pass).length;
  console.log(results.map(r => `${r.pass ? 'PASS' : 'FAIL'}  ${r.name}${r.pass ? '' : '   [' + r.extra + ']'}`).join('\n'));
  console.log(`\n${pass}/${results.length} 通过`);

  ws.close(); child.kill();
  setTimeout(() => { try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) { } process.exit(pass === results.length ? 0 : 1); }, 500);
})().catch(e => { console.error('E2E ERROR:', e.message); process.exit(2); });
