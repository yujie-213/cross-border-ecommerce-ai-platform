<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { route, navigate } from './router'
import { init, state, summary } from './s01'
import WorkbenchPage from './pages/WorkbenchPage.vue'
import SuggestionsPage from './pages/SuggestionsPage.vue'
import SkuPage from './pages/SkuPage.vue'
import RequisitionsPage from './pages/RequisitionsPage.vue'

const emit = defineEmits<{ logout: []; loggedOut: [] }>()

const sections = [
  { key: 'workbench', path: '/workbench', label: '工作台' },
  { key: 'suggestions', path: '/suggestions', label: '补货建议' },
  { key: 'requisitions', path: '/requisitions', label: '请购管理' }
]

const current = computed(() => {
  const path = route.value.path
  if (path.startsWith('/sku/')) return 'sku'
  if (path.startsWith('/requisitions')) return 'requisitions'
  if (path.startsWith('/suggestions')) return 'suggestions'
  return 'workbench'
})

const page = computed(() => {
  switch (current.value) {
    case 'suggestions': return SuggestionsPage
    case 'sku': return SkuPage
    case 'requisitions': return RequisitionsPage
    default: return WorkbenchPage
  }
})

const crumb = computed(() => {
  if (current.value === 'sku') return ['补货建议', 'SKU 详情']
  if (current.value === 'suggestions') return ['补货建议']
  if (current.value === 'requisitions') return ['请购管理']
  return ['工作台']
})

const navCount = computed(() => summary.value?.scopeObjectCount ?? null)

onMounted(async () => {
  if (!route.value.segments.length) navigate('/workbench')
  await init()
})

watch(() => route.value.path, path => {
  if (['/detail', '/approvals'].includes(path)) navigate('/workbench')
  if (path === '/' || path === '') navigate('/workbench')
}, { immediate: true })
</script>

<template>
  <aside class="sidebar">
    <a class="brand" href="#/workbench"><span class="brand-symbol">序</span><span>序衡<small class="brand-en">COMMERCE OPERATIONS</small></span></a>
    <div class="workspace"><span class="workspace-icon">跨</span><div>跨境电商智慧中台<small>采购运营空间</small></div></div>
    <div class="nav-label">采购业务</div>
    <nav aria-label="主要导航">
      <a v-for="item in sections" :key="item.key" :href="'#' + item.path"
         :class="{ active: current === item.key || (item.key === 'suggestions' && current === 'sku') }"
         :aria-current="current === item.key || (item.key === 'suggestions' && current === 'sku') ? 'page' : undefined">
        <span class="nav-icon">{{ item.key === 'workbench' ? '▦' : item.key === 'suggestions' ? '≡' : '☑' }}</span>
        {{ item.label }}
        <span v-if="item.key === 'suggestions' && navCount" class="nav-count">{{ navCount }}</span>
      </a>
    </nav>
    <div class="sidebar-note"><span class="tiny-dot" /> S01 · 供需与库存分析<small>规则算数量 · 人工确认 · ERP 审批</small></div>
    <div class="sidebar-bottom"><div class="version">WORKSPACE <span>v0.2</span></div></div>
  </aside>

  <div class="app-shell">
    <header class="topbar">
      <div class="breadcrumb">采购运营 <span>/</span> <span v-for="(name, index) in crumb" :key="name">{{ name }}<template v-if="index < crumb.length - 1"> / </template></span></div>
      <div class="top-actions">
        <span class="demo-chip" title="本地教学环境：数据来自教学 ERP 的仿真业务数据，采购提交仅创建申请单">教学数据</span>
        <span class="tenant">可信会话 · 已连接</span>
        <button class="button small" @click="emit('logout')">退出会话</button>
      </div>
    </header>
    <main id="main">
      <component :is="page" />
    </main>
    <footer class="page-footer">
      <span>序衡 / S01 采购补货分析</span>
      <span>规则计算数量 · AI 辅助理解 · 人工确认提交</span>
    </footer>
  </div>
</template>
