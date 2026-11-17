<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { route, navigate } from './router'
import { init, state, summary } from './s01'
import HomePage from './pages/HomePage.vue'
import WorkbenchPage from './pages/WorkbenchPage.vue'
import SuggestionsPage from './pages/SuggestionsPage.vue'
import SkuPage from './pages/SkuPage.vue'
import RequisitionsPage from './pages/RequisitionsPage.vue'
import AfterSalesPage from './afterSales/AfterSalesPage.vue'

const emit = defineEmits<{ logout: []; loggedOut: [] }>()

const mobileMenuOpen = ref(false)
const navigation = [
  { key: 'home', path: '/home', label: '工作台', icon: '▦' },
  { key: 'replenishment', path: '/workbench', label: '智能补货', icon: '补', children: [
    { key: 'suggestions', path: '/suggestions', label: '商品分析' },
    { key: 'requisitions', path: '/requisitions', label: '请购管理' }
  ] },
  { key: 'after-sales', path: '/after-sales/workbench', label: '售后与客户体验', icon: '客', children: [
    { key: 'after-cases', path: '/after-sales/cases', label: '售后处理' },
    { key: 'after-experience', path: '/after-sales/experience', label: '退货与商品分析' },
    { key: 'after-risks', path: '/after-sales/risks', label: '调查与质量风险' },
    { key: 'after-materials', path: '/after-sales/materials', label: '知识与政策' }
  ] }
]

const current = computed(() => {
  const path = route.value.path
  if(path.startsWith('/after-sales')) return 'after-sales'
  if (path === '/home' || path === '/') return 'home'
  if (path.startsWith('/sku/')) return 'sku'
  if (path.startsWith('/requisitions')) return 'requisitions'
  if (path.startsWith('/suggestions')) return 'suggestions'
  return 'workbench'
})

const page = computed(() => {
  switch (current.value) {
    case 'home': return HomePage
    case 'after-sales': return AfterSalesPage
    case 'suggestions': return SuggestionsPage
    case 'sku': return SkuPage
    case 'requisitions': return RequisitionsPage
    default: return WorkbenchPage
  }
})

function navActive(key: string) {
  const path = route.value.path
  if (key === 'home') return current.value === 'home'
  if (key === 'replenishment') return current.value !== 'home' && current.value !== 'after-sales'
  if (key === 'suggestions') return current.value === 'suggestions' || current.value === 'sku'
  if (key === 'requisitions') return current.value === 'requisitions'
  if (key === 'after-sales') return current.value === 'after-sales'
  if (key === 'after-cases') return path === '/after-sales/cases'
  if (key === 'after-experience') return path === '/after-sales/experience'
  if (key === 'after-risks') return path === '/after-sales/risks'
  if (key === 'after-materials') return path === '/after-sales/materials'
  return false
}

const crumb = computed(() => {
  if (current.value === 'home') return ['首页']
  if (current.value === 'after-sales') {
    const section = route.value.segments[1]
    const labels: Record<string, string> = { workbench: '售后工作台', cases: '售后处理', experience: '退货与商品分析', risks: '调查与质量风险', materials: '知识与政策' }
    return ['售后与客户体验', labels[section] || '售后工作台']
  }
  if (current.value === 'sku') return ['智能补货', '商品分析']
  if (current.value === 'suggestions') return ['智能补货', '商品列表']
  if (current.value === 'requisitions') return ['请购管理']
  return ['智能补货']
})

const navCount = computed(() => summary.value?.discoveredSkuCount ?? null)
onMounted(async () => {
  if (!route.value.segments.length) navigate('/home')
  await init()
})

watch(() => route.value.path, path => {
  mobileMenuOpen.value = false
  if (['/detail', '/approvals'].includes(path)) navigate('/home')
  if (path === '/' || path === '') navigate('/home')
}, { immediate: true })
</script>

<template>
  <aside class="sidebar agent-sidebar" :class="{ 'mobile-open': mobileMenuOpen }">
    <div class="sidebar-head"><a class="brand" href="#/home"><span class="brand-symbol">序</span><span>序衡<small class="brand-en">COMMERCE OPERATIONS</small></span></a><button class="mobile-menu-button" type="button" :aria-expanded="mobileMenuOpen" @click="mobileMenuOpen = !mobileMenuOpen">{{ mobileMenuOpen ? '收起导航' : '功能导航' }}</button></div>
    <div class="workspace"><span class="workspace-icon">中</span><div>跨境电商智慧中台<small>业务工作台</small></div></div>
    <div class="nav-label">工作台</div>
    <nav aria-label="主要导航">
      <template v-for="group in navigation" :key="group.key">
        <a class="nav-group-link" :class="{ active: navActive(group.key) }" :href="'#' + group.path" :aria-current="navActive(group.key) ? 'page' : undefined">
          <span class="nav-icon">{{ group.icon }}</span>{{ group.label }}
        </a>
        <div v-if="group.children" class="nav-children">
          <a v-for="item in group.children" :key="item.key" :href="'#' + item.path" :class="{ active: navActive(item.key) }" :aria-current="navActive(item.key) ? 'page' : undefined">
            {{ item.label }}<span v-if="item.key === 'suggestions' && navCount" class="nav-count">{{ navCount }}</span>
          </a>
        </div>
      </template>
    </nav>
    <div class="sidebar-bottom"><div class="version">WORKSPACE <span>v0.2</span></div></div>
  </aside>

  <div class="app-shell">
    <header class="topbar">
      <div class="breadcrumb"><a href="#/home">序衡 · 智慧中台</a> <span>/</span> <span v-for="(name, index) in crumb" :key="name">{{ name }}<template v-if="index < crumb.length - 1"> / </template></span></div>
      <div class="top-actions">
        <span class="demo-chip" title="本地教学环境：数据来自教学 ERP 的仿真业务数据，采购提交仅创建申请单">教学数据</span>
        <button class="button small" @click="emit('logout')">退出会话</button>
      </div>
    </header>
    <main id="main">
      <component :is="page" />
    </main>
    <footer class="page-footer">
      <span>序衡 / 跨境电商智慧 AI 中台</span>
    </footer>
  </div>
</template>
