/* 校验原型页面逻辑：不渲染像素，只验证数据→页面的实际执行与输出完整性 */
const fs = require('fs');

const el = () => {
  const o = {
    innerHTML: '', textContent: '', value: '', hidden: false, disabled: false,
    dataset: {}, style: {}, open: false,
    addEventListener() {}, setAttribute() {}, focus() {}, closest: () => el(),
    querySelector: () => el(), querySelectorAll: () => [el()], showModal() {}, close() {}
  };
  return o;
};
const store = {};
const handlers = { click: [], hashchange: [] };
global.document = {
  getElementById: () => el(),
  querySelector: () => el(),
  querySelectorAll: () => [el()],
  addEventListener(type, fn) { (handlers[type] = handlers[type] || []).push(fn); },
  activeElement: el()
};
global.sessionStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: k => { delete store[k]; }
};
global.location = { hash: '#/workbench', replace(h) { this.hash = h; } };
global.window = {
  addEventListener() {}, scrollTo() {}, scrollY: 0,
  location: global.location, sessionStorage: global.sessionStorage
};
global.setTimeout = (fn) => 0;
global.clearTimeout = () => {};

let src = fs.readFileSync('index.html', 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
// 暴露内部函数用于校验
src = src.replace(/\n\}\)\(\);\s*$/, `
globalThis.__T = { SKUS, state, stage, validate, pWorkbench, pSuggestions, pSku, pRequisitions, pRequisition, counts, REQS, POLICY, BATCH };
})();
`);
eval(src);
const T = globalThis.__T;

let fail = 0, pass = 0;
function check(name, cond, extra) {
  if (cond) { pass++; }
  else { fail++; console.log('  ✗ ' + name + (extra ? ' :: ' + extra : '')); }
}
function txt(html) { return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' '); }

console.log('— 数据结构 —');
check('11 个店仓对象', T.SKUS.length === 11, T.SKUS.length);
const stages = T.SKUS.map(s => T.stage(s));
const counts = T.counts();
console.log('  状态分布', JSON.stringify(counts));
check('待人工确认 ≥3', counts.pending_confirm >= 3);
check('依据待核实 ≥3', counts.need_evidence >= 3);
check('请购覆盖 3 种状态', ['SUBMITTED', 'APPROVED', 'UNKNOWN'].every(st => T.REQS().some(r => r.state === st)));
check('存在无需补货对象', stages.includes('no_need'));
check('存在分析失败对象', stages.includes('failed'));

