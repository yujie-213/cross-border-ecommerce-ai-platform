/* B V1.0 interaction prototype. Synthetic state only; no network or business IO. */
'use strict';
const $ = (s, root = document) => root.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tag = (text, tone = '') => `<span class="badge ${tone}">${esc(text)}</span>`;
const button = (text, action, tone = '', extra = '') => `<button class="button ${tone}" data-action="${action}" ${extra}>${text}</button>`;
const link = (text, path, tone = '') => `<a class="button ${tone}" href="#${path}">${text}</a>`;
const facts = rows => rows.map(([k,v]) => `<div class="fact"><span>${k}</span><b>${v}</b></div>`).join('');
let state;
let dialogReturn = null;
let timer;
function resetState() {
  state = { queue: 'pending', search: '', workMode: 'normal', analysisMode: 'complete',
    risk: 'suspected', riskVersion: 1, riskReason: '', riskHistory: [], riskTab: 'all',
    purchaseView: 'single', purchaseFilter: '全部商品', quantity: '100', riskQuery: 'ok', returnTo: null,
    cases: {
      apparel: {id:'CASE-DEMO-001', title:'上衣尺码与描述不符', product:'棉质宽松上衣 / DEMO-TEE-M', status:'待处理', revision:1, linked:false,
        messages:[{role:'客户主张', text:'收到的 M 码上衣比商品页面尺码表小，穿着偏紧。想确认如何处理。', time:'今天 09:12'}],
        draft:'', original:'', draftRevision:0, reviews:[], evidence:false, scenario:'normal', note:''},
      usb: {id:'CASE-DEMO-002', title:'USB 转接器诉求待澄清', product:'USB-C 转接器 / DEMO-USB-C', status:'待补证', revision:2, linked:false,
        messages:[{role:'客户主张', text:'这件商品尺码太小，我想换大一码。', time:'今天 08:55'}],
        draft:'', original:'', draftRevision:0, reviews:[], evidence:false, scenario:'conflict', note:''},
      safety: {id:'CASE-DEMO-003', title:'充电时异常发热及异味', product:'便携充电器 / DEMO-CHARGER', status:'优先升级', revision:1, linked:true,
        messages:[{role:'客户主张', text:'充电时闻到焦味，外壳也很烫，是否还能继续使用？', time:'今天 09:18'}],
        draft:'', original:'', draftRevision:0, reviews:[], evidence:false, scenario:'safety', note:''},
      review: {id:'CASE-DEMO-004', title:'包装破损，回复待审核', product:'棉质宽松上衣 / DEMO-TEE-M', status:'待审核', revision:3, linked:true,
        messages:[{role:'客户主张', text:'外包装破了，衣服暂未发现破损，已补充包装照片。', time:'昨天 16:40'}],
        draft:'感谢您补充包装照片。我们已记录包装破损情况，请再确认衣物是否有损坏，便于人工核实后续处理方案。',
        original:'感谢您补充包装照片。我们已记录包装破损情况，请再确认衣物是否有损坏，便于人工核实后续处理方案。',
        draftRevision:3, reviews:[], evidence:true, scenario:'normal', note:''}
    }
  };
}
resetState();
function route() {
  const raw = location.hash.slice(1) || '/home';
  const [path, query = ''] = raw.split('?');
  return { path, query: new URLSearchParams(query) };
}
function go(path) { location.hash = path; }
function toast(text) { $('#toast').textContent = text; $('#toast').hidden = false; clearTimeout(timer); timer = setTimeout(() => $('#toast').hidden = true, 3500); }
function panel(title, body, meta = '', action = '') {
  return `<section class="panel"><div class="panel-head"><div><h2>${title}</h2>${meta ? `<small>${meta}</small>` : ''}</div>${action}</div><div class="panel-body">${body}</div></section>`;
}
function head(title, subtitle, actions = '') { return `<div class="page-head"><div><div class="eyebrow">AFTER SALES / B V1.0</div><h1>${title}</h1><p class="subtitle">${subtitle}</p></div><div class="button-row">${actions}</div></div>`; }
function scope(extra = '') { return `<div class="scope"><span>${tag('中台教学资料 · 模拟','blue')}</span><span>工作区 <b>售后演示</b></span><span>店铺 <b>演示服饰店 US</b></span>${extra}</div>`; }
function notice(title, text, tone = 'amber') { return `<div class="notice ${tone}"><strong>${title}</strong><p>${text}</p></div>`; }
function modeControl(label, value, options, id) {
  return `<div class="demo-control"><span>原型状态演示</span><label for="${id}">${label}</label><select id="${id}" data-control="${id}">${options.map(([v,n])=>`<option value="${v}" ${value===v?'selected':''}>${n}</option>`).join('')}</select></div>`;
}
function shell(path) {
  const purchase = path.startsWith('/replenishment');
  const home = path === '/home';
  const nav = purchase ? [ ['▦','补货工作区','/replenishment'], ['↗','返回智能售后','/after-sales'] ] : [
    ['▦','售后工作台','/after-sales'], ['≡','体验与退货分析','/after-sales/analyses'], ['◇','质量风险','/after-sales/risks'], ['▤','知识与资料','/after-sales/knowledge'] ];
  const active = path.includes('/cases/') ? '/after-sales' : path.includes('/analyses/') ? '/after-sales/analyses' : path;
  $('#sidebar').innerHTML = `<a class="brand" href="#/home"><b>序</b><span>序衡<small>COMMERCE OPERATIONS</small></span></a><a class="platform-return" href="#/home">← 返回平台首页</a><div class="workspace"><span>${purchase?'补':'售'}</span><div>${purchase?'智能补货':'智能售后'}<small>${purchase?'采购工作区 · 演示':'客户体验工作区 · 演示'}</small></div></div><div class="nav-label">${home?'平台导航':purchase?'智能补货 Agent':'智能售后与客户体验'}</div><nav aria-label="工作区导航">${(home ? [['⌂','平台首页','/home'],['▦','智能售后','/after-sales'],['↗','智能补货','/replenishment']] : nav).map(([icon,name,url])=>`<a href="#${url}" class="${active===url?'active':''}" ${active===url?'aria-current="page"':''}><span aria-hidden="true">${icon}</span>${name}</a>`).join('')}</nav><div class="sidebar-bottom"><strong>本地交互原型</strong>全部为合成样例 · 无业务连接</div>`;
  $('#crumb').textContent = home ? '平台首页' : purchase ? '智能补货 / 风险协作' : '智能售后与客户体验';
}
function homePage() {
  return `<div class="overview"><div class="eyebrow">COMMERCE OPERATIONS</div><h1>让每一次客户反馈，有据可循</h1><p>在同一中台处理售后、观察体验变化，并将经人工确认的质量风险带回采购工作区。</p><small>本次预览聚焦 B V1.0 操作方向；现有补货页面以模拟协作区呈现。</small></div><div class="two-col"><section class="panel"><a class="link-card" href="#/after-sales"><div class="split-title"><h2>智能售后与客户体验</h2><span class="feature-icon">售</span></div><p>客服案件 → 体验分析 → 质量调查，证据与人工决定逐步留存。</p><span class="text-button">进入售后工作台 →</span></a></section><section class="panel"><a class="link-card" href="#/replenishment"><div class="split-title"><h2>智能补货</h2><span class="feature-icon">补</span></div><p>查看单品与批量的质量风险提示，保留原补货数量和采购上下文。</p><span class="text-button">体验补货风险协作 →</span></a></section></div>`;
}
function workbench() {
  const c = Object.entries(state.cases);
  const queues = {pending:['待处理','优先升级'], evidence:['待补证'], review:['待审核'], handled:['已处理','已升级']};
  const filtered = c.filter(([,v])=>queues[state.queue].includes(v.status) && `${v.title} ${v.product} ${v.id}`.toLowerCase().includes(state.search.toLowerCase()));
  return head('售后工作台','先处理安全事项，再核实证据与回复。',button('＋ 新建案件','new-case','primary')) + scope() +
    modeControl('工作区',state.workMode,[['normal','正常队列'],['empty','空队列'],['restricted','无权访问示例']],'workMode') +
    (state.workMode==='restricted' ? notice('当前范围不可访问','本演示不展示受限案件、计数或原文。可切回正常队列继续体验。') :
    `<div class="notice red split"><div><strong>优先处理 · 客户反馈充电器异常发热</strong><p>安全信号直接进入人工升级队列，不等待 AI 或统计门槛。</p></div>${link('立即核实 →','/after-sales/cases/safety','small')}</div><div class="columns"><section class="panel"><div class="tabs" role="group" aria-label="案件队列">${Object.entries({pending:'待处理',evidence:'待补证',review:'待审核',handled:'处理记录'}).map(([k,n])=>`<button class="tab ${state.queue===k?'active':''}" data-queue="${k}" aria-pressed="${state.queue===k}">${n}<span class="count">${state.workMode==='empty'?0:c.filter(([,v])=>queues[k].includes(v.status)).length}</span></button>`).join('')}</div><div class="toolbar"><label>搜索案件 <input id="case-search" value="${esc(state.search)}" placeholder="案件号 / 商品 / 问题" autocomplete="off"></label><small>按下一步责任动作组织</small></div>${state.workMode==='empty'||!filtered.length?'<div class="empty"><h2>当前队列没有案件</h2><p>可切换队列，或新建一条模拟案件。</p></div>':`<div class="table-scroll"><table><thead><tr><th>客户问题 / 目标商品</th><th>处理状态</th><th>下一步</th></tr></thead><tbody>${filtered.map(([id,v])=>`<tr><td><a href="#/after-sales/cases/${id}"><strong>${esc(v.title)}</strong></a><small>${esc(v.product)}</small><small class="mono">${v.id}</small></td><td>${tag(v.status,v.status==='优先升级'?'red':v.status==='待审核'?'blue':'amber')}<small>${v.linked?'已确认目标商品':'待确认订单及商品行'}</small></td><td class="nowrap">${link(v.status==='待审核'?'审核回复':'继续处理 →','/after-sales/cases/'+id,'small')}</td></tr>`).join('')}</tbody></table></div>`}<div class="table-foot"><span>当前授权范围 · 模拟案件</span><span>内容仅在本次页面会话中保留</span></div></section><aside class="side-stack">${panel('待调查线索',`<p>棉质上衣 · 实收退货率上升</p><p class="hint">2.5% → 30% · +27.5 个百分点<br>异常线索尚未确认质量缺陷。</p><div class="spaced">${link('查看同口径分析 →','/after-sales/analyses','small')}</div>`,'完整教学金样 v1 · 模拟')}${panel('采购协作',`<p class="muted">仅人工确认且在有效范围内的风险进入补货提醒。</p><div class="spaced">${link('查看质量风险','/after-sales/risks','small')}</div>`,'风险只提醒，不改补货量')}</aside></div>`);
}
function currentCase() { return state.cases[route().path.split('/')[3]]; }
function casePage(id) {
  const c = state.cases[id];
  if (!c) return '<div class="empty"><h1>案件不可访问</h1><p>返回工作台选择演示案件。</p></div>';
  const stale = !!c.draft && c.draftRevision !== c.revision;
  const blocked = !c.linked || !c.evidence || ['no-policy','failure','conflict','safety'].includes(c.scenario);
  const identity = c.product.includes('USB') ? ['DEMO-ORDER-102 / L1','演示数码店 US / 演示仓 A'] : c.product.includes('CHARGER') ? ['DEMO-ORDER-103 / L1','演示数码店 US / 演示仓 A'] : ['DEMO-ORDER-101 / L1','演示服饰店 US / 演示仓 A'];
  const title = head(c.title,`${c.id} · 本地合成样例`,button('查看处理历史','case-history'));
  const warn = c.scenario==='safety' ? notice('安全信号 · 优先人工升级','客户陈述为异常发热及异味。请建议暂停使用并转专人核实，不提供拆机操作，不宣告商品安全。','red') : c.scenario==='conflict' ? notice('诉求与已核实属性冲突','USB 转接器没有服装尺码。保留客户原话，先澄清目标商品和具体问题，不能直接判断质量。') : '';
  return `<a class="back" href="#/after-sales?queue=${state.queue}">← 返回原案件队列</a>` + title +
    `<div class="case-meta">${tag(c.status,c.status==='优先升级'?'red':'amber')}${tag('模拟来源','blue')}<span>caseRevision <b>${c.revision}</b></span><span>操作者 <b>admin（模拟）</b></span><span>${c.linked?'已确认目标行':'未关联订单 / SKU'}</span></div>` +
    modeControl('案件情形',c.scenario,[['normal','正常处理'],['conflict','商品诉求冲突'],['no-policy','无适用政策'],['failure','取证 / AI 失败'],['safety','安全升级']],'caseScenario') + warn +
    `<div class="case-grid">${panel('客户会话',c.messages.map(m=>`<div class="message ${m.role==='内部澄清'?'internal':''}"><small>${esc(m.role)} · ${esc(m.time)}</small>${esc(m.text)}</div>`).join('') +
      `<label class="label" for="new-message">追加客户信息 / 内部澄清</label><textarea id="new-message" rows="4" placeholder="追加新信息，保留原始记录"></textarea><label class="label spaced" for="message-kind">信息类型</label><select id="message-kind"><option>客户主张</option><option>内部澄清</option></select><div class="spaced">${button('追加记录','append-message')}</div>`, '原话与内部记录分别保留')}
      ${panel('核实对象与证据',
        (c.linked ? `${facts([['目标商品',esc(c.product)],['订单 / 明细',identity[0]],['店铺 / 仓库',identity[1]]])}<div class="spaced">${button('重新选择目标行','choose-target','small')}</div>` : `<p class="muted">此案件尚无已确认商品。录入主张不会自动关联第一条候选。</p><div class="spaced">${button('确认目标商品','choose-target','primary')}</div>`) +
        `<hr><h3>付款、履约与售后</h3>${c.scenario==='failure'?notice('取证失败 · 模拟超时','付款域暂不可用；其余已保存事实仍保留。失败不表示没有付款。'):''}${c.evidence?facts([['付款','已付款 · USD 24.00（模拟）'],['发货','已发货 · 不证明签收'],['售后','客户申请已记录 · 未执行退款']]):'<p class="hint">尚未取得已核实事实。客户陈述不等于交易状态。</p>'}<div class="spaced">${button(c.evidence?'重新核查证据':'获取证据（模拟）','case-evidence','',c.linked?'':'disabled')}</div><hr><h3>适用政策</h3>${c.scenario==='no-policy'?notice('无适用政策','可继续记录澄清和转人工，不能承诺退款或退货资格。'):c.evidence?`<div class="policy"><b>尺码与描述处理 · v1 / §2</b>${tag('已发布 · 模拟','teal')}<p>核对商品实测尺寸、尺码表与目标订单明细；由人工按适用条款决定后续方案。</p><button class="text-button" data-action="policy-detail">查看政策原文与适用条件</button></div>`:'<p class="hint">核实商品和业务日期后匹配政策。</p>'}`, 'OBSERVED 与 CLAIM 在界面中分开')}
      ${panel('回复草稿与人工审核',
        (stale?notice('内容已更新 · 草稿已过期','新增消息改变了案件版本，请重新生成后再采纳。'):'') +
        `${c.note?notice('本次操作',esc(c.note),c.note.includes('失败')?'amber':'green'):''}<div class="button-row">${button(c.generating?'正在生成模拟建议…':'生成建议（模拟）','generate','primary',blocked||c.generating?'disabled':'')}</div>${blocked?`<p class="hint">${!c.linked?'先确认目标商品。':!c.evidence?'先获取证据。':c.scenario==='safety'?'安全事项先升级人工。':c.scenario==='conflict'?'先澄清诉求冲突。':c.scenario==='failure'?'模拟能力失败，可保留手工记录。':'缺少适用政策，转人工核实。'}</p>`:''}<label class="label spaced" for="reply-draft">人工回复稿</label><textarea id="reply-draft" rows="7" placeholder="生成模拟草稿后可在此修订；也可记录人工澄清">${esc(c.draft)}</textarea><p class="hint">${c.original?`AI原稿基于 revision ${c.draftRevision} · <button class="text-button" data-action="original-draft">查看原稿</button>`:'AI 尚未生成建议'}</p><label class="label spaced" for="review-reason">审核 / 升级理由</label><textarea id="review-reason" rows="2" placeholder="说明核实依据或下一步动作"></textarea><div class="field-error" id="case-error" role="alert"></div><div class="button-row">${button('保存并采纳','save-review','primary',!c.draft||stale||blocked?'disabled':'')}${button('退回修改','return-review')}${button('升级人工','escalate','danger')}</div><p class="hint">仅保存内部处理记录。不会发送回复、退款或操作 ERP。</p>`, 'AI 原稿和人工决定分别留存')}
    </div>`;
}

