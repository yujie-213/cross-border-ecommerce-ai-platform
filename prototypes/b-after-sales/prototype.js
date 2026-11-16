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
  const tee = {key:'tee', product:'棉质宽松上衣 · M 码', sku:'DEMO-TEE-M', productId:'DEMO-PRODUCT-TEE', line:'L1'};
  const shirt = {key:'shirt', product:'棉质长袖衬衫 · M 码', sku:'DEMO-SHIRT-M', productId:'DEMO-PRODUCT-SHIRT', line:'L2'};
  const socks = {key:'socks', product:'基础款棉袜', sku:'DEMO-SOCKS', productId:'DEMO-PRODUCT-SOCKS', line:'L2'};
  const make = (v) => ({revision:1, linked:false, targetKey:null, lines:[], evidence:false, draft:'', original:'', draftRevision:0, reviews:[], linkHistory:[], scenario:'normal', note:'', source:'erp', store:'演示服饰店 US', warehouse:'演示仓 A', order:null, ...v});
  state = {queue:'pending', search:'', sourceFilter:'erp', workMode:'normal', analysisMode:'complete', analysisProduct:'tee',
    risk:'suspected', riskVersion:1, riskReason:'', riskHistory:[], riskTab:'all',
    purchaseView:'single', purchaseFilter:'全部商品', quantity:'100', riskQuery:'ok', returnTo:null,
    cases:{
      apparel:make({id:'DEMO-TICKET-001', title:'上衣尺码与描述不符', product:tee.product, status:'待处理', linked:true, targetKey:'tee', lines:[tee,shirt], order:'DEMO-ORDER-101', evidence:true,
        messages:[{role:'客户主张',text:'收到的 M 码上衣比商品页面尺码表小，穿着偏紧。想确认如何处理。',time:'今天 09:12'}]}),
      multi:make({id:'DEMO-TICKET-002',title:'订单内有两件商品，退货目标待核实',product:'棉质宽松上衣 / 基础款棉袜',status:'待补证',order:'DEMO-ORDER-201',lines:[tee,socks],
        messages:[{role:'客户主张',text:'这次订单里有件商品不合适，希望退货。',time:'今天 08:55'}]}),
      missing:make({id:'DEMO-TICKET-003',title:'客户反馈缺少可靠订单信息',product:'商品尚未核实',status:'待补证',
        messages:[{role:'客户主张',text:'上次收到的东西有问题，可以帮我查一下吗？',time:'今天 08:40'}]}),
      review:make({id:'DEMO-TICKET-004',title:'包装破损，回复待审核',product:tee.product,status:'待审核',linked:true,targetKey:'tee',lines:[tee],order:'DEMO-ORDER-301',revision:3,evidence:true,
        messages:[{role:'客户主张',text:'外包装破了，衣服暂未发现破损，已补充包装照片。',time:'昨天 16:40'}],
        draft:'感谢您补充包装照片。我们已记录包装破损情况，请再确认衣物是否有损坏，便于人工核实后续处理方案。',original:'感谢您补充包装照片。我们已记录包装破损情况，请再确认衣物是否有损坏，便于人工核实后续处理方案。',draftRevision:3}),
      usb:make({id:'TEACHING-CASE-USB',title:'USB 转接器诉求待澄清',source:'teaching',store:'演示数码店 US',order:'TEACHING-ORDER-USB',product:'USB-C 转接器',linked:true,targetKey:'usb',evidence:true,status:'待补证',scenario:'conflict',
        lines:[{key:'usb',product:'USB-C 转接器',sku:'DEMO-USB-C',productId:'DEMO-PRODUCT-USB',line:'L1'}],messages:[{role:'客户主张',text:'这件商品尺码太小，我想换大一码。',time:'教学样例'}]}),
      safety:make({id:'TEACHING-CASE-SAFETY',title:'充电时异常发热及异味',source:'teaching',store:'演示数码店 US',order:'TEACHING-ORDER-SAFETY',product:'便携充电器',linked:true,targetKey:'charger',evidence:true,status:'优先升级',scenario:'safety',
        lines:[{key:'charger',product:'便携充电器',sku:'DEMO-CHARGER',productId:'DEMO-PRODUCT-CHARGER',line:'L1'}],messages:[{role:'客户主张',text:'充电时闻到焦味，外壳也很烫，是否还能继续使用？',time:'教学样例'}]})
    }
  };
}
resetState();
function addTeachingCase() {
  const c=state.cases.apparel;
  state.cases.teachingTee={...c,id:'TEACHING-CASE-TEE',source:'teaching',order:'TEACHING-ORDER-101',messages:c.messages.map(m=>({...m})),reviews:[],linkHistory:[]};
}
addTeachingCase();
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
function modeControl() { return ''; }
function demoLab() {
  const path=route().path, c=currentCase();
  const select=(id,label,value,options)=>`<label class="field" for="demo-${id}">${label}</label><select id="demo-${id}" data-control="${id}">${options.map(([v,n])=>`<option value="${v}" ${v===value?'selected':''}>${n}</option>`).join('')}</select>`;
  modal('教学与异常演示', `<p>此处仅切换原型测试状态，与正常业务操作分开。全部为合成数据，不会修改 ERP。</p><div class="button-row">${link('USB 尺码冲突案例','/after-sales/cases/usb')}${link('安全升级案例','/after-sales/cases/safety')}${button('创建内部教学案件','new-case')}${button('重置全部演示','reset')}</div><hr>`+
    (path==='/after-sales'?select('workMode','工作区状态',state.workMode,[['normal','正常队列'],['empty','空队列'],['restricted','无权访问']]):'')+
    (c?select('caseScenario','案件情形',c.scenario,[['normal','正常处理'],['conflict','商品诉求冲突'],['no-policy','无适用政策'],['failure','取证 / AI 失败'],['safety','安全升级']]):'')+
    (path.includes('/analyses')?select('analysisMode','分析状态',state.analysisMode,[['complete','完整教学样例'],['immature','观察尚未完成'],['insufficient','可比较样本不足'],['failed','AI 分析失败'],['historical','历史版本']]):'')+
    (path.includes('/risks')?select('riskStatus','生命周期',state.risk,Object.entries(riskNames)):'')+
    (path.startsWith('/replenishment')?select('riskQuery','风险查询',state.riskQuery,[['ok','完整查询'],['failure','查询失败'],['wrong-store','错店范围'],['normal-mode','正常 ERP 模式排除教学风险']]):''));
}
function sourceLabel(c) { return c.source==='erp'?'ERP 已有工单 · 模拟':'中台内部教学案件'; }
function selectedLine(c) { return c.lines.find(l=>l.key===c.targetKey); }

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
  const all=Object.entries(state.cases),c=all.filter(([,v])=>state.sourceFilter==='all'||v.source===state.sourceFilter);
  const queues={pending:['待处理','优先升级'],evidence:['待补证'],review:['待审核'],handled:['已处理','已升级']};
  const filtered=c.filter(([,v])=>queues[state.queue].includes(v.status)&&`${v.title} ${v.product} ${v.id} ${v.order||''}`.toLowerCase().includes(state.search.toLowerCase()));
  const safety=c.find(([,v])=>v.status==='优先升级');
  return head('售后工作台','从已有售后记录继续工作，优先处理需要判断和补证的事项。')+
    `<div class="scope"><span>${tag('本页记录均为模拟','blue')}</span><label>记录来源 <select id="source-filter"><option value="erp" ${state.sourceFilter==='erp'?'selected':''}>ERP 已有工单（模拟）</option><option value="teaching" ${state.sourceFilter==='teaching'?'selected':''}>中台教学案件</option><option value="all" ${state.sourceFilter==='all'?'selected':''}>全部来源（分别标识）</option></select></label></div>`+
    (state.workMode==='restricted'?notice('当前范围不可访问','请联系管理员核对授权。受限案件、计数和原文均不展示。'):
    `${safety&&state.workMode!=='empty'?`<div class="notice red split"><div><strong>优先处理 · ${esc(safety[1].title)}</strong><p>安全反馈直接转人工核实。</p></div>${link('立即核实 →','/after-sales/cases/'+safety[0],'small')}</div>`:''}<div class="columns"><section class="panel"><div class="tabs" role="group" aria-label="案件队列">${Object.entries({pending:'待处理',evidence:'待补证',review:'待审核',handled:'处理记录'}).map(([k,n])=>`<button class="tab ${state.queue===k?'active':''}" data-queue="${k}" aria-pressed="${state.queue===k}">${n}<span class="count">${state.workMode==='empty'?0:c.filter(([,v])=>queues[k].includes(v.status)).length}</span></button>`).join('')}</div><div class="toolbar"><label>搜索售后记录 <input id="case-search" value="${esc(state.search)}" placeholder="工单 / 订单 / 商品 / 问题" autocomplete="off"></label></div>${state.workMode==='empty'||!filtered.length?'<div class="empty"><h2>当前队列没有售后记录</h2><p>可调整来源、筛选或查看其他处理队列。</p></div>':`<div class="table-scroll"><table><thead><tr><th>售后问题 / 商品</th><th>来源 / 订单</th><th>处理状态 / 下一步</th></tr></thead><tbody>${filtered.map(([id,v])=>`<tr><td><a href="#/after-sales/cases/${id}"><strong>${esc(v.title)}</strong></a><small>${esc(v.product)}</small></td><td>${tag(sourceLabel(v),'blue')}<small>${esc(v.store)}</small><small>${esc(v.order||'订单信息待补充')}</small></td><td>${tag(v.status,v.status==='优先升级'?'red':'amber')}<small>${v.linked?'查看事实和处理建议':v.lines.length?'核实本订单目标商品':'补充订单或可核查凭证'}</small></td></tr>`).join('')}</tbody></table></div>`}<div class="table-foot"><span>仅展示当前来源与权限范围</span><span>模拟处理结果仅在本次页面保留</span></div></section><aside class="side-stack">${panel('退货异常提醒','<strong>棉质宽松上衣</strong><p class="hint">本期退货率 30%，较上期上升 27.5 个百分点。优先核查尺码反馈。</p><div class="spaced">'+link('查看异常分析 →','/after-sales/analyses','small')+'</div>','中台教学样例')}${panel('商品评价与客户反馈','<p>商品评价用于体验分析；有可靠订单和明细时才进一步关联个案。</p><div class="spaced">'+link('查看商品反馈 →','/after-sales/feedback','small')+'</div>','本原型使用中台模拟资料')}</aside></div>`);
}
function feedbackPage() {
  return `<a class="back" href="#/after-sales">← 返回售后工作台</a>`+head('商品评价与客户反馈','先看商品反馈，再按可靠关联深入分析。')+
    notice('中台模拟反馈 · 未连接 ERP 评价接口','历史资料曾读到 ERP 评价样本；本页不使用该批业务数据，订单与商品的完整关联仍需核验。','blue')+
    panel('商品评价',`<div class="message"><small>中台教学评价 · 演示服饰店 US</small><b>棉质宽松上衣 · DEMO-TEE-M</b><p>“收到的 M 码比页面尺码表小，穿着偏紧。”</p></div>${facts([['商品关联','教学 Listing / 商品 / SKU 已明确'],['订单关联','未知；不能据此查付款或归入某订单退货'],['用途','反馈主题分析；不作为退货件数']])}<div class="spaced">${link('分析该商品体验 →','/after-sales/analyses?from=feedback','primary')}</div>`)+
    panel('订单级客户反馈',`<p>“这次订单有件商品不合适，希望退货。”</p>${facts([['订单关联','DEMO-ORDER-201 · 两件商品'],['目标商品','尚未明确，不能复制归因到每个商品']])}<div class="spaced">${link('核实关联售后记录 →','/after-sales/cases/multi')}</div>`,'模拟：仅此反馈有明确订单关联');
}
function currentCase() { return state.cases[route().path.split('/')[3]]; }
function casePage(id) {
  const c=state.cases[id]; if(!c)return '<div class="empty"><h1>案件不可访问</h1></div>';
  const target=selectedLine(c),stale=!!c.draft&&c.draftRevision!==c.revision;
  const blocked=!c.linked||!c.evidence||['no-policy','failure','conflict','safety'].includes(c.scenario);
  const warn=c.scenario==='safety'?notice('安全信号 · 优先人工升级','先建议暂停使用并转专人核实，不提供拆机指引，不宣告商品安全。','red'):c.scenario==='conflict'?notice('诉求与已核实属性冲突','USB 转接器没有服装尺码。保留原话，请核实客户指的是哪件商品及具体问题；AI 不代选。'):'';
  const garment=['tee','shirt'].includes(c.targetKey);
  const gaps=!c.linked?(c.lines.length?'已找到订单，但无法确定反馈针对哪件商品。请向客户核实后选择本订单明细。':'没有可靠订单或商品凭证。请补充完整订单号、店铺和可核查材料，系统不会按文字猜测商品。'):c.scenario==='no-policy'?'未找到适用政策，请转人工核实处理资格。':c.scenario==='failure'?'业务资料核查失败，请稍后重试或保留人工记录，不能推导为无付款。':garment?'尚缺衣物平铺尺寸、标签照片及当时页面尺码表，暂不能确定问题原因。':'尚缺问题照片与具体情况，请补充可核查材料，暂不能确定原因。';
  return `<a class="back" href="#/after-sales?queue=${state.queue}">← 返回原案件队列</a>`+head(c.title,'客户问题、业务事实与人工决定分别留存。',button('查看处理历史','case-history'))+
    `<div class="case-meta">${tag(c.status,'amber')}${tag(sourceLabel(c),'blue')}<span>${esc(c.store)}</span><span>${esc(c.order||'订单待核实')}</span></div>`+warn+
    `<div class="case-grid">${panel('客户反馈了什么',c.messages.map(m=>`<div class="message ${m.role==='内部澄清'?'internal':''}"><small>${esc(m.role)} · ${esc(m.time)}</small>${esc(m.text)}</div>`).join('')+`<details><summary>补充客户信息或内部记录</summary><div class="spaced"><label class="label" for="new-message">追加客户信息 / 内部澄清</label><textarea id="new-message" rows="3"></textarea><label class="label spaced" for="message-kind">信息类型</label><select id="message-kind"><option>客户主张</option><option>内部澄清</option></select><div class="spaced">${button('追加记录','append-message')}</div></div></details>`)}
    ${panel('系统核实的业务事实',(c.linked&&target?`<div class="notice green"><strong>已核实关联商品</strong><p>受信来源中的订单和商品明细已匹配，无需重复选择。</p></div>${facts([['商品',esc(target.product)],['SKU',esc(target.sku)],['订单 / 明细',esc(c.order)+' / '+esc(target.line)],['店铺 / 仓库',esc(c.store)+' / '+esc(c.warehouse)]])}<details class="spaced"><summary>关联依据与人工纠正</summary><p class="hint">模拟服务端已核对来源租户、店铺、商品 ID、SKU 和订单明细。纠正只在当前订单已核实明细内进行，原关联和原因留存。</p><div class="spaced">${button('纠正商品关联','correct-target','small')}</div></details>`:
      notice('商品关联待核实',gaps)+(c.lines.length?button('核实订单内商品','choose-target','primary'):'')+`<p class="hint">可在客户反馈区记录澄清或升级人工。</p>`)+
      `<hr><h3>交易与处理状态</h3>${c.scenario==='failure'?notice('业务资料核查失败','部分资料暂不可用，已保存事实仍保留；请稍后核查。'):c.evidence?facts([['付款','已付款（模拟凭证）'],['履约','已发货；签收情况待核实'],[c.source==='erp'?'ERP 售后状态':'教学案件状态','处理中；没有退款执行记录']]):'<p class="hint">尚无可核查交易事实，客户主张不能替代业务凭证。</p>'}<details class="spaced"><summary>查看取证与来源明细</summary><p class="hint">${esc(c.id)} · ${c.source==='erp'?'模拟 ERP 工单及订单回读':'中台独立教学案件'} · 本次页面模拟观测</p><div class="spaced">${button('重新核查业务资料','case-evidence','',c.linked?'':'disabled')}</div></details>`, '以下为原型模拟的核查结果')}
    ${panel('AI 处理建议与人工审核',(stale?notice('内容已更新 · 草稿已过期','请依据最新信息重新生成后再审核。'):'')+
      `${c.note?notice('操作反馈',esc(c.note),'blue'):''}<div class="ai-block"><b>AI 建议 · 模拟</b><p>${blocked?'目前不宜生成具体商品处理方案。请先处理下列缺口或交由人工。':c.id==='DEMO-TICKET-004'?'先确认衣物本身是否损坏，包装照片不能直接证明商品破损。':garment?'先补充实测尺寸与标签照片，核对购买时的尺码表，再由人工决定处理方向。':'先补充具体问题与照片，核对商品信息，再由人工决定处理方向。'}</p><p class="hint">${blocked?esc(gaps):'依据：已核实订单商品、客户原话及适用的补证政策。客户主张尚不能证明商品缺陷。'}</p></div><details class="spaced"><summary>查看适用政策与原文</summary>${c.scenario==='no-policy'?notice('无适用政策','仅可澄清、补证或转人工，不能承诺退款资格。'):c.evidence?`<p class="hint">尺码与描述处理 · 模拟已发布政策，适用于演示服饰店 US 服饰商品；先补证，不承诺退款。</p>${button('查看政策原文与适用条件','policy-detail','small')}`:'<p>待核实商品与业务日期后匹配。</p>'}</details><div class="spaced">${button(c.generating?'正在整理建议…':'生成回复草稿（模拟）','generate','primary',blocked||c.generating?'disabled':'')}</div><label class="label spaced" for="reply-draft">人工回复稿</label><textarea id="reply-draft" rows="5" placeholder="审核 AI 草稿或记录人工澄清">${esc(c.draft)}</textarea>${c.original?'<button class="text-button" data-action="original-draft">查看 AI 原稿（模拟）</button>':''}<label class="label spaced" for="review-reason">审核 / 升级理由</label><textarea id="review-reason" rows="2"></textarea><div class="field-error" id="case-error" role="alert"></div><div class="button-row">${button('保存并采纳','save-review','primary',!c.draft||stale||blocked?'disabled':'')}${button('退回修改','return-review')}${button('升级人工','escalate','danger')}</div><p class="hint">人工决定仅保存为内部记录，不发送客户消息、不执行退款。</p>`, '重要决定由业务人员审核')}
    </div>`;
}
function analysesPage() {
  const unknown=['immature','insufficient'].includes(state.analysisMode),historical=state.analysisMode==='historical',failed=state.analysisMode==='failed',normal=state.analysisProduct==='socks';
  const count=historical?11:12,rate=historical?'27.5%':'30%',change=historical?'25':'27.5';
  return (route().query.get('from')==='feedback'?'<a class="back" href="#/after-sales/feedback">← 返回商品反馈</a>':'')+
    head('客户体验与退货分析','优先找到退货异常、客户关心的问题和下一步处理方向。',button('调整分析范围','new-analysis'))+
    `<div class="scope"><span>${tag('中台教学资料 · 模拟','blue')}</span><span>演示服饰店 US · 演示仓 A</span><span>本期与上期同口径比较</span></div>`+
    (historical?notice('正在查看历史分析','此版本尚未计入迟到的 1 件退货，旧结论保留；当前版本可在教学演示中切换。','blue'):'')+
    `<section class="panel"><div class="panel-head"><div><h2>哪些商品需要优先关注？</h2><small>退货情况与异常优先级</small></div></div><div class="table-scroll"><table><thead><tr><th>商品</th><th>本期退货率</th><th>上期退货率</th><th>变化幅度</th><th>建议关注程度</th></tr></thead><tbody><tr class="highlight"><td><button class="text-button" data-action="analysis-product" data-product="tee">棉质宽松上衣</button><small>DEMO-TEE-M</small></td><td><strong>${unknown?'暂无法判断':rate}</strong></td><td>2.5%</td><td>${unknown?'暂无法比较':'上升 '+change+' 个百分点'}</td><td>${tag(unknown?'需要补充数据':'优先调查','amber')}</td></tr><tr><td><button class="text-button" data-action="analysis-product" data-product="socks">基础款棉袜</button><small>正常对照商品</small></td><td>${unknown?'暂无法判断':'2.5%'}</td><td>2.5%</td><td>${unknown?'暂无法比较':'无变化'}</td><td>${tag(unknown?'需要补充数据':'常规观察',unknown?'amber':'teal')}</td></tr></tbody></table></div></section>`+
    `<section class="panel section-gap"><div class="panel-head"><div><h2>${normal?(unknown?'基础款棉袜 · 数据不足，暂时无法判断':'基础款棉袜 · 退货情况平稳'):'棉质宽松上衣 · '+(unknown?'数据不足，暂时无法判断':'退货明显上升，建议优先调查尺码问题')}</h2><small>${normal?'正常对照，不代表商品没有问题':'异常是调查线索，不是商品缺陷认定'}</small></div>${tag('AI 分析 · 模拟','blue')}</div><div class="panel-body">`+
    (unknown?notice('数据不足，暂时无法判断',state.analysisMode==='immature'?(state.customWindow?'自选范围尚未取得完整可比较数据。请补齐来源、发货和退货证据后重新分析。':'这批订单还未完成规定的退货观察期，目前只有 29 天。请等待观察完成后重新分析。'):'可比较的成熟订单商品组合只有 19 个，未达到最低样本要求。请补充完整数据后重新分析。'):'')+
    (failed?notice('AI 分析暂不可用','退货统计仍可查看。请稍后重试 AI 分析，或由运营人员查阅原文，不用正常结论填补失败。'):'')+
    `<div class="two-col"><div><h3>客户主要反馈什么？</h3><div class="ai-block"><p>${failed?'本次反馈总结未生成。':normal?'反馈较分散，当前样本没有支持某一问题集中上升的证据。':'尺码偏紧、实测尺寸与页面说明不一致是主要反馈，另有少量包装与物流问题。'}</p>${!failed&&!normal?'<p class="hint">8 / 12 条唯一反馈涉及尺码；可多主题归类，不是退货率。</p>':''}</div><div class="button-row spaced">${button('查看评价与反馈原文','feedback')}${button('查看相关售后记录','related-tickets')}</div>${!normal&&!failed?button('修订反馈主题','edit-theme','small'):''}<h3 class="spaced">已核实的事实</h3><p>${normal?'同口径退货情况为 1/40 → 1/40。':`本期 ${count} 件退货已实际收到，对应同批订单实际发货 40 件；上期为 1/40。`}</p><p class="hint">评价和工单用于理解问题，不计入退货件数。</p><div class="button-row spaced">${button('查看本期退货证据','analysis-returns')}${button('查看上期退货证据','drill','', 'data-drill="before"')}</div></div><div><h3>可能原因与待核实信息</h3><div class="ai-block"><p>${failed?'AI 原因分析未生成，请查阅证据后人工判断。':normal?'暂不支持直接创建尺码质量结论。继续观察后续反馈。':'可能与尺码表版本或实测尺寸偏差有关；流量人群和批次差异也可能影响退货。以上均为假设。'}</p><p class="hint">还需购买时页面版本、平铺实测和批次资料；不能据此认定质量缺陷。</p></div><h3 class="spaced">建议下一步</h3><p>${unknown?'先完成观察或补齐样本，再判断变化；仍可记录人工调查。':normal?'持续观察，出现集中反馈时再核查。':'核对尺码表与实物，抽查相关批次，并联系运营检查商品描述。'}</p><label class="label spaced" for="investigation-note">调查记录</label><textarea id="investigation-note" rows="3" placeholder="记录已核事实、待补材料及下一步">${esc(state.investigation||'')}</textarea><div class="spaced">${button('创建调查','investigate','primary',normal?'disabled':'')}</div><p class="hint">创建后仍为待调查线索，风险发布需要人工确认。</p></div></div>`+
    `<details class="section-gap" id="metric-details"><summary>指标说明 / 数据依据 / 高级详情</summary><div class="spaced">${facts([['主指标','同一发货完成群组：实际收到退货件数 ÷ 实际发货件数'],['本期构成',normal?'1 / 40 件':count+' / 40 件'],['上期构成','1 / 40 件'],['比较窗口','上期 [09.01,09.21) / 本期 [09.21,10.11) · Asia/Shanghai'],['成熟度','每个订单-SKU在末次实际发货t0后观察30×24小时'],['最低样本','每窗至少20成熟订单-SKU及20实际发货件'],['异常阈值','未舍入差值 ≥10个百分点且本期实收 ≥3件'],['来源与规则','完整教学金样 v1 / teaching-return-rules-v1'],['去重与覆盖','同来源事件去重；同键冲突、缺页、不可归属等不静默剔除，受影响率UNKNOWN']])}<div class="spaced">${button('查看实际发货构成','drill','', 'data-drill="denominator"')}</div><p class="hint">申请16 / 有效授权14 / 实收12 / 已退款8；期外2 / 已取消2（当前上衣教学样例）。阶段分开，退款不重复加退货件数。主题以唯一反馈为分母，多标签可重叠；不混用ERP与教学分子分母。历史版11/40与当前12/40分别留存。</p></div></details></div></section>`;
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
  const body = path==='/home'?homePage():path==='/after-sales'?workbench():path==='/after-sales/feedback'?feedbackPage():path.startsWith('/after-sales/cases/')?casePage(path.split('/')[3]):path.startsWith('/after-sales/analyses')?analysesPage():path.startsWith('/after-sales/risks')?risksPage():path.startsWith('/after-sales/knowledge')?knowledgePage():path.startsWith('/replenishment')?purchasePage():`<div class="empty"><h1>此原型页面不存在</h1>${link('回到平台首页','/home')}</div>`;
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
  return Array.from({length:n},(_,i)=>`<tr><td class="mono">DEMO-RET-${window==='before'?'B':'A'}-${String(i+1).padStart(2,'0')}</td><td>received</td><td>1 件</td><td class="mono">TEACHING-ORDER-${(window==='before'?1:101)+i}/${state.drillProduct==='socks'?'L2':'L1'}</td><td>${button('发货与原文','event-detail','small',`data-event="${i+1}" data-window="${window}"`)}</td></tr>`).join('');
}
function riskEvidence() {
  const fromPurchase=route().path.startsWith('/replenishment');
  modal('质量风险证据',`${tag('全部为合成样例','blue')}<div class="spaced">${facts([['当前状态',state.riskQuery==='failure'&&fromPurchase?'未核实（模拟查询失败）':riskNames[state.risk]],['风险范围','DEMO-PRODUCT-TEE / DEMO-TEE-M / DEMO-STORE-US / DEMO-WH-A'],['来源','教学金样 v1 · 授权教学消费'],['统计证据','上期 2.5%；本期 30%；上升 27.5 个百分点'],['调查结论',esc(state.investigation||'尺码一致性待补充实测，尚未宣告缺陷')]])}</div>${notice('历史与当前分开','历史报告引用的风险版本保留；当前失效或查询失败时不能沿用旧有效状态。')}<p>采购摘要只显示商品与调查证据，不带客户身份。参考补货量始终 100 件。</p>`,button('返回原页面','close-modal')+button('进入质量风险详情','to-risk','primary'));
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
  else if(key==='riskStatus'){state.risk=e.target.value;state.riskHistory.push({version:state.riskVersion,status:riskNames[state.risk],reason:'教学演示状态切换；历史版本保留'});render();}
  else if(key){if(key==='analysisMode')state.customWindow=false;state[key]=e.target.value;render();}
  if(e.target.id==='purchase-filter')state.purchaseFilter=e.target.value;
  if(e.target.id==='source-filter'){state.sourceFilter=e.target.value;render();}
});
document.addEventListener('click',e=>{
  if(e.target.closest('a.skip')) {e.preventDefault();$('#main').focus();return;}
  const anchor=e.target.closest('a[href^="#/"]');
  if(anchor && $('#modal').open) closeModal();
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
  if(action==='demo-lab'){demoLab();return;}
  if(action==='analysis-product'){state.analysisProduct=el.dataset.product;render();return;}
  if(action==='analysis-returns'){el.dataset.drill=state.analysisProduct==='socks'?'socks':'received';el.dataset.action='drill';el.click();return;}
  if(action==='related-tickets'){modal('相关售后记录 · 模拟',state.analysisProduct==='socks'?'<p>当前样例没有可确认归属于棉袜的售后工单，不能从多商品订单复制归因。</p>':`<p>以下教学案件与本商品身份明确匹配；不作为退货率分子。</p>${link('打开上衣教学案件','/after-sales/cases/teachingTee')}`);return;}
  if(action==='edit-theme'){modal('修订反馈主题（模拟）',`<p>保留原AI分类与人工修订理由，不改变退货数量。</p><label class="field">主题<select id="theme-name"><option>尺码</option><option>描述不符</option><option>待核实</option></select></label><label class="label spaced" for="theme-reason">修订理由</label><textarea id="theme-reason"></textarea><div id="modal-error" role="alert"></div>`,button('取消','close-modal')+button('保存主题修订','save-theme','primary'));return;}
  if(action==='save-theme'){if(!$('#theme-reason').value.trim()){$('#modal-error').textContent='请填写修订依据。';return;}state.themeHistory={theme:$('#theme-name').value,reason:$('#theme-reason').value};closeModal();toast('已保存主题修订（模拟），原分类保留在反馈详情。');return;}
  if(action==='close-modal'){closeModal();return;}
  if(action==='leave-case'){closeModal();go(state.pendingNavigate);return;}
  if(action==='reset'){resetState();addTeachingCase();render();toast('演示数据已重置；全部操作仍为模拟。');return;}
  if(action==='new-case'){
    modal('创建内部教学案件（模拟）',`<label class="label" for="case-title">客户问题标题</label><input id="case-title" class="full" maxlength="120" placeholder="例如：收到商品后发现包装破损"><label class="label spaced" for="case-body">客户原话</label><textarea id="case-body" rows="4" maxlength="2000"></textarea><p class="hint">允许尚无订单与 SKU。此操作仅增加本次页面会话内的合成演示案件。</p><div id="modal-error" class="field-error" role="alert"></div>`,button('取消','close-modal')+button('创建模拟案件','create-case','primary'));return;
  }
  if(action==='create-case'){
    const title=$('#case-title').value.trim(),body=$('#case-body').value.trim();
    if(!title||!body){$('#modal-error').textContent='请填写标题与客户原话。';return;}
    const id='local'+Object.keys(state.cases).length;
    state.cases[id]={source:'teaching',store:'演示服饰店 US',warehouse:'演示仓 A',order:null,lines:[],targetKey:null,linkHistory:[],id:'TEACHING-CASE-'+id,title,product:'尚未确认',status:'待处理',revision:1,linked:false,messages:[{role:'客户主张',text:body,time:'本次会话'}],draft:'',original:'',draftRevision:0,reviews:[],evidence:false,scenario:'normal',note:''};
    closeModal();go('/after-sales/cases/'+id);return;
  }
  if(action==='append-message'){
    const text=$('#new-message').value.trim();if(!text){toast('先填写需要追加的信息。');return;}
    stashCase(c);c.messages.push({role:$('#message-kind').value,text,time:'本次会话'});c.revision++;c.status='待处理';c.note='已追加，原话和旧草稿保留。';
    if(/焦味|发热|起火|冒烟/.test(text)){c.scenario='safety';c.status='优先升级';}
    render();toast('模拟记录已追加。');return;
  }
  if(action==='choose-target'||action==='correct-target'){
    if(!c.lines.length){toast('没有可靠订单明细，请先补证。');return;}
    state.correcting=action==='correct-target';
    modal(state.correcting?'纠正已有商品关联':'核实本订单目标商品',`<p>${esc(c.order)} · ${esc(c.store)}。仅展示此订单已核实明细，不包含其他店铺或订单。</p>${c.lines.map(l=>`<label class="radio-card"><input type="radio" name="target" value="${l.key}"><span>${esc(l.product)}<small>${esc(l.sku)} · ${esc(l.line)} ${l.key===c.targetKey?'· 当前关联':''}</small></span></label>`).join('')}${state.correcting?'<label class="label spaced" for="link-reason">修订原因（必填）</label><textarea id="link-reason" placeholder="说明原关联为何有误及核实依据"></textarea>':'<p class="hint">向客户核实后确认即可，首次确认不必填写原因。</p>'}<div id="modal-error" class="field-error" role="alert"></div>`,button('取消','close-modal')+button('确认所选商品','link-target','primary'));return;
  }
  if(action==='link-target'){
    const selected=$('input[name=target]:checked'),reason=$('#link-reason')?.value.trim()||'';
    if(!selected){$('#modal-error').textContent='请选择客户已核实的商品明细。';return;}
    if(state.correcting&&(!reason||selected.value===c.targetKey)){$('#modal-error').textContent=selected.value===c.targetKey?'所选仍是原商品，无需修订。':'纠正已有商品关联必须填写修订原因。';return;}
    const target=c.lines.find(l=>l.key===selected.value);if(!target)return;
    const original=selectedLine(c);stashCase(c);c.linked=true;c.targetKey=target.key;c.product=target.product;c.revision++;c.evidence=true;
    const decision=state.correcting?'人工纠正商品关联':'首次核实目标商品';
    c.linkHistory.push({original:original?.product||'订单级反馈，未定位商品',current:target.product,reason,revision:c.revision});
    c.reviews.push({decision,text:(original?.product||'未定位商品')+' → '+target.product,reason:reason||'首次确认，无强制理由',revision:c.revision});
    c.note=state.correcting?'商品关联已纠正，原关联和修订原因已保留。':'目标商品已核实，可继续查看建议。';closeModal();render();return;
  }
  if(action==='case-evidence'){
    if(c.scenario==='failure'){c.note='取证失败（模拟超时），保留已知事实与人工输入。';render();return;}
    c.evidence=true;c.revision++;c.note='模拟证据已核查，付款、发货及退款语义分别展示。';render();return;
  }
  if(action==='generate'){
    c.generating=true;c.note='';const revision=c.revision;const original=c.id==='DEMO-TICKET-004'?'感谢您补充包装照片。请进一步确认衣物是否损坏，核实后由人工确认处理方案。':`感谢您反馈${esc(selectedLine(c)?.product||'商品')}的问题。我们已记录您的描述，请补充商品照片及可核查材料。核对订单明细与适用政策后，由人工确认后续处理方案。`;
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
    const denominator=el.dataset.drill==='denominator',before=el.dataset.drill==='before';state.drillProduct=el.dataset.drill==='socks'?'socks':state.analysisProduct;state.drillCount=before||state.drillProduct==='socks'?1:state.analysisMode==='historical'?11:12;state.drillWindow=before?'before':'after';state.drillDenominator=denominator;
    modal(denominator?'实际发货构成':before?'上期退货收货证据 · 1 件':`本期退货收货证据 · ${state.drillCount} 件`,`<p>${denominator?'20 个成熟订单-SKU，每单唯一发货批次 2 件，共 40 件；不是投诉条数。':'仅 received 阶段计入实收；转 refunded 不再次加件。各事件位于本对象 [t0,t0+30天) 内。'}</p>${tag('模拟证据 · 完整教学金样 v1','blue')}<div class="table-scroll spaced"><table><thead><tr><th>事件 / 批次 ID</th><th>阶段</th><th>数量</th><th>对象 / 订单行</th><th>追溯</th></tr></thead><tbody>${denominator?Array.from({length:20},(_,i)=>`<tr><td>DEMO-SHIP-${i+1}</td><td>shipped</td><td>2 件</td><td>TEACHING-ORDER-${101+i}/${state.drillProduct==='socks'?'L2':'L1'}</td><td>${button('发货与原文','event-detail','small',`data-event="${i+1}"`)}</td></tr>`).join(''):receivedRows(state.drillCount,state.drillWindow)}</tbody></table></div>`);return;
  }
  if(action==='event-detail'){
    const n=Number(el.dataset.event);
    modal('原始事件追溯（模拟）',facts([['订单-SKU',`TEACHING-ORDER-${(el.dataset.window==='before'?0:100)+n}/${state.drillProduct==='socks'?'L2':'L1'} / ${state.drillProduct==='socks'?'DEMO-SOCKS':'DEMO-TEE-M'}`],['实际发货批次',`DEMO-SHIP-${n} / 2 件`],['末次实际发货 t0',el.dataset.window==='before'?'2026-09-05 10:00 +08:00':'2026-09-25 10:00 +08:00'],['实收事件',state.drillDenominator&&n>(state.drillProduct==='socks'?1:state.analysisMode==='historical'?11:12)?'此发货明细在观察期内无实收退货事件':el.dataset.window==='before'?'received / 1 件 / 2026-09-12 10:00 +08:00':'received / 1 件 / 2026-10-02 10:00 +08:00'],['后续退款','退款单独记录，不再加实收件数']])+`<hr><h3>客户反馈原文 · CLAIM</h3><p>${state.drillDenominator&&n>(state.drillProduct==='socks'?1:12)?'此明细无已关联反馈原文，不能补造客户问题。':state.drillProduct==='socks'?'“袜子包装破损，希望核实。”':'“衣服实际尺寸与页面尺码表不一致，希望进一步核实。”'}</p><p class="hint">这是合成示例，保留投诉与实收事件的不同语义。</p>`,button('关闭','close-modal')+button(`返回 ${state.drillCount||12} 件构成`,'return-drill','primary'));return;
  }
  if(action==='return-drill'){modal(`${state.drillWindow==='before'?'前窗':'后窗'}实收证据 · ${state.drillCount||12} 件`,`<div class="table-scroll"><table><thead><tr><th>事件 ID</th><th>阶段</th><th>数量</th><th>订单行</th><th>追溯</th></tr></thead><tbody>${receivedRows(state.drillCount||12,state.drillWindow||'after')}</tbody></table></div>`);return;}
  if(action==='feedback'){
    modal('商品评价与反馈依据 · 中台模拟',`<p>未连接 ERP 评价接口。评价可有商品而没有订单；订单级反馈未定位商品时不计入商品主题。评价与工单数不构成退货数量。</p>${state.themeHistory?`<div class="notice"><b>人工主题修订：${esc(state.themeHistory.theme)}</b><p>${esc(state.themeHistory.reason)}；原AI尺码分类保留。</p></div>`:''}${state.analysisProduct==='socks'?'<div class="message">中台模拟评价：袜子包装破损。商品已关联，订单未知。</div>':`<p>12 条唯一反馈中，8 条涉及尺码（多标签）。以下为可展开的原文样例：</p>${Array.from({length:8},(_,i)=>`<div class="message"><small>中台教学反馈 ${i+1} · ${i%2?'教学工单 / TEACHING-ORDER-'+(101+i)+'/L1':'商品评价 / DEMO-TEE-M · 订单未知'}</small>“${i%2?'尺码表与实测尺寸存在差异。':'收到的 M 码偏紧，请协助核对尺寸。'}”</div>`).join('')}`}`);return;
  }
  if(action==='new-analysis'){
    modal('新建体验分析（模拟）',`<div class="form-grid"><label class="field">来源版本<select><option>完整教学金样 v1 · 模拟已回读</option></select></label><label class="field">店仓范围<select><option>演示服饰店 US / 演示仓 A</option></select></label><label class="field">前窗开始<input type="date" id="window-start" value="2026-09-01"></label><label class="field">相邻两窗边界<input type="date" id="window-middle" value="2026-09-21"></label><label class="field">后窗结束<input type="date" id="window-end" value="2026-10-11"></label><label class="field">截止时间<input type="date" id="window-cutoff" value="2026-11-15"></label></div><p class="hint">等长、不重叠半开窗，按实际末次发货入群。按钮仅模拟受理，不调用真实统计或模型。</p><div class="field-error" id="modal-error" role="alert"></div>`,button('取消','close-modal')+button('受理模拟分析','run-analysis','primary'));return;
  }
  if(action==='run-analysis'){
    const a=Date.parse($('#window-start').value),b=Date.parse($('#window-middle').value),d=Date.parse($('#window-end').value),t=Date.parse($('#window-cutoff').value);
    if(![a,b,d,t].every(Number.isFinite)||!(a<b&&b<d&&t>=d)||b-a!==d-b){$('#modal-error').textContent='请设置相邻等长两窗，并确保截止时间不早于后窗结束。';return;}
    if(a!==Date.parse('2026-09-01')||b!==Date.parse('2026-09-21')||d!==Date.parse('2026-10-11')||t!==Date.parse('2026-11-15')){state.customWindow=true;state.analysisMode='immature';toast('自选窗口仅演示受限状态；金样结果对应固定演示窗口。');}
    else {state.customWindow=false;state.analysisMode='complete';toast('模拟任务已完成，可钻取统计证据。');}
    closeModal();render();return;
  }
  if(action==='investigate'){state.investigation=$('#investigation-note').value.trim();if(!state.investigation){toast('先填写调查依据或待补材料。');return;}if(state.risk!=='suspected'){state.riskHistory.push({version:state.riskVersion,status:riskNames[state.risk],reason:'旧版本保留，新的调查另建待确认版本'});state.riskVersion++;}state.risk='suspected';go('/after-sales/risks');toast('调查已创建（模拟），风险仍需人工确认。');return;}
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
