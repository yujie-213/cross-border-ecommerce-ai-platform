<script setup lang="ts">
import { computed } from 'vue'
import type { V2Item } from '../api/v2'
import { issueLabel } from '../api/v2'
import { fmt, dash } from '../s01'
import SalesBars from './charts/SalesBars.vue'
import BalanceChart from './charts/BalanceChart.vue'
const props = defineProps<{ item: V2Item; scopes: V2Item[] }>()
const emit = defineEmits<{ select: [key: string] }>()
const decision = computed(() => props.item.decision!)
const forecast = computed(() => decision.value.forecast)
const scopes = computed(() => (props.scopes.length ? props.scopes : [props.item]).map(r => r.entityKey === props.item.entityKey ? props.item : r))
const label = (r: V2Item) => ({ REPLENISH: '建议补货', NO_REPLENISHMENT: '暂不补货', NEEDS_REVIEW: '依据不足' }[r.decision?.status || 'NEEDS_REVIEW'])
const needed = computed(() => scopes.value.filter(r => r.decision?.status === 'REPLENISH').length)
const judged = computed(() => scopes.value.filter(r => r.decision && r.decision.status !== 'NEEDS_REVIEW').length)
const risks: Record<string, string> = {
  HISTORY_DATES_WITHOUT_RECORDS_UNKNOWN: '部分日期没有销售记录，实际需求未知', STALE_SALES_SAMPLES: '历史样本较旧，请核实近期需求变化',
  LOW_SALES_SAMPLE: '销售记录日期较少，建议谨慎使用', SALES_ENUMERATION_INCOMPLETE: '销售接口未完整读取，当前仅部分样本',
  CONFLICTING_SALES_RECORDS: '销售记录存在冲突，未用于确定数量', SALES_CONCENTRATED_IN_ONE_DAY: '销量集中于单日，可能受大单影响'
}
</script>

