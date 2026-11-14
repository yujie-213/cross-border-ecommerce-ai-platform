<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { init, loadRequisitions, requisitionRows, state, loadSingleHistory } from '../s01'

const filter = ref<'all' | 'waiting' | 'approved' | 'unknown' | 'blocked'>('all')

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

const withRequisition = computed(() => requisitionRows.items.filter(row => !!row.requisition))
const withoutRequisition = computed(() => requisitionRows.items.length - withRequisition.value.length)

const rows = computed(() => withRequisition.value.filter(row => {
  const rq = row.requisition
  if (filter.value === 'all') return true
  if (!rq) return false
  if (filter.value === 'unknown') return ['SUBMIT_UNKNOWN', 'CREATE_UNKNOWN'].includes(rq.state)
  if (filter.value === 'blocked') return rq.state === 'BLOCKED'
  if (filter.value === 'approved') return String(rq.erpStatus || '').includes('审批') && !String(rq.erpStatus || '').includes('待')
  return rq.state === 'SUBMITTED' && !(String(rq.erpStatus || '').includes('审批') && !String(rq.erpStatus || '').includes('待'))
}))

const counts = computed(() => ({
  all: withRequisition.value.length,
  waiting: withRequisition.value.filter(r => r.requisition?.state === 'SUBMITTED').length,
  approved: withRequisition.value.filter(r => String(r.requisition?.erpStatus || '').includes('审批') && !String(r.requisition?.erpStatus || '').includes('待')).length,
  unknown: withRequisition.value.filter(r => ['SUBMIT_UNKNOWN', 'CREATE_UNKNOWN'].includes(r.requisition?.state || '')).length,
  blocked: withRequisition.value.filter(r => r.requisition?.state === 'BLOCKED').length
}))
const shortNumber = (value?: string | null) => value ? (value.length > 18 ? value.slice(0, 9) + '…' + value.slice(-6) : value) : '—'

const unknownCount = computed(() => counts.value.unknown)

onMounted(async () => {
  await init()
  await loadSingleHistory()
  await loadRequisitions()
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>请购管理</h1>
        <p class="page-sub">平台提交与 ERP 审批分开记录；返回的状态来自独立回读，不代替领导审批</p>
      </div>
      <div class="head-actions">
        <button class="button" :disabled="requisitionRows.loading" @click="loadSingleHistory().then(loadRequisitions)">
          {{ requisitionRows.loading ? '回读中…' : '重新回读' }}
        </button>
      </div>
    </header>

    <p v-if="state.error" class="banner danger" role="alert">{{ state.error }}</p>

    <div v-if="unknownCount" class="banner danger">
      <strong>{{ unknownCount }} 单提交结果未确认。</strong>ERP 可能已经建单，请先在对应 SKU 详情用原命令核对，不要重复提交。
    </div>

    <p class="banner plain">
      数据来源：最近 20 条单品分析的已保存请购记录，逐条读取。<strong>后端尚未提供请购列表接口</strong>，因此这里不是全平台台账；
      全量统计需接口补充后再实现。
    </p>

    <div class="seg" role="group" aria-label="请购状态">
      <button :aria-pressed="filter === 'all'" @click="filter = 'all'">全部<em>{{ counts.all }}</em></button>
      <button :aria-pressed="filter === 'waiting'" @click="filter = 'waiting'">待审批<em>{{ counts.waiting }}</em></button>
      <button :aria-pressed="filter === 'approved'" @click="filter = 'approved'">已审批<em>{{ counts.approved }}</em></button>
      <button :aria-pressed="filter === 'unknown'" @click="filter = 'unknown'">待核对<em>{{ counts.unknown }}</em></button>
      <button :aria-pressed="filter === 'blocked'" @click="filter = 'blocked'">已阻断<em>{{ counts.blocked }}</em></button>
    </div>

    <section class="panel">
      <div class="panel-head"><h2>请购记录</h2><small>{{ rows.length }} 条</small></div>
      <div class="table-scroll">
        <table class="ltable">
          <thead>
            <tr><th>SKU / 对象</th><th>平台状态</th><th>ERP 状态</th><th class="r">建议 → 最终</th><th>ERP 单号</th><th>回读时间</th><th></th></tr>
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
        <span>另有 {{ withoutRequisition }} 条单品分析未提交请购（不显示在本页）</span>
      </div>
      <div v-if="!rows.length" class="empty-inline">
        {{ requisitionRows.loading ? '正在回读已保存的请购记录…' : '当前范围内没有已保存的请购记录。' }}
      </div>
    </section>
  </div>
</template>