function analysesPage() {
  const unknown = ['immature','insufficient'].includes(state.analysisMode);
  return head('客户体验与退货分析','从同口径变化出发，回到真实构成它的证据。',button('新建分析','new-analysis','primary')) + scope('<span>资料版本 <b>完整教学金样 v1</b></span>') +
    modeControl('分析状态',state.analysisMode,[['complete','完整成熟金样'],['immature','仅 29 天，群组未成熟'],['insufficient','19 订单，样本不足'],['failed','分析失败'],['historical','历史报告 / 新版本对比']],'analysisMode') +
    (state.analysisMode==='failed'?notice('分析任务失败 · 模拟 Schema 不合法','确定性输入与原报告仍可读；本次 AI 解释不可用，未替换为正常结论。'):'') +
    `<div class="panel"><div class="panel-head"><div><h2>两窗对比 · 服饰体验观察</h2><small>报告 DEMO-ANALYSIS-01 / v${state.analysisMode==='historical'?'1（历史）':'2'} · teaching-return-rules-v1 · 模拟统计</small></div>${tag(unknown?'受限报告':'确定性结果可用',unknown?'amber':'teal')}</div><div class="panel-body"><div class="report-summary"><div><small>前窗 / 后窗 · 实际末次发货入群</small><b>09.01–09.21 / 09.21–10.11</b><small>半开区间 [S,E) · Asia/Shanghai</small></div><div><small>观察截止 / 每群组观察期</small><b>${state.analysisMode==='immature'?'29 天 · 未成熟':'11.15 / 30 × 24h'}</b><small>固定目标集合，不剔除坏记录凑样本</small></div><div><small>异常判定门槛</small><b>≥ 10 个百分点</b><small>且后窗实收 ≥ 3 件；每窗 ≥20 订单-SKU / ≥20 件</small></div></div>${unknown?notice('UNKNOWN · '+({immature:'固定群组尚未满 30 天',insufficient:'成熟订单-SKU 仅 19，不足 20',historical:'这是历史版本，当前结论需重新核查',failed:'AI 解释失败，事实需单独核对'}[state.analysisMode]),'已知计数可追溯，但不能用 0% 或“无异常”代替缺证据结论。'):''}</div><div class="table-scroll"><table class="comparison"><thead><tr><th>商品 / 同一店仓</th><th>前窗 实收 / 实发</th><th>后窗 实收 / 实发</th><th>率变化</th><th>观察结论</th></tr></thead><tbody><tr class="highlight"><td><strong>棉质宽松上衣</strong><small>DEMO-TEE-M · 演示仓 A</small></td><td><button class="text-button" data-action="drill" data-drill="before">1 / 40 件</button><small>2.5% · 20 订单-SKU</small></td><td><button class="text-button" data-action="drill" data-drill="received">${state.analysisMode==='historical'?11:12} / 40 件</button><small>${unknown?'UNKNOWN':state.analysisMode==='historical'?'27.5%':'30%'} · ${state.analysisMode==='insufficient'?19:20} 订单-SKU</small></td><td><strong>${unknown?'UNKNOWN':state.analysisMode==='historical'?'+25 pp':'+27.5 pp'}</strong><small>百分点差，非相对增幅</small></td><td>${tag(unknown?'需补证':'待调查异常','amber')}<small>不等于质量缺陷</small></td></tr><tr><td><strong>基础款棉袜</strong><small>DEMO-SOCKS · 演示仓 A</small></td><td>1 / 40 件<small>2.5% · 20 订单-SKU</small></td><td>1 / 40 件<small>${unknown?'UNKNOWN':'2.5%'} · 20 订单-SKU</small></td><td><strong>${unknown?'UNKNOWN':'0 pp'}</strong></td><td>${tag(unknown?'未核实':'未达异常阈值',unknown?'amber':'teal')}</td></tr></tbody></table></div><div class="table-foot"><span>主指标按实收退货件数计算；申请与退款分别统计</span><button class="text-button" data-action="drill" data-drill="denominator">查看分母 / 发货群组</button></div></div>
    <div class="two-col section-gap">${panel('退货阶段与客户主题',`<div class="table-scroll"><table><thead><tr><th>阶段</th><th>后窗件数</th><th>含义</th></tr></thead><tbody><tr><td>申请 / 有效授权</td><td>16 / 14</td><td>未等同实收</td></tr><tr><td>实收 / 已退款</td><td>12 / 8</td><td>阶段流转不重复计件</td></tr><tr><td>期外 / 已取消</td><td>2 / 2</td><td>单列，不计入主分子</td></tr></tbody></table></div><hr><button class="text-button" data-action="feedback">尺码诉求 · 8 / 12 条反馈 → 查看去重原文</button><p class="hint">主题分母为 12 条唯一反馈，不是退货件数；多标签可重叠。</p>`)}${panel('人工调查',`<p>上衣退货率上升与尺码反馈同时出现。</p><p class="hint">替代解释：尺码表调整、流量构成或批次差异。当前没有足够证据宣告商品缺陷。</p><label class="label spaced" for="investigation-note">调查记录</label><textarea id="investigation-note" rows="3" placeholder="核对实测尺寸、页面版本、批次与样本口径">${esc(state.investigation||'')}</textarea><div class="spaced">${button('保存调查，查看疑似风险','investigate','primary')}</div>`,'AI 假设与确定性指标分开')}</div>${state.analysisMode==='historical'?panel('版本差异','<p>v1 → v2：补入迟到的 1 件实收事件，后窗 11/40 → 12/40。旧报告不覆写，规则版本相同。</p>','模拟版本差异'):''}`;
}
const riskNames = {suspected:'疑似待调查',confirmed:'当前有效',rejected:'已驳回',closed:'已关闭',revoked:'已撤销',expired:'已到期'};
function risksPage() {
  const shown = state.riskTab==='all'||state.riskTab==='current'&&state.risk==='confirmed'||state.riskTab==='suspected'&&state.risk==='suspected'||state.riskTab==='history'&&!['confirmed','suspected'].includes(state.risk);
  return head('质量风险','调查、范围与人工决定，构成风险提醒的依据。',link('体验补货展示 →','/replenishment')) + scope() +
    modeControl('生命周期',state.risk,Object.entries(riskNames),'riskStatus') +
    (state.returnTo?`<div class="notice split"><span>从补货证据进入；原筛选、视图和采购编辑仍保留。</span>${button('返回原补货上下文','back-purchase','small')}</div>`:'') +
    `<section class="panel"><div class="tabs" role="group" aria-label="风险状态">${[['all','全部'],['current','当前有效'],['suspected','疑似待调查'],['history','历史']].map(([k,n])=>`<button class="tab ${state.riskTab===k?'active':''}" data-risk-tab="${k}" aria-pressed="${state.riskTab===k}">${n}</button>`).join('')}</div>${shown?`<div class="panel-body"><div class="split-title"><div><h2>棉质宽松上衣 · 尺码一致性待核实</h2><small class="mono">RISK-DEMO-01 / v${state.riskVersion}</small></div>${tag(riskNames[state.risk],state.risk==='confirmed'?'amber':state.risk==='suspected'?'blue':'')}</div><p class="subtitle">来源：完整教学金样 v1 / 分析报告 DEMO-ANALYSIS-01 · 模拟</p><hr><div class="two-col"><div>${facts([['精确对象','DEMO-PRODUCT-TEE / DEMO-TEE-M'],['店铺 / 仓库','DEMO-STORE-US / DEMO-WH-A'],['仓库语义','显式指定演示仓 A'],['消费方式','仅演示教学绑定 · 正常 ERP 模式不可见']])}</div><div>${facts([['状态 / 当前核查',riskNames[state.risk]],['有效期',state.risk==='confirmed'?'2026-11-16 至 2026-12-16（不含）':'尚未确认或已失效'],['实际确认人',state.risk==='confirmed'?'admin（模拟人工操作）':'无当前有效确认'],['依据','12/40 vs 1/40 · 尺码投诉，需调查']])}</div></div><div class="spaced">${notice(state.risk==='suspected'?'疑似风险不形成有效补货提醒':'风险只作提醒','原参考补货量、候选和采购资格保持。关闭、撤销和到期后的旧版本只作为历史。',state.risk==='suspected'?'blue':'amber')}</div><div class="button-row spaced">${button('查看证据','risk-evidence')}${state.risk==='suspected'?button('人工确认风险','confirm-risk','primary')+button('驳回','reject-risk'):state.risk==='confirmed'?button('关闭风险','close-risk')+button('撤销风险','revoke-risk','danger'):button('新建待调查版本','new-risk-version')}</div><div class="history"><h3>调查与决定记录</h3><div class="history-item">报告阈值命中 → 形成疑似线索<small>原始事实保留；没有自动确认风险</small></div>${state.riskHistory.map(h=>`<div class="history-item">v${h.version} · ${esc(h.status)}<small>admin（模拟） · ${esc(h.reason)}</small></div>`).join('')}${state.investigation?`<div class="history-item">人工调查补充<small>${esc(state.investigation)}</small></div>`:''}</div></div>`:'<div class="empty"><h2>当前页签没有风险记录</h2><p>可以切换“全部”或演示其他生命周期状态。</p></div>'}</section>`;
}
function purchasePage() {
  const valid = state.risk==='confirmed' && state.riskQuery==='ok';
  const riskText = state.riskQuery==='failure'?'风险未核实':valid?'存在有效质量风险提醒':'本次完整查询无适用风险';
  return `<div class="page-head"><div><div class="eyebrow">REPLENISHMENT / 采购协作演示</div><h1>补货工作区</h1><p class="subtitle">质量风险从售后工作区读取，原补货计算保持。</p></div>${link('管理质量风险','/after-sales/risks')}</div>` +
    modeControl('风险查询',state.riskQuery,[['ok','完整查询'],['failure','查询失败 / 超过核查期限'],['wrong-store','错店范围不适用'],['normal-mode','正常 ERP 模式排除教学风险']],'riskQuery') +
    `<div class="panel"><div class="tabs" role="group" aria-label="补货视图">${[['single','单品详情'],['batch','批量建议']].map(([k,n])=>`<button class="tab ${state.purchaseView===k?'active':''}" data-purchase-view="${k}" aria-pressed="${state.purchaseView===k}">${n}</button>`).join('')}</div><div class="toolbar"><label>原列表筛选 <select id="purchase-filter"><option ${state.purchaseFilter==='全部商品'?'selected':''}>全部商品</option><option ${state.purchaseFilter==='需补货'?'selected':''}>需补货</option></select></label><span class="badge blue">合成补货输入 · 固定参考量 100</span></div></div><div class="section-gap">${state.purchaseView==='batch'?`<div class="panel"><div class="table-scroll"><table><thead><tr><th>商品 / 店仓</th><th>参考量</th><th>候选量</th><th>质量风险</th><th>操作</th></tr></thead><tbody><tr><td>棉质宽松上衣<small>DEMO-TEE-M / 演示仓 A</small></td><td><strong>100 件</strong></td><td>100 件</td><td>${tag(valid?'有效提醒':state.riskQuery==='failure'?'未核实':'无适用提醒',valid||state.riskQuery==='failure'?'amber':'')}<small>当前核查与历史引用分开</small></td><td>${button('查看风险','risk-evidence','small')}</td></tr><tr><td>基础款棉袜<small>DEMO-SOCKS / 演示仓 A</small></td><td>0 件</td><td>无</td><td>${tag(state.riskQuery==='failure'?'未核实':'无适用提醒')}</td><td>—</td></tr></tbody></table></div></div>`:
      `<div class="purchase-grid"><section class="panel"><div class="panel-head"><div class="detail-title"><span class="object-mark">衣</span><div><h2>棉质宽松上衣 · M 码</h2><small>DEMO-TEE-M / 演示服饰店 US / 演示仓 A</small></div></div></div><div class="panel-body"><div class="risk-summary"><div><strong>${riskText}</strong><p>${valid?'尺码一致性存在待核实问题；有效至 12 月 16 日。':state.riskQuery==='failure'?'查询失败不能推导为无风险；历史引用只供追溯。':'疑似、失效、错店及未获教学绑定的记录不形成有效提醒。'}</p><small>${valid?'当前版本 v'+state.riskVersion:'完整范围匹配与当前状态为准'}</small></div>${button('查看证据','risk-evidence','small')}</div><div class="report-summary"><div><small>可用库存</small><b>20 件</b></div><div><small>参考补货量</small><b data-testid="reference-quantity">100 件</b></div><div><small>候选量 / 原采购门</small><b>100 件</b><small>人工确认、报价、MOQ 与整箱</small></div></div>${facts([['策略','既有补货策略 · 本原型不重算'],['参考数量来源','固定模拟计算结果'],['风险影响','仅展示，不改变计算 / 候选 / 采购资格']])}</div></section>${panel('采购编辑上下文',`<label class="label" for="purchase-quantity">拟采购量（件）</label><input id="purchase-quantity" class="quantity" type="number" min="1" step="1" value="${esc(state.quantity)}"><p class="hint">可修改后打开证据并跨模块往返，数量不会被重置。</p><hr>${button('采购提交未接入','no-purchase','full','disabled')}<p class="hint">本原型仅演示导航和状态，无采购或 ERP 写入。</p>`,'模拟输入，保留于本次会话')}</div>`}</div>`;
}
function knowledgePage() {
  return head('知识与资料','政策版本和教学资料是建议可用性的前置证据。') + scope() +
    panel('四类政策首包（模拟）',`<div class="table-scroll"><table><thead><tr><th>政策类型</th><th>版本 / 状态</th><th>操作</th></tr></thead><tbody>${['尺码与描述处理','3C 安全升级','退货资格、时限、费用与例外','回复承诺与证据适用'].map((n,i)=>`<tr><td>${n}</td><td>v1 ${tag(i===2?'草稿 · 不可用于承诺':'已发布 · 模拟',i===2?'amber':'teal')}</td><td>${button('查看原文','policy-detail','small')}</td></tr>`).join('')}</tbody></table></div>`,'页面展示不代表正式政策发布授权') +
    panel('完整教学金样 v1',facts([['来源性质','MIDDLEWARE_TEACHING_DATA（合成样例）'],['固定总体','40 逻辑订单 × 2 SKU'],['两窗 / 每 SKU','每窗 20 订单-SKU / 40 件'],['校验 / 回读状态','模拟：已验证及独立回读'],['教师答案','独立隔离，本原型没有答案资产']]),'导入、校验、独立回读与激活将在后续后端实现');
}
function render(focusMain = false) {
  const focusedId = document.activeElement?.id;
  const focusedAction = document.activeElement?.dataset?.action;
  const hadControlFocus = document.activeElement && document.activeElement !== document.body;
  if ($('#modal').open) $('#modal').close();
  const {path,query} = route();
  if (path==='/after-sales' && query.has('queue') && ['pending','evidence','review','handled'].includes(query.get('queue'))) state.queue=query.get('queue');
  shell(path);
  const body = path==='/home'?homePage():path==='/after-sales'?workbench():path.startsWith('/after-sales/cases/')?casePage(path.split('/')[3]):path.startsWith('/after-sales/analyses')?analysesPage():path.startsWith('/after-sales/risks')?risksPage():path.startsWith('/after-sales/knowledge')?knowledgePage():path.startsWith('/replenishment')?purchasePage():`<div class="empty"><h1>此原型页面不存在</h1>${link('回到平台首页','/home')}</div>`;
  $('#main').innerHTML = body;
  if (focusMain) $('#main').focus();
  else if (focusedId && document.getElementById(focusedId)) document.getElementById(focusedId).focus({preventScroll:true});
  else if (focusedAction) ($('#main').querySelector(`[data-action="${focusedAction}"]`) || $('#main')).focus({preventScroll:true});
  else if (hadControlFocus) $('#main').focus({preventScroll:true});
}
function modal(title, body, foot = '') {
  if (!$('#modal').open) dialogReturn = document.activeElement;
  $('#modal').innerHTML = `<div class="modal-head"><h2 id="modal-title">${title}</h2><button class="close" data-action="close-modal" aria-label="关闭弹窗">×</button></div><div class="modal-body">${body}</div><div class="modal-foot">${foot||button('关闭','close-modal')}</div>`;
  $('#modal').showModal();
}
function closeModal() { $('#modal').close(); if (dialogReturn?.isConnected) dialogReturn.focus(); }
function receivedRows(n, window = 'after') {
  return Array.from({length:n},(_,i)=>`<tr><td class="mono">DEMO-RET-${window==='before'?'B':'A'}-${String(i+1).padStart(2,'0')}</td><td>received</td><td>1 件</td><td class="mono">DEMO-ORDER-${101+i}/L1</td><td>${button('发货与原文','event-detail','small',`data-event="${i+1}" data-window="${window}"`)}</td></tr>`).join('');
}
function riskEvidence() {
  const fromPurchase=route().path.startsWith('/replenishment');
  modal('质量风险证据',`${tag('全部为合成样例','blue')}<div class="spaced">${facts([['当前状态',state.riskQuery==='failure'&&fromPurchase?'未核实（模拟查询失败）':riskNames[state.risk]],['风险范围','DEMO-PRODUCT-TEE / DEMO-TEE-M / DEMO-STORE-US / DEMO-WH-A'],['来源','教学金样 v1 · 授权教学消费'],['统计证据','前窗 1/40；后窗 12/40；差 27.5 pp'],['调查结论',esc(state.investigation||'尺码一致性待补充实测，尚未宣告缺陷')]])}</div>${notice('历史与当前分开','历史报告引用的风险版本保留；当前失效或查询失败时不能沿用旧有效状态。')}<p>采购摘要只显示商品与调查证据，不带客户身份。参考补货量始终 100 件。</p>`,button('返回原页面','close-modal')+button('进入质量风险详情','to-risk','primary'));
}
function stashCase(c) { if ($('#reply-draft')) c.draft=$('#reply-draft').value; }
document.addEventListener('input', e=>{
  if (e.target.id==='reply-draft') currentCase().draft=e.target.value;
  if (e.target.id==='purchase-quantity') state.quantity=e.target.value;
  if (e.target.id==='case-search') { const pos=e.target.selectionStart; state.search=e.target.value; render(); $('#case-search').focus(); $('#case-search').setSelectionRange(pos,pos); }
});
document.addEventListener('change',e=>{
  const key=e.target.dataset.control;
  if(key==='caseScenario') {const c=currentCase();stashCase(c);c.scenario=e.target.value;c.note='';if(c.scenario==='safety')c.status='优先升级';else if(c.status==='优先升级')c.status='待补证';render();}
  else if(key==='riskStatus'){state.risk=e.target.value;render();}
  else if(key){state[key]=e.target.value;render();}
  if(e.target.id==='purchase-filter')state.purchaseFilter=e.target.value;
});
document.addEventListener('click',e=>{
  if(e.target.closest('a.skip')) {e.preventDefault();$('#main').focus();return;}
  const anchor=e.target.closest('a[href^="#/"]');
  if(anchor && currentCase()) {
    const c=currentCase(),saved=c.reviews.at(-1)?.text||c.original;
    if(c.draft && c.draft!==saved){
      e.preventDefault();state.pendingNavigate=anchor.getAttribute('href').slice(1);
      modal('回复稿尚未保存', '<p>人工编辑仍保留在本次页面会话中。重新加载页面会重置模拟数据。</p>', button('继续编辑','close-modal')+button('保留草稿并离开','leave-case','primary'));return;
    }
  }
  const el=e.target.closest('button'); if(!el||el.disabled)return;
  if(el.dataset.queue){state.queue=el.dataset.queue;go('/after-sales?queue='+state.queue);render();return;}
  if(el.dataset.riskTab){state.riskTab=el.dataset.riskTab;render();return;}
  if(el.dataset.purchaseView){state.purchaseView=el.dataset.purchaseView;render();return;}
  const action=el.dataset.action; const c=currentCase();
  if(action==='close-modal'){closeModal();return;}
  if(action==='leave-case'){closeModal();go(state.pendingNavigate);return;}
  if(action==='reset'){resetState();render();toast('演示数据已重置；全部操作仍为模拟。');return;}
  if(action==='new-case'){
    modal('新建售后案件（模拟）',`<label class="label" for="case-title">客户问题标题</label><input id="case-title" class="full" maxlength="120" placeholder="例如：收到商品后发现包装破损"><label class="label spaced" for="case-body">客户原话</label><textarea id="case-body" rows="4" maxlength="2000"></textarea><p class="hint">允许尚无订单与 SKU。此操作仅增加本次页面会话内的合成演示案件。</p><div id="modal-error" class="field-error" role="alert"></div>`,button('取消','close-modal')+button('创建模拟案件','create-case','primary'));return;
  }
  if(action==='create-case'){
    const title=$('#case-title').value.trim(),body=$('#case-body').value.trim();
    if(!title||!body){$('#modal-error').textContent='请填写标题与客户原话。';return;}
    const id='local'+Object.keys(state.cases).length;
    state.cases[id]={id:'CASE-DEMO-'+id,title,product:'尚未确认',status:'待处理',revision:1,linked:false,messages:[{role:'客户主张',text:body,time:'本次会话'}],draft:'',original:'',draftRevision:0,reviews:[],evidence:false,scenario:'normal',note:''};
    closeModal();go('/after-sales/cases/'+id);return;
  }
  if(action==='append-message'){
    const text=$('#new-message').value.trim();if(!text){toast('先填写需要追加的信息。');return;}
    stashCase(c);c.messages.push({role:$('#message-kind').value,text,time:'本次会话'});c.revision++;c.status='待处理';c.note='已追加，原话和旧草稿保留。';
    if(/焦味|发热|起火|冒烟/.test(text)){c.scenario='safety';c.status='优先升级';}
    render();toast('模拟记录已追加。');return;
  }
  if(action==='choose-target'){
    modal('明确选择目标订单明细',`<p>下列是模拟候选，不会自动选择第一条。选择需与客户诉求核对。</p><label class="radio-card"><input type="radio" name="target" value="tee"><span>棉质宽松上衣 · M 码<small>DEMO-ORDER-101 / L1 · 演示服饰店 US / 演示仓 A</small></span></label><label class="radio-card"><input type="radio" name="target" value="usb"><span>USB-C 转接器 · 无服装尺码<small>DEMO-ORDER-102 / L1 · 演示数码店 US / 演示仓 A</small></span></label><label class="label spaced" for="link-reason">关联 / 修订理由</label><input id="link-reason" class="full" placeholder="记录如何核实目标商品"><div id="modal-error" class="field-error" role="alert"></div>`,button('取消','close-modal')+button('确认所选明细','link-target','primary'));return;
  }
  if(action==='link-target'){
    const selected=$('input[name=target]:checked'),reason=$('#link-reason').value.trim();
    if(!selected||!reason){$('#modal-error').textContent='显式选择目标行并填写关联理由。';return;}
    stashCase(c);c.linked=true;c.product=selected.value==='usb'?'USB-C 转接器 / DEMO-USB-C':'棉质宽松上衣 / DEMO-TEE-M';c.revision++;c.evidence=false;
    if(selected.value==='usb')c.scenario='conflict';
    else if(c.scenario==='conflict')c.scenario='normal';
    c.reviews.push({decision:'修订目标商品',text:c.product,reason,revision:c.revision});c.note='已确认目标行，需重新取证。';closeModal();render();return;
  }
  if(action==='case-evidence'){
    if(c.scenario==='failure'){c.note='取证失败（模拟超时），保留已知事实与人工输入。';render();return;}
    c.evidence=true;c.revision++;c.note='模拟证据已核查，付款、发货及退款语义分别展示。';render();return;
  }
  if(action==='generate'){
    c.generating=true;c.note='';const revision=c.revision;const original='感谢您反馈尺码问题。我们已记录您关于 M 码偏紧的描述，请补充衣物平铺尺寸和尺码标签照片。核对订单明细与适用政策后，将由人工确认后续处理方案。';
    render();setTimeout(()=>{c.generating=false;c.original=original;c.draft=original;c.draftRevision=revision;c.status='待审核';c.note='已生成模拟建议，尚未经人工采纳。';if(currentCase()===c)render();},350);return;
  }
  if(action==='save-review'||action==='return-review'||action==='escalate'){
    const text=$('#reply-draft').value.trim(),reason=$('#review-reason').value.trim();
    if(!reason||action==='save-review'&&!text){$('#case-error').textContent='请保留回复内容，并填写本次审核或升级理由。';return;}
    c.draft=text;c.reviews.push({decision:action==='save-review'?'保存并采纳':action==='escalate'?'升级人工':'退回修改',text,reason,revision:c.revision});
    c.status=action==='save-review'?'已处理':action==='escalate'?'已升级':'待处理';c.note='内部处理记录已保存（模拟），未发送或退款。';render();toast(c.note);return;
  }
  if(action==='original-draft'){modal('AI 原始草稿（模拟）',`<p>${esc(c.original)}</p><small>基于 caseRevision ${c.draftRevision}，人工文本单独保留。</small>`);return;}
  if(action==='case-history'){
    modal('案件处理历史（本次会话）',c.reviews.length?c.reviews.map(r=>`<div class="history-item"><b>${esc(r.decision)} · revision ${r.revision}</b><p>${esc(r.text)}</p><small>admin（模拟） · ${esc(r.reason)}</small></div>`).join(''):'<p>暂无人工决定。原始消息已保留，可在会话栏查看。</p>');return;
  }
  if(action==='policy-detail'){
    modal('政策原文与适用性 · 模拟 v1',`${tag('演示政策，不是已批准业务条款','amber')}<h3 class="spaced">尺码与描述处理 / §2 先核事实</h3><p>核对目标订单行、商品类别、页面尺码表和实测记录；缺证据时仅请求补充材料，不承诺处理资格。</p>${facts([['适用条件','演示服饰店 US / 服饰 / 简体中文'],['版本与状态','v1 · 模拟已发布 · 2026-09-01 起生效'],['责任人','模拟政策管理员'],['撤销 / 过期','当前不可使用版本不得继续引用']])}<p class="hint">3C 安全事项优先人工升级，不等待本条款或模型。</p>`);return;
  }
  if(action==='drill'){
    const denominator=el.dataset.drill==='denominator',before=el.dataset.drill==='before';state.drillCount=before?1:state.analysisMode==='historical'?11:12;state.drillWindow=before?'before':'after';
    modal(denominator?'分母构成 · 唯一实际发货批次':before?'前窗实收证据 · 1 件':`后窗实收证据 · ${state.drillCount} 件`,`<p>${denominator?'20 个成熟订单-SKU，每单唯一发货批次 2 件，共 40 件；不是投诉条数。':'仅 received 阶段计入实收；转 refunded 不再次加件。各事件位于本对象 [t0,t0+30天) 内。'}</p>${tag('模拟证据 · 完整教学金样 v1','blue')}<div class="table-scroll spaced"><table><thead><tr><th>事件 / 批次 ID</th><th>阶段</th><th>数量</th><th>对象 / 订单行</th><th>追溯</th></tr></thead><tbody>${denominator?Array.from({length:20},(_,i)=>`<tr><td>DEMO-SHIP-${i+1}</td><td>shipped</td><td>2 件</td><td>DEMO-ORDER-${101+i}/L1</td><td>${button('发货与原文','event-detail','small',`data-event="${i+1}"`)}</td></tr>`).join(''):receivedRows(state.drillCount,state.drillWindow)}</tbody></table></div>`);return;
  }
  if(action==='event-detail'){
    const n=Number(el.dataset.event);
    modal('原始事件追溯（模拟）',facts([['订单-SKU',`DEMO-ORDER-${100+n}/L1 / DEMO-TEE-M`],['实际发货批次',`DEMO-SHIP-${n} / 2 件`],['末次实际发货 t0',el.dataset.window==='before'?'2026-09-05 10:00 +08:00':'2026-09-25 10:00 +08:00'],['实收事件',el.dataset.window==='before'?'received / 1 件 / 2026-09-12 10:00 +08:00':'received / 1 件 / 2026-10-02 10:00 +08:00'],['后续退款','退款单独记录，不再加实收件数']])+`<hr><h3>客户反馈原文 · CLAIM</h3><p>“衣服实际尺寸与页面尺码表不一致，希望进一步核实。”</p><p class="hint">这是合成示例，保留投诉与实收事件的不同语义。</p>`,button('关闭','close-modal')+button(`返回 ${state.drillCount||12} 件构成`,'return-drill','primary'));return;
  }
  if(action==='return-drill'){modal(`${state.drillWindow==='before'?'前窗':'后窗'}实收证据 · ${state.drillCount||12} 件`,`<div class="table-scroll"><table><thead><tr><th>事件 ID</th><th>阶段</th><th>数量</th><th>订单行</th><th>追溯</th></tr></thead><tbody>${receivedRows(state.drillCount||12,state.drillWindow||'after')}</tbody></table></div>`);return;}
  if(action==='feedback'){modal('尺码主题 · 唯一反馈原文',`<p>8 / 12 条唯一反馈被标记为尺码主题；这是多标签分类，比例不代表退货率。</p>${Array.from({length:8},(_,i)=>`<div class="message"><small>DEMO-FEEDBACK-${i+1} · DEMO-ORDER-${101+i}/L1 · 模拟原文</small>“${i%2?'尺码表与实测尺寸存在差异。':'收到的 M 码偏紧，请协助核对尺寸。'}”</div>`).join('')}`);return;}
  if(action==='new-analysis'){
    modal('新建体验分析（模拟）',`<div class="form-grid"><label class="field">来源版本<select><option>完整教学金样 v1 · 模拟已回读</option></select></label><label class="field">店仓范围<select><option>演示服饰店 US / 演示仓 A</option></select></label><label class="field">前窗开始<input type="date" id="window-start" value="2026-09-01"></label><label class="field">相邻两窗边界<input type="date" id="window-middle" value="2026-09-21"></label><label class="field">后窗结束<input type="date" id="window-end" value="2026-10-11"></label><label class="field">截止时间<input type="date" id="window-cutoff" value="2026-11-15"></label></div><p class="hint">等长、不重叠半开窗，按实际末次发货入群。按钮仅模拟受理，不调用真实统计或模型。</p><div class="field-error" id="modal-error" role="alert"></div>`,button('取消','close-modal')+button('受理模拟分析','run-analysis','primary'));return;
  }
  if(action==='run-analysis'){
    const a=Date.parse($('#window-start').value),b=Date.parse($('#window-middle').value),d=Date.parse($('#window-end').value),t=Date.parse($('#window-cutoff').value);
    if(![a,b,d,t].every(Number.isFinite)||!(a<b&&b<d&&t>=d)||b-a!==d-b){$('#modal-error').textContent='请设置相邻等长两窗，并确保截止时间不早于后窗结束。';return;}
    if(a!==Date.parse('2026-09-01')||b!==Date.parse('2026-09-21')||d!==Date.parse('2026-10-11')||t!==Date.parse('2026-11-15')){state.analysisMode='immature';toast('自选窗口仅演示受限状态；金样结果对应固定演示窗口。');}
    else {state.analysisMode='complete';toast('模拟任务已完成，可钻取统计证据。');}
    closeModal();render();return;
  }
  if(action==='investigate'){state.investigation=$('#investigation-note').value.trim();if(!state.investigation){toast('先填写调查依据或待补材料。');return;}go('/after-sales/risks');toast('调查已保存至本次演示会话，风险仍需人工确认。');return;}
  if(action==='risk-evidence'){riskEvidence();return;}
  if(action==='to-risk'){if(route().path.startsWith('/replenishment'))state.returnTo='/replenishment';closeModal();go('/after-sales/risks');return;}
  if(action==='back-purchase'){state.returnTo=null;go('/replenishment');return;}
  if(action==='confirm-risk'){
    modal('人工确认质量风险（模拟）',`<p>仅对下列精确范围发布教学提醒。确认不会产生采购阻断、退款或商品安全认证。</p>${facts([['商品 / SKU','DEMO-PRODUCT-TEE / DEMO-TEE-M'],['单店 / 显式仓','DEMO-STORE-US / DEMO-WH-A'],['依据','分析 12/40、原文及人工调查'],['有效期','2026-11-16 至 2026-12-16（右端点不含）']])}<label class="label spaced" for="risk-reason">人工调查结论与限制</label><textarea id="risk-reason" rows="3" placeholder="说明已核证据、待补内容及为何提醒"></textarea><label class="check-line"><input id="risk-check" type="checkbox"><span>已核实本店仓的证据和教学消费范围，明确仅作风险提醒。</span></label><div id="modal-error" class="field-error" role="alert"></div>`,button('取消','close-modal')+button('确认此范围风险','commit-risk','primary'));return;
  }
  if(action==='commit-risk'){
    const reason=$('#risk-reason').value.trim();if(!reason||!$('#risk-check').checked){$('#modal-error').textContent='填写调查结论，并明确确认本店仓范围。';return;}
    state.risk='confirmed';state.riskReason=reason;state.riskHistory.push({version:state.riskVersion,status:'人工确认',reason});closeModal();render();toast('模拟风险已确认。补货参考量仍为 100 件。');return;
  }
  if(['reject-risk','close-risk','revoke-risk'].includes(action)){
    modal('记录风险决定（模拟）',`<label class="label" for="decision-reason">决定理由</label><textarea id="decision-reason" rows="3"></textarea><div id="modal-error" class="field-error" role="alert"></div>`,button('取消','close-modal')+button('保存决定','commit-decision','danger',`data-decision="${action}"`));return;
  }
  if(action==='commit-decision'){
    const reason=$('#decision-reason').value.trim();if(!reason){$('#modal-error').textContent='请填写决定理由，历史记录会保留。';return;}
    state.risk={'reject-risk':'rejected','close-risk':'closed','revoke-risk':'revoked'}[el.dataset.decision];state.riskHistory.push({version:state.riskVersion,status:riskNames[state.risk],reason});closeModal();render();return;
  }
  if(action==='new-risk-version'){state.riskVersion++;state.risk='suspected';state.riskHistory.push({version:state.riskVersion,status:'新建待调查版本',reason:'旧版本保持失效；新版本需重新调查及人工确认'});render();return;}
});
$('#modal').addEventListener('close',()=>{if(dialogReturn?.isConnected)dialogReturn.focus();});
window.addEventListener('hashchange',()=>render(true));
window.addEventListener('beforeunload',e=>{const c=currentCase();if(c?.draft&&c.draft!==(c.reviews.at(-1)?.text||c.original)){e.preventDefault();e.returnValue='';}});
render();