<template>
  <div class="decision-product">
    <section class="panel overall">
      <div class="panel-head"><h2>商品整体判断</h2><small>不混加不同店仓库存与销量</small></div>
      <div class="overall-grid">
        <div><b>{{ scopes.length }}</b><span>相关店仓对象</span></div>
        <div><b>{{ judged }}</b><span>可给出补货判断</span></div>
        <div><b class="teal">{{ needed }}</b><span>建议补货店仓</span></div>
        <div><b>{{ scopes.filter(r => r.decision?.stockoutRisk).length }}</b><span>参考缺货风险店仓</span></div>
      </div>
      <p class="muted small">优先查看需补仓库与预计短缺日期。下表各行独立计算；点选店仓后查看其销量、预测、ERP 对比和采购资格。</p>
      <div class="table-scroll"><table class="ltable compact" aria-label="逐店仓补货判断">
        <thead><tr><th>店铺 / 仓库</th><th>历史参考日均</th><th class="r">可用库存</th><th class="r">周期需求</th><th class="r">参考补充</th><th>判断 / 风险</th><th></th></tr></thead>
        <tbody><tr v-for="r in scopes" :key="r.entityKey" :class="{ chosen: r.entityKey === item.entityKey }">
          <td>{{ r.storeName || '店铺待核实' }}<small>{{ r.warehouseName || '仓库待核实' }}</small></td>
          <td>{{ fmt(r.decision?.forecast.averageDailyDemand, 2) }}<small>{{ r.decision?.forecast.observedDays || 0 }} 个有记录日</small></td>
          <td class="r num">{{ dash(r.inventory?.available) }}</td><td class="r num">{{ fmt(r.decision?.forecastQuantity) }}<small>{{ r.decision?.horizonDays || '—' }} 天周期</small></td>
          <td class="r num strong">{{ dash(r.decision?.referenceReplenishmentQuantity) }}</td>
          <td><span class="chip" :class="r.decision?.status === 'REPLENISH' ? 'confirm' : r.decision?.status === 'NO_REPLENISHMENT' ? 'none' : 'review'">{{ label(r) }}</span><small v-if="r.decision?.stockoutRisk">预计 {{ r.decision.firstShortageDate }} 短缺</small></td>
          <td><button class="button small" :disabled="r.entityKey === item.entityKey" @click="emit('select', r.entityKey)">{{ r.entityKey === item.entityKey ? '当前店仓' : '分析此仓' }}</button></td>
        </tr></tbody>
      </table></div>
    </section>

    <section class="panel scope-analysis">
      <div class="panel-head"><h2>{{ item.warehouseName || '归属待核实' }} · 补货决策</h2><span class="chip" :class="decision.status === 'REPLENISH' ? 'confirm' : decision.status === 'NO_REPLENISHMENT' ? 'none' : 'review'">{{ label(item) }}</span></div>
      <div class="decision-kpis">
        <div><span>未来 {{ decision.horizonDays }} 天参考需求</span><b>{{ fmt(decision.forecastQuantity) }}<small>件</small></b></div>
        <div><span>需补充的库存</span><b class="teal">{{ dash(decision.referenceReplenishmentQuantity) }}<small>件</small></b></div>
        <div><span>满足 MOQ / 整箱的可采购量</span><b>{{ dash(decision.purchasableQuantity) }}<small>件</small></b></div>
        <div><span>当前库存预计覆盖</span><b>{{ fmt(decision.coverageDays) }}<small>天</small></b></div>
      </div>
      <p class="planning-note">{{ decision.horizonBasis === 'ASSUMED_14_DAY_PLANNING' ? '交期未知：采用14天规划假设' : `报价交期 ${decision.leadDays} 天 + 7天覆盖` }} · 未扣未核实在途 · {{ decision.confidence === 'MEDIUM' ? '参考可信度中等' : decision.confidence === 'LOW' ? '参考可信度较低' : '依据不足' }} · 不代表已确认采购数量</p>
      <ul class="business-reasons"><li v-for="line in decision.explanation" :key="line">{{ line }}</li></ul>
      <details v-if="decision.assumptions.length"><summary>试算假设与供给范围</summary><ul class="business-reasons"><li v-for="a in decision.assumptions" :key="a">{{ a }}</li></ul><p class="muted small">当前库存来自 ERP available 字段与唯一登记店仓关联；不混加不同记录，不声称全历史守恒已通过。采购计划到货日期不等于确认可售日期。</p></details>
    </section>

    <section class="panel">
      <div class="panel-head"><h2>可信历史与未来需求</h2><small>已采集的全日期历史 · 当前店仓</small></div>
      <template v-if="forecast.available">
        <p class="sample-caption">{{ forecast.sampleStart }} 至 {{ forecast.sampleEnd }} · {{ forecast.orderCount }} 条记录 / {{ forecast.totalSales }} 件 · {{ forecast.observedDays }} 个有记录日 / {{ forecast.spanDays }} 天跨度 · 最近样本距今 {{ forecast.sampleAgeDays }} 天</p>
        <SalesBars :days="forecast.dailySales || []" :average="fmt(forecast.averageDailyDemand, 2)" :total="forecast.totalSales" />
        <p class="muted small">图中仅展示有记录日期；空缺日期不补零。区间参考 {{ fmt(forecast.averageDailyDemand, 2) }} 件/天；销售记录日均 {{ fmt(forecast.salesRecordDayAverage, 2) }} 件/天。两者均不冒充已核验完整自然日均。</p>
        <div v-if="forecast.risks?.length" class="risk-notes"><span v-for="r in forecast.risks" :key="r">{{ risks[r] || issueLabel(r) }}</span></div>
        <div class="table-scroll"><table class="ltable compact" aria-label="需求周期情景"><thead><tr><th>规划周期</th><th class="r">区间参考需求</th><th class="r">记录日均情景需求</th><th class="r">区间参考补充库存</th></tr></thead><tbody><tr v-for="s in decision.scenarios" :key="s.days"><td>{{ s.days }} 天{{ s.days === decision.horizonDays ? ' · 主周期' : '' }}</td><td class="r num">{{ fmt(s.forecastQuantity) }}</td><td class="r num">{{ fmt(s.recordDayScenarioQuantity) }}</td><td class="r num">{{ dash(s.referenceReplenishmentQuantity) }}</td></tr></tbody></table></div>
        <p class="muted small">两种需求是假设情景，不是统计置信区间。真实大单保留；已排除不可信状态和重复记录，不以删除异常销量调结果。</p>
        <BalanceChart v-if="decision.baseline?.series.length" :series="decision.baseline.series" />
      </template>
      <p v-else class="empty-inline">当前缺少可归属该店仓的可信历史，无法独立预测；ERP 原有建议仍可在下方查看。请核实支付、发货、退款状态与店仓关系。</p>
    </section>

    <section class="panel">
      <div class="panel-head"><h2>平台与 ERP 建议对比</h2><small>同业务范围 · 参考补充量口径</small></div>
      <div class="table-scroll"><table class="ltable compact" aria-label="ERP建议对比"><thead><tr><th>仓库</th><th class="r">平台参考补充</th><th class="r">ERP 原有建议</th><th class="r">平台减 ERP</th><th>说明</th></tr></thead><tbody><tr v-for="r in scopes" :key="r.entityKey"><td>{{ r.warehouseName || '仓库未关联' }}</td><td class="r num">{{ dash(r.decision?.referenceReplenishmentQuantity) }}</td><td class="r num">{{ r.erpComparison?.erpQuantity ?? (r.erpComparison?.status === 'ERP_AMBIGUOUS' ? '多条冲突' : 'ERP 未提供') }}</td><td class="r num">{{ dash(r.erpComparison?.difference) }}</td><td>{{ r.erpComparison?.significant ? '明显差异 · 核实口径' : r.erpComparison?.status === 'COMPARABLE' ? '同范围数量可比' : '不强行比较' }}</td></tr></tbody></table></div>
      <p class="muted small">{{ item.erpComparison?.explanation }}</p>
    </section>

    <section class="panel qualification"><div class="panel-head"><h2>分析建议与请购资格</h2><span class="chip" :class="item.procurementEligibility?.eligible && item.procurementEligibility?.scopeAuthorized ? 'confirm' : 'review'">{{ item.procurementEligibility?.eligible && item.procurementEligibility?.scopeAuthorized ? '可继续人工确认' : '采购条件待核实' }}</span></div>
      <p>需求预测 → 参考补充库存 → 满足采购约束的候选 → 人工确认最终数量。当前分析不创建 ERP 单据。</p>
      <details><summary>查看采购限制（不影响上方需求试算）</summary><ul class="business-reasons"><li v-for="b in item.procurementEligibility?.hardBlocks || []" :key="b">{{ issueLabel(b) }}</li><li v-if="!item.procurementEligibility?.scopeAuthorized">当前店仓未授予采购提交权限。</li></ul></details>
    </section>
  </div>
