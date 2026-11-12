<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useWorkspace } from './useWorkspace'
import { choiceLabel, shown, sourceText, terminal } from './domain'
import Panel from './components/Panel.vue'
import Notice from './components/Notice.vue'
import Modal from './components/Modal.vue'
import StatusBadge from './components/StatusBadge.vue'
import ReportDetail from './components/ReportDetail.vue'
import HistoryTable from './components/HistoryTable.vue'
import type { Ref } from './api/types'
const w = useWorkspace()
const { choices, selectedRef, selected, connected, busy, loading, task, report, history, cursor, historyBefore, error, pollNote, pending, evidence, evidenceError, evidenceLoading, evidenceOpen } = w
const routes: Record<string, string> = { workbench: '工作台', suggestions: '补货建议', approvals: '人工审批', detail: '分析详情' }
const route = ref('workbench')
function syncRoute() { route.value = Object.hasOwn(routes, location.hash.slice(1)) ? location.hash.slice(1) : 'workbench' }
function navigate(page: string) { location.hash = page }
const loginToken = ref(''), loginOpen = ref(false), createOpen = ref(false)
const previous = ref<Ref | null>(null)
const storeFilter = ref(''), warehouseFilter = ref(''), skuFilter = ref(''), stateFilter = ref('')
const filteredChoices = computed(() => choices.value.filter(c => (!storeFilter.value || c.scope.storeIds.includes(storeFilter.value)) && (!warehouseFilter.value || c.scope.warehouseIds.includes(warehouseFilter.value)) && c.scope.canonicalSkuIds.some(id => id.toLowerCase().includes(skuFilter.value.trim().toLowerCase()))))
const stores = computed(() => [...new Set(choices.value.flatMap(c => c.scope.storeIds))])
const warehouses = computed(() => [...new Set(choices.value.flatMap(c => c.scope.warehouseIds))])
watch(filteredChoices, filtered => { if (selectedRef.value && !filtered.some(c => c.packageRef === selectedRef.value)) void w.selectPackage('') })
const visibleHistory = computed(() => history.value.filter(t => !stateFilter.value || t.state === stateFilter.value))
async function login() { const token = loginToken.value.trim(); loginToken.value = ''; await w.connect(token || undefined); if (connected.value) loginOpen.value = false }
async function openTask(id: string) { navigate('detail'); await w.openTask(id) }
function newAnalysis(reanalyze = false) {
  previous.value = null
  if (reanalyze && report.value) {
    const matching = choices.value.find(c => c.packageRef === report.value!.dataReport.scenarioSupplement.packageRef)
    if (!matching) return
    void w.selectPackage(matching.packageRef); previous.value = report.value.reportRef
  }
  createOpen.value = true
}
async function submit() { createOpen.value = false; navigate('detail'); await w.create(previous.value) }
async function showEvidence(id: string) { await w.readEvidence(id) }
const canReanalyze = computed(() => !!report.value && choices.value.some(c => c.packageRef === report.value!.dataReport.scenarioSupplement.packageRef))
onMounted(() => { syncRoute(); window.addEventListener('hashchange', syncRoute); void w.connect() })
onUnmounted(() => window.removeEventListener('hashchange', syncRoute))
</script>
<template>
  <a class="skip" href="#main" @click.prevent="($refs.main as HTMLElement)?.focus()">跳至主要内容</a>
  <aside class="sidebar"><a class="brand" href="#workbench"><span class="brand-symbol">序</span><span>序衡<small class="brand-en">COMMERCE OPERATIONS</small></span></a><div class="workspace"><span class="workspace-icon">跨</span><div>跨境电商智慧中台<small>采购运营空间</small></div></div><div class="nav-label">运营中心</div><nav aria-label="主要导航"><a v-for="(name, key) in { workbench: '工作台', suggestions: '补货建议', approvals: '人工审批' }" :key="key" :href="'#' + key" :class="{ active: route === key || (key === 'suggestions' && route === 'detail') }" :aria-current="route === key || (key === 'suggestions' && route === 'detail') ? 'page' : undefined"><span class="nav-icon">{{ key === 'workbench' ? '▦' : key === 'suggestions' ? '≡' : '☑' }}</span>{{ name }}<small v-if="key === 'approvals'" class="future">未开放</small></a></nav><div class="sidebar-note"><span class="tiny-dot" /> S01 · 供需与库存分析<small>确定性工作流 / 只读教学切片</small></div><div class="sidebar-bottom"><div class="version">WORKSPACE <span>v0.1</span></div></div></aside>
  <div class="app-shell"><header class="topbar"><div class="breadcrumb">运营中心 <span>/</span> <span>{{ routes[route] }}</span></div><div class="top-actions"><span class="tenant">{{ connected ? '可信会话 · 已连接' : '尚未连接身份' }}</span><button v-if="connected" class="button small" :disabled="busy" @click="w.logout">退出会话</button><button v-else class="button small" @click="loginOpen = true">连接身份</button></div></header><div class="prototype-bar"><span><b>S01 只读教学分析</b><span class="bar-divider">/</span>固定服务端数据包 · 企业正式准入 BLOCKED</span><span>无采购审批 / 执行</span></div>
  <main id="main" ref="main" tabindex="-1">
    <Notice v-if="error" tone="danger" title="操作未完成" :alert="true"><p>{{ error }}</p><button class="button small" :disabled="busy" @click="w.connect()">重新核对会话与选项</button></Notice>
    <Notice v-if="pending" tone="warning" title="命令状态待确认"><p>{{ pending.kind === 'create' ? '创建分析' : '取消任务' }} · {{ pending.createdAt }}。请核对原命令；重复核对沿用相同幂等 key，不创建新命令。</p><button class="button small" :disabled="busy || !connected" @click="w.retryCommand()">使用原命令核对</button></Notice>
    <Notice v-if="!connected" title="需要服务端可信身份">请连接已有授权会话。身份令牌仅用于交换安全 Cookie，不保存至浏览器存储；此处不能创建账号或切换角色。<button class="button small" @click="loginOpen = true">连接身份</button></Notice>
    <template v-if="route === 'workbench' || route === 'suggestions'">
      <div class="page-head"><div><div class="eyebrow">{{ route === 'workbench' ? 'OPERATIONS / WORKBENCH' : 'S01 / REPLENISHMENT' }}</div><h1>{{ route === 'workbench' ? '采购运营工作台' : '补货建议' }}</h1><p class="subtitle">选择授权范围，查看任务、规则报告与待核实的问题。</p></div><button class="button primary" :disabled="!connected || busy || !!pending || !choices.length" @click="newAnalysis()">＋ 新建补货分析</button></div>
      <div v-if="route === 'workbench'" class="hero-overview"><div><div class="hero-status"><span class="status-dot" />只读分析工作空间</div><h2>先核实供需与风险，再进行人工复核</h2><p class="muted">真实 API / 独立 Worker / 固定教学快照。当前页面不提供采购操作。</p></div><button class="button" @click="navigate('suggestions')">进入补货分析 →</button></div>
      <Panel :title="route === 'workbench' ? '当前有权分析的范围' : '授权数据包与范围筛选'" note="固定 packageRef · 非在线 ERP 商品搜索">
        <div class="filters"><label class="field">店铺<select v-model="storeFilter"><option value="">全部授权店铺</option><option v-for="store in stores" :key="store">{{ store }}</option></select></label><label class="field">仓库<select v-model="warehouseFilter"><option value="">全部授权仓库</option><option v-for="warehouse in warehouses" :key="warehouse">{{ warehouse }}</option></select></label><label class="field">SKU 搜索<input v-model="skuFilter" type="search" placeholder="在授权包内筛选 SKU"></label><button class="button small" @click="storeFilter = ''; warehouseFilter = ''; skuFilter = ''">清空筛选</button></div>
        <label class="field package-select">当前包 / 精确历史范围<select :value="selectedRef" :disabled="!connected" @change="w.selectPackage(($event.target as HTMLSelectElement).value)"><option value="">请选择授权 SKU 与教学时点包</option><option v-for="choice in filteredChoices" :key="choice.packageRef" :value="choice.packageRef">{{ choiceLabel(choice) }}</option></select></label>
        <Notice v-if="selected" :title="sourceText(selected.sourceNature)" tone="warning"><p class="mono wrap">{{ selected.sourceNature }}</p><p>时点 {{ shown(selected.asOf) }} · 包 {{ selected.packageRef.slice(0, 16) }}。同一 SKU 的多个时点包是独立快照，库存不能相加。历史按精确店 / 仓 / SKU 查询，可能包含该范围其他时点的任务。</p></Notice>
        <div v-if="connected && !filteredChoices.length" class="empty compact"><h3>无符合条件的授权包</h3><p>请清空筛选或联系管理员核实当前授权，不会选择模拟默认 SKU。</p></div>
      </Panel>
      <div v-if="route === 'workbench' && selected" class="metrics"><div class="metric"><div class="metric-label">本页历史任务</div><div class="metric-value">{{ history.length }}<small>条</small></div><p class="metric-foot">精确范围 · 最多 20 条</p></div><div class="metric"><div class="metric-label">本页已发布报告</div><div class="metric-value">{{ history.filter(t => t.state === 'SUCCEEDED' && t.reportRef).length }}<small>份</small></div><p class="metric-foot">不代表全库总数</p></div></div>
      <Panel v-if="route === 'workbench' && report" title="最近打开的报告" note="仅当前会话已读取的报告"><template #action><button class="button small" @click="openTask(report.taskRef.taskId)">打开报告</button></template><div class="section-head"><h3>{{ report.scope.canonicalSkuIds.join('、') }}</h3><StatusBadge :value="report.completeness" /></div><p class="micro-note">{{ report.scope.storeIds.join('、') }} / {{ report.scope.warehouseIds.join('、') }} · {{ shown(report.dataReport.scenarioSupplement.asOf) }}</p><Notice v-if="report.dataReport.quality.length" tone="warning" title="存在数据 / 质量问题">{{ report.dataReport.quality.map(i => i.code).join('、') }}。请打开详情核实责任与限制。</Notice><p v-else class="micro-note">当前报告未返回质量问题，企业准入仍 BLOCKED。</p></Panel>
      <Panel title="任务与报告历史" note="精确范围 · 游标分页"><template #action><button class="button small" :disabled="!selected || busy" @click="w.loadHistory()">刷新历史</button></template><div class="filters history-filters"><label class="field">本页状态<select v-model="stateFilter"><option value="">全部状态</option><option v-for="state in ['QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED']" :key="state" :value="state">{{ state }}</option></select></label><p class="micro-note">详情中独立查看质量、AI 和采购适用性。</p></div><HistoryTable :items="visibleHistory" :cursor="cursor" :paged="!!historyBefore" @open="openTask" @next="cursor && w.loadHistory(cursor)" @first="w.loadHistory()" /></Panel>
    </template>
    <template v-else-if="route === 'detail'">
      <a class="back" href="#suggestions">← 返回补货建议</a>
      <Panel title="分析任务" note="受理 / 运行不等于报告发布"><div v-if="task" class="task-strip"><div><StatusBadge :value="task.state" /><p class="mono wrap">{{ task.taskRef.taskId }} · revision {{ task.revision }}</p><p class="micro-note">服务端截止 {{ task.deadline }}<template v-if="task.errorCode"> · {{ task.errorCode }}</template></p></div><div class="button-row"><button class="button" :disabled="busy || loading" @click="w.openTask(task.taskRef.taskId)">重新查询状态</button><button v-if="!terminal(task.state)" class="button danger" :disabled="busy || !!pending" @click="w.cancel()">取消分析任务</button><button v-if="report" class="button primary" :disabled="busy || !!pending || !canReanalyze" @click="newAnalysis(true)">基于此报告重新分析</button></div></div><div v-else class="empty compact">{{ loading ? '正在查询服务端实际状态…' : '尚未选择可访问的任务。请从历史打开，或新建分析。' }}</div><p v-if="pollNote" class="micro-note" role="status">{{ pollNote }}</p><p v-if="task && !terminal(task.state)" class="micro-note">每 2 秒查询，最多 60 次；终态、权限拒绝或网络异常时停止。</p></Panel>
      <ReportDetail v-if="report" :report="report" @evidence="showEvidence" />
      <Notice v-else-if="task && terminal(task.state)" :tone="task.state === 'FAILED' ? 'danger' : 'info'" title="当前无可读报告">{{ task.state === 'CANCELLED' ? '任务已取消，不会展示成功报告。' : task.state === 'FAILED' ? '任务失败，请核实错误后再发起新的用户命令。' : '报告尚未发布或不可访问，请重新查询。' }}</Notice>
    </template>
    <template v-else><div class="page-head"><div><div class="eyebrow">HUMAN REVIEW</div><h1>人工审批</h1><p class="subtitle">保留独立人工终点，等待后端能力及业务授权。</p></div></div><Panel title="审批功能尚未开放"><Notice title="当前仅支持只读补货分析">服务端没有采购建议草稿提交、采购审批或执行 API。请在分析详情核实证据与限制。</Notice><p class="micro-note">本页不会切换角色授予权限，也不会产生审批记录。</p><a class="button" href="#suggestions">返回补货建议</a></Panel></template>
  </main><footer class="page-footer"><span>序衡 / S01 采购补货分析</span><span>教学验证 · 仅供人工复核</span></footer></div>
  <Modal v-if="loginOpen" title="连接可信身份" @close="loginOpen = false; loginToken = ''"><form @submit.prevent="login"><p>使用受控启动流程提供的短期 Bearer 令牌，或直接核对已有 Cookie 会话。不在此输入 ERP 密码、签名密钥或数据库凭据。</p><label class="field">短期身份令牌<input v-model="loginToken" type="password" autocomplete="off" spellcheck="false" placeholder="已有 Cookie 会话可留空"></label><p class="micro-note">令牌交换后立即清空；Secure / HttpOnly / SameSite Cookie 与 CSRF 由后端校验。</p><button class="button primary" :disabled="busy">{{ busy ? '连接中…' : '连接会话' }}</button></form></Modal>
  <Modal v-if="createOpen" :title="previous ? '基于旧报告新建分析' : '新建只读补货分析'" @close="createOpen = false"><form @submit.prevent="submit"><label class="field">授权 SKU / 时点包<select :value="selectedRef" required :disabled="!!previous" @change="w.selectPackage(($event.target as HTMLSelectElement).value)"><option value="">请选择授权包</option><option v-for="choice in choices" :key="choice.packageRef" :value="choice.packageRef">{{ choiceLabel(choice) }}</option></select></label><template v-if="selected"><dl class="metadata"><dt>店铺 / 仓库</dt><dd>{{ selected.scope.storeIds.join('、') }} / {{ selected.scope.warehouseIds.join('、') }}</dd><dt>来源</dt><dd>{{ sourceText(selected.sourceNature) }}</dd><dt>快照时点</dt><dd>{{ shown(selected.asOf) }}</dd><dt>packageRef</dt><dd>{{ selected.packageRef }}</dd><dt v-if="previous">前序报告</dt><dd v-if="previous">{{ previous.reportId }}</dd></dl></template><Notice tone="warning" title="只读教学分析">不会创建采购订单。新任务重新生成报告，不继承旧计算结论或审批状态。</Notice><button class="button primary" :disabled="!selected || busy || !!pending">发起真实分析任务</button></form></Modal>
  <Modal v-if="evidenceOpen" title="当前报告证据" @close="evidenceOpen = false; w.closeEvidence()"><p v-if="evidenceLoading">正在核对当前读取权限…</p><Notice v-if="evidenceError" tone="danger" title="证据不可访问或不存在">{{ evidenceError }}<p>无法核实此依据，请联系数据负责人。</p></Notice><pre v-if="evidence !== undefined" class="evidence-json">{{ JSON.stringify(evidence, null, 2) }}</pre><p class="micro-note">仅展示公开报告内的最小字段值，不提供 ERP 原始响应。</p></Modal>
</template>