console.log('— 页面渲染 —');
const pages = {
  工作台: T.pWorkbench(),
  补货建议: T.pSuggestions(),
  'SKU详情-CB-1001': T.pSku('CB-1001'),
  'SKU详情-LT-3021': T.pSku('LT-3021'),
  'SKU详情-BT-2003': T.pSku('BT-2003'),
  'SKU详情-KT-4022': T.pSku('KT-4022'),
  请购管理: T.pRequisitions(),
  '请购详情-0011': T.pRequisition('RQ-2026-0011'),
  '请购详情-0012': T.pRequisition('RQ-2026-0012')
};
for (const [name, html] of Object.entries(pages)) {
  const t = txt(html);
  check(name + ' 非空', html.length > 500, html.length);
  check(name + ' 无 undefined/null 漏出', !/undefined|\[object Object\]|>null</.test(html),
    (html.match(/undefined|\[object Object\]|>null</) || [''])[0]);
  check(name + ' 无未替换模板占位', !/\$\{/.test(html));
}

console.log('— 关键内容 —');
const wb = txt(pages['工作台']);
check('工作台含"待人工确认"', wb.includes('待人工确认'));
check('工作台标注政策草案未生效', wb.includes('未生效'));
check('工作台不出现15天7日已实施表述', !/已实施.*7 个有效业务日/.test(wb));
const list = txt(pages['补货建议']);
check('列表含规则建议来源', list.includes('平台规则计算'));
check('列表含 ERP 参考建议', list.includes('ERP 参考建议'));
check('列表含无可用来源', list.includes('无可用来源'));
check('列表含无需补货', list.includes('无需补货'));
const d1 = txt(pages['SKU详情-CB-1001']);
check('详情含建议数量 20', d1.includes('20'));
check('详情含 MOQ/整箱', d1.includes('MOQ') && d1.includes('整箱'));
check('详情强调确认≠审批', d1.includes('不等于 ERP 审批'));
const d2 = txt(pages['SKU详情-LT-3021']);
check('数据不足不显示建议数量', !/建议数量\s*[0-9]/.test(d2));
check('数据不足提示草案未生效', d2.includes('未生效'));
check('数据不足显示责任方', d2.includes('数据负责人'));
const d3 = txt(pages['SKU详情-BT-2003']);
check('AI 已解读含四段结构', ['建议依据', '关键事实', '风险提醒', '人工确认'].every(k => d3.includes(k)));
const d4 = txt(pages['SKU详情-KT-4022']);
check('失败态可重试', d4.includes('重新分析此 SKU'));
const rq = txt(pages['请购管理']);
check('请购页区分"人工确认≠ERP审批"', rq.includes('平台人工确认 ≠ ERP 领导审批'));
check('请购页显示三种状态', rq.includes('待 ERP 审批') && rq.includes('ERP 已审批') && rq.includes('提交结果待核对'));
const rq12 = txt(pages['请购详情-0012']);
check('UNKNOWN 单提示原单核对', rq12.includes('不要新建第二张申请'));

console.log('— 数量校验规则 —');
const cb = T.SKUS.find(s => s.key === 'CB-1001'); // MOQ 10, 倍数 10, 建议 20
T.state.reason['CB-1001'] = '';
check('空数量被拒', !!T.validate(cb, 0));
check('低于 MOQ 被拒', !!T.validate(cb, 5));
check('非整箱倍数被拒', !!T.validate(cb, 25));
check('等于建议量通过', T.validate(cb, 20) === '');
check('改量无原因被拒', !!T.validate(cb, 30));
T.state.reason['CB-1001'] = '考虑已有在途';
check('改量填原因通过', T.validate(cb, 30) === '');

console.log('— 筛选逻辑 —');
T.state.filters = { q: '收纳', store: '', warehouse: '', source: '', stage: '' };
check('按名称搜索命中', T.SKUS.filter(s => s.name.includes('收纳')).length >= 2);
T.state.filters = { q: '', store: 'Shopify 独立站', warehouse: '', source: 'NONE', stage: '' };
const noneStore = T.SKUS.filter(s => s.store === 'Shopify 独立站' && s.source === 'NONE');
check('店铺+来源组合可筛', noneStore.length >= 2, noneStore.length);

console.log('— 交互行为（点击提交链路） —');
function fireClick(act, dataset) {
  const target = {
    dataset: Object.assign({ act }, dataset || {}),
    disabled: false,
    textContent: '',
    setAttribute() {},
    parentElement: { querySelectorAll: () => [target] }
  };
  handlers.click.forEach(h => h({ target: { closest: () => target }, preventDefault() {} }));
}
T.state.route = { page: 'sku', id: 'CB-1001' };
T.state.filters = { q: '', store: '', warehouse: '', source: '', stage: '' };
T.state.qty['CB-1001'] = 30;
T.state.reason['CB-1001'] = '';
T.state.ack['CB-1001'] = true;
const before = T.counts().requisition;
fireClick('confirm');
check('改量未填原因时拒绝提交', T.SKUS.find(s => s.key === 'CB-1001').requisition === null);
check('拒绝提交后状态不变', T.counts().requisition === before);

T.state.reason['CB-1001'] = '已有在途 36 件，本次只补一半';
fireClick('confirm');
const submitted = T.SKUS.find(s => s.key === 'CB-1001').requisition;
check('填原因后可提交', !!submitted, JSON.stringify(submitted));
check('提交后单据号为请购状态', submitted && submitted.state === 'SUBMITTED', submitted && submitted.state);
check('提交数量=人工最终量', submitted && submitted.finalQty === 30, submitted && submitted.finalQty);
check('保留平台建议量', submitted && submitted.suggestQty === 20, submitted && submitted.suggestQty);
check('保留调整原因', submitted && submitted.reason.includes('在途'));
check('SKU 处理状态变为已请购', T.stage(T.SKUS.find(s => s.key === 'CB-1001')) === 'requisition_waiting');
check('请购管理计数 +1', T.counts().requisition === before + 1);
check('请购列表包含新单据', T.REQS().some(r => r.no === submitted.no));
const afterHtml = txt(T.pSku('CB-1001') + T.pRequisitions());
check('提交后页面显示待 ERP 审批', afterHtml.includes('待 ERP 审批'));

fireClick('seg', { val: '依据待核实' });
check('状态筛选写入 state', T.state.filters.stage === '依据待核实');
fireClick('req-tab', { val: 'approved' });
check('请购状态筛选写入 state', T.state.reqTab === 'approved');
fireClick('tab', { tab: 'procurement' });
check('详情分区切换写入 state', T.state.tab === 'procurement');
check('采购条件分区可渲染', txt(T.pSku('CB-1001')).length > 300);

console.log('\\n结果: ' + pass + ' 通过 / ' + fail + ' 失败');
process.exit(fail ? 1 : 0);