</template>

<style scoped>
.decision-product{display:grid;gap:18px}.overall-grid,.decision-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;padding:16px 20px}.overall-grid>div,.decision-kpis>div{display:grid;gap:5px}.overall-grid b{font-size:27px}.overall-grid span,.decision-kpis span{font-size:12px;color:#627081}.decision-kpis b{font-size:29px;font-weight:650}.decision-kpis small{font-size:12px;font-weight:400;margin-left:4px;color:#788795}.teal{color:#0f6b64}.business-reasons{margin:10px 20px 16px;padding-left:18px;line-height:1.9;font-size:13px}.planning-note,.sample-caption{padding:0 20px 12px;font-size:12px;color:#6c7b89}.overall>p,.panel>p{padding:10px 20px}.chosen{background:#edf7f3}.risk-notes{display:flex;gap:8px;flex-wrap:wrap;padding:8px 20px}.risk-notes span{font-size:11px;background:#fff6e8;color:#98652e;border-radius:4px;padding:4px 8px}.decision-product details{padding:10px 20px;color:#5f7080;font-size:12px}.decision-product summary{cursor:pointer;color:#0f6b64}.decision-product table{min-width:760px}.decision-product .table-scroll{overflow-x:auto}.decision-product :deep(.balance-chart){padding:16px}.decision-product :deep(svg){max-width:100%}@media(max-width:1000px){.decision-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:640px){.overall-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
