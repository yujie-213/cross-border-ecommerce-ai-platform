<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { route, navigate } from './router'
import { init, state, summary } from './s01'
import HomePage from './pages/HomePage.vue'
import WorkbenchPage from './pages/WorkbenchPage.vue'
import SuggestionsPage from './pages/SuggestionsPage.vue'
import SkuPage from './pages/SkuPage.vue'
import RequisitionsPage from './pages/RequisitionsPage.vue'

const emit = defineEmits<{ logout: []; loggedOut: [] }>()

const sections = [
  { key: 'home', path: '/home', label: '首页' },
  { key: 'workbench', path: '/workbench', label: '智能补货' },
  { key: 'suggestions', path: '/suggestions', label: '补货建议' },
  { key: 'requisitions', path: '/requisitions', label: '请购管理' }
]

const current = computed(() => {
  const path = route.value.path
  if (path === '/home' || path === '/') return 'home'
  if (path.startsWith('/sku/')) return 'sku'
  if (path.startsWith('/requisitions')) return 'requisitions'
  if (path.startsWith('/suggestions')) return 'suggestions'
  return 'workbench'
})

const page = computed(() => {
  switch (current.value) {
    case 'home': return HomePage
    case 'suggestions': return SuggestionsPage
    case 'sku': return SkuPage
    case 'requisitions': return RequisitionsPage
    default: return WorkbenchPage
  }
})

const crumb = computed(() => {
  if (current.value === 'home') return ['首页']
  if (current.value === 'sku') return ['补货建议', 'SKU 详情']
  if (current.value === 'suggestions') return ['补货建议']
  if (current.value === 'requisitions') return ['请购管理']
  return ['智能补货']
})

const navCount = computed(() => summary.value?.discoveredSkuCount ?? null)

onMounted(async () => {
  if (!route.value.segments.length) navigate('/home')
  await init()
})

watch(() => route.value.path, path => {
  if (['/detail', '/approvals'].includes(path)) navigate('/home')
  if (path === '/' || path === '') navigate('/home')
}, { immediate: true })
</script>

<template>
  <aside class="sidebar">
    <a class="brand" href="#/home"><span class="brand-symbol">序</span><span>序衡<small class="brand-en">COMMERCE OPERATIONS</small></span></a>
    <div class="workspace"><span class="workspace-icon">跨</span><div>跨境电商智慧中台<small>业务工作空间</small></div></div>
    <div class="nav-label">业务导航</div>
    <nav aria-label="主要导航">
      <a v-for="item in sections" :key="item.key" :href="'#' + item.path"
         :class="{ active: current === item.key || (item.key === 'suggestions' && current === 'sku') }"
         :aria-current="current === item.key || (item.key === 'suggestions' && current === 'sku') ? 'page' : undefined">
        <span class="nav-icon">{{ item.key === 'home' ? '⌂' : item.key === 'workbench' ? '▦' : item.key === 'suggestions' ? '≡' : '☑' }}</span>
        {{ item.label }}
        <span v-if="item.key === 'suggestions' && navCount" class="nav-count">{{ navCount }}</span>
      </a>
    </nav>
    <div class="sidebar-note"><span class="tiny-dot" /> 自有业务 · 教学环境<small>只分析登记核验的商品</small></div>
    <div class="sidebar-bottom"><div class="version">WORKSPACE <span>v0.2</span></div></div>
  </aside>

  <div class="app-shell">
    <header class="topbar">
      <div class="breadcrumb">智慧中台 <span>/</span> <span v-for="(name, index) in crumb" :key="name">{{ name }}<template v-if="index < crumb.length - 1"> / </template></span></div>
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
      <span>序衡 / 跨境电商智慧 AI 中台</span>
      <span>业务事实为依据 · AI 辅助决策</span>
    </footer>
  </div>
</template>
