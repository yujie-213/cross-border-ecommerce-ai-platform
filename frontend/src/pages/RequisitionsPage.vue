<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { init, loadRequisitions, requisitionRows, state, loadSingleHistory, requisitionCategory } from '../s01'
import type { RequisitionCategory as Category } from '../s01'

const filter = ref<'all' | Category>('all')

const PLATFORM: Record<string, { label: string; tone: string }> = {
  SUBMITTED: { label: '已提交', tone: 'info' },
  CREATED: { label: '已创建 · 待提交', tone: 'info' },
  SUBMITTING: { label: '提交中', tone: 'info' },
  CREATING: { label: '创建中', tone: 'info' },
  PREPARING: { label: '准备中', tone: 'info' },
  SUBMIT_UNKNOWN: { label: '提交结果未确认', tone: 'danger' },
  CREATE_UNKNOWN: { label: '创建结果未确认', tone: 'danger' },
  BLOCKED: { label: '已阻断', tone: 'warning' }
}

const CATEGORIES: { key: Category; label: string }[] = [
  { key: 'pending', label: '待 ERP 结果' },
  { key: 'approved', label: 'ERP 已审批' },
  { key: 'unknown', label: '待核对' },
  { key: 'blocked', label: '已阻断' },
  { key: 'draft', label: '流程未完成' }
]

const withRequisition = computed(() => requisitionRows.items.filter(row => !!row.requisition))
const withoutRequisition = computed(() => requisitionRows.items.length - withRequisition.value.length)

/** 行筛选与计数共用同一个分类函数，避免"数字与列表对不上"。 */
const counts = computed(() => {
  const result = { all: withRequisition.value.length } as Record<string, number>
  for (const category of CATEGORIES) result[category.key] = 0
  for (const row of withRequisition.value) result[requisitionCategory(row.requisition)]++
  return result
})

const rows = computed(() => filter.value === 'all'
  ? withRequisition.value
  : withRequisition.value.filter(row => requisitionCategory(row.requisition) === filter.value))

const visibleTabs = computed(() => CATEGORIES.filter(category => counts.value[category.key] > 0))
const unknownCount = computed(() => counts.value.unknown || 0)
const shortNumber = (value?: string | null) => value ? (value.length > 18 ? value.slice(0, 9) + '…' + value.slice(-6) : value) : '—'

const coverage = computed(() => {
  if (requisitionRows.loading || (!state.singleHistory.length && !requisitionRows.loaded)) return '正在回读最近的单品分析与请购记录…'
  const scanned = state.singleHistory.length
  const saved = withRequisition.value.length
  const capped = scanned >= 20 ? '（已达最近 20 条上限，更早记录未包含）' : ''
  return `覆盖范围：本次读取最近 ${scanned} 条单品分析，其中 ${saved} 条有已保存请购记录${capped}。`
})

async function refresh() {
  await loadSingleHistory()
  await loadRequisitions()
}

onMounted(async () => {
  await init()
  await refresh()
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>请购管理</h1>
        <p class="page-sub">平台提交与 ERP 审批分开记录；ERP 状态为回读原文，不代替领导审批</p>
      </div>
      <div class="head-actions">
        <button class="button" :disabled="requisitionRows.loading" @click="refresh">
          {{ requisitionRows.loading ? '回读中…' : '重新回读' }}
        </button>
      </div>
    </header>

    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>

    <div v-if="unknownCount" class="banner danger">
      <strong>{{ unknownCount }} 单提交结果未确认。</strong>ERP 可能已经建单，请先在对应 SKU 详情用原命令核对，不要重复提交。
    </div>

    <p class="banner plain">
      {{ coverage }}
      <strong>后端尚未提供请购列表接口</strong>，本页按单品分析逐条回读已保存的单据，不是全平台台账。
    </p>
    <p class="banner plain small">
      分类口径：平台状态由本平台记录；ERP 状态为回读原文，只有明确写明“通过 / 已审批”才计入已审批，其余一律归入待 ERP 结果，不做推断。
    </p>

    <div class="seg" role="group" aria-label="请购状态">
      <button :aria-pressed="filter === 'all'" @click="filter = 'all'">全部<em>{{ counts.all }}</em></button>
      <button v-for="category in visibleTabs" :key="category.key"
              :aria-pressed="filter === category.key" @click="filter = category.key">
        {{ category.label }}<em>{{ counts[category.key] }}</em>
      </button>
    </div>

    <section class="panel">
      <div class="panel-head"><h2>请购记录</h2><small>{{ rows.length }} 条</small></div>
      <div class="table-scroll">
        <table class="ltable">
          <thead>
            <tr><th>SKU / 对象</th><th>平台状态</th><th>ERP 状态（回读原文）</th><th class="r">建议 → 最终</th><th>ERP 单号</th><th>回读时间</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.task.taskRef.taskId">
              <td><span class="cell-title">{{ row.task.sku || '单品分析' }}</span><small class="mono">{{ row.task.taskRef.taskId.slice(0, 10) }}</small></td>
              <td>
                <span class="chip" :class="PLATFORM[row.requisition?.state || '']?.tone || 'muted'">{{ PLATFORM[row.requisition?.state || '']?.label || row.requisition?.state || '未提交' }}</span>
                <small v-if="row.requisition?.errorCode" class="err">{{ row.requisition.errorCode }}</small>
              </td>
              <td>{{ row.requisition?.erpStatus || '未回读' }}</td>
              <td class="r num">{{ row.requisition ? `${row.requisition.aiQuantity} → ${row.requisition.finalQuantity}` : '—' }}</td>
              <td class="mono" :title="row.requisition?.erpNumber || ''">{{ shortNumber(row.requisition?.erpNumber) }}</td>
              <td class="num">{{ row.requisition?.verifiedAt?.slice(5, 16).replace('T', ' ') || '—' }}</td>
              <td class="r"><a class="button small" :href="'#/sku/' + (row.task.entityKey || '') + '?batch=' + state.batchId + '&single=' + row.task.taskRef.taskId">查看 SKU</a></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="withoutRequisition" class="table-foot">
        <span>另有 {{ withoutRequisition }} 条单品分析没有已保存的请购记录（未提交或分析未完成），不计入本页统计</span>
      </div>
      <div v-if="!rows.length" class="empty-inline">
        {{ requisitionRows.loading ? '正在回读已保存的请购记录…' : '当前范围内没有已保存的请购记录。' }}
      </div>
    </section>
  </div>
</template>
