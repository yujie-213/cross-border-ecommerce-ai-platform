<script setup lang="ts">
import type { V2Item } from '../api/v2'
import { unitLabel } from '../api/v2'
import { shown } from '../domain'
import Panel from './Panel.vue'
defineProps<{ item: V2Item }>()
</script>
<template>
      <Panel v-if="item.demandWindow?.referenceAverage" title="历史销量参考分析" note="参考信息，不是当前采购数量">
        <p>历史样本 {{ item.demandWindow.sampleStart }}—{{ item.demandWindow.sampleEnd }}，{{ item.demandWindow.referenceDays }} 个有销售记录日期；记录日期均值 {{ Number(item.demandWindow.referenceAverage).toFixed(2) }} 件。该均值不把未知日期补零，也不冒充当前7日SMA。</p>
        <p>当前ERP可用库存 {{ shown(item.inventory?.available) }} {{ unitLabel(item.unit) }}；{{ item.inventoryBasis?.status === 'VERIFIED' ? '库存守恒已核验' : '库存流水尚未完整核验' }}。本期 {{ item.demandWindow.windowStart }}—{{ item.demandWindow.windowEnd }}，有效样本 {{ item.demandWindow.validDays }} 日，待核实 {{ item.demandWindow.missingDays }} 日。</p>
        <p v-if="item.demandWindow.referenceGrade === 'STALE_HISTORICAL'">历史样本已较旧，请核对近期经营情况。</p>
        <div class="table-scroll"><table><thead><tr><th>历史业务日</th><th>ERP记录销量</th></tr></thead><tbody><tr v-for="d in item.demandWindow.observedHistory" :key="d.orderRef"><td>{{ d.businessDate }}</td><td>{{ d.quantity }} 件</td></tr></tbody></table></div>
        <p v-for="hint in item.recoveryHints || []" :key="hint.code" class="micro-note">{{ hint.message }} {{ hint.action }}。</p>
        <p class="micro-note">缺少完整预测证据时不生成采购数量；已有历史报告仍按原日期保留，请新建单品分析获取当前事实。</p>
      </Panel>
</template>
