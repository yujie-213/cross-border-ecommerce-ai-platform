<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { request, errorText } from '../api/client'
import { init, openBatch, latestBatchId, state, loadRequisitions, requisitionRows } from '../s01'
import { resultDate, purchaseStatusTone } from '../business'
type Row = {erpId:string;erpNumber:string;skus:string[];warehouseName:string;status:string|null;previousStatus:string|null;verified:boolean;verifiedAt:string|null;error:string|null;receivedQuantity:number|null;pendingQuantity:number|null;quantities:{sku:string;ordered:number|null}[]}
type Tracking = {items:Row[];failedCount:number;checkedAt:string;coverage:string;registeredSkuCount?:number;discoveryErrors?:{warehouseName:string;code:string}[]}
const tracking = ref<Tracking|null>(null), loading=ref(false), error=ref(''), filter=ref('all')
let timer:ReturnType<typeof setTimeout>|undefined, alive=true, sequence=0
const rows=computed(()=> (tracking.value?.items || []).filter(r=>filter.value==='all' || filter.value==='unverified' ? filter.value==='all' || !r.verified : r.verified && r.status===filter.value))
const statuses=computed(()=> [...new Set((tracking.value?.items || []).filter(r=>r.verified).map(r=>r.status!))])
function action(row:Row){if(!row.verified)return '重新回读后再判断';if(row.status==='待审核')return '等待 ERP 审批';if(row.status==='待下单')return '在 ERP 核对下单安排';if(row.status==='已取消')return '核对是否仍有补货需要';return '按 ERP 当前状态跟进'}
async function refresh(){
 if(loading.value)return
 clearTimeout(timer);loading.value=true;error.value='';const mine=++sequence
 try{await init();const id=latestBatchId();if(!id)throw new Error('NO_BATCH');const next=await request<Tracking>('/s01/v2/purchase-status?batchId='+encodeURIComponent(id),{},undefined,90000);if(alive && mine===sequence)tracking.value=next}
 catch(e){if(alive && mine===sequence)error.value=e instanceof Error && e.message==='NO_BATCH' ? '先在智能补货工作区完成一次商品检查，才能核对关联采购。' : errorText(e)}
 finally{if(alive && mine===sequence){loading.value=false;timer=setTimeout(()=>{if(document.visibilityState==='visible')void refresh();else schedule()},60000)}}
}
function schedule(){clearTimeout(timer);timer=setTimeout(()=>{if(document.visibilityState==='visible')void refresh();else schedule()},60000)}
function foreground(){if(document.visibilityState==='visible')void refresh()}
onMounted(()=>{void refresh();document.addEventListener('visibilitychange',foreground)})
onUnmounted(()=>{alive=false;sequence++;clearTimeout(timer);document.removeEventListener('visibilitychange',foreground)})
</script>
<template>
 <div class="page purchase-tracking"><header class="page-head"><div><span class="eyebrow">智能补货 / 执行跟进</span><h1>请购与采购跟进</h1></div><div class="head-actions"><span class="check-time">{{ tracking ? '最近核对 '+resultDate(tracking.checkedAt) : '尚未核对' }}</span><button class="button primary" :disabled="loading" @click="refresh">{{ loading ? '正在回读 ERP…' : '刷新 ERP 状态' }}</button></div></header>
 <div v-if="loading" class="run-strip" role="status"><span class="spinner" /><b>正在更新 ERP 状态</b></div>
 <p v-if="error" class="banner danger" role="alert">{{ error }}<span v-if="tracking"> · 当前显示上次结果，不能视为最新状态。</span></p>
 <p v-if="tracking?.failedCount" class="banner warning">{{ tracking.failedCount }} 条单据核对失败，请刷新重试。</p>
 <p v-if="tracking?.discoveryErrors?.length" class="banner warning">部分仓库单据搜索失败，列表可能不完整。请刷新重试。</p>
 <div class="tracking-scope"><span class="live-dot" />{{ tracking?.registeredSkuCount ?? '—' }} 款登记商品<span v-if="tracking">{{ tracking.items.length }} 张关联单据</span></div>
 <section class="panel"><div class="tracking-tabs"><button :class="{active:filter==='all'}" @click="filter='all'">全部</button><button v-for="status in statuses" :key="status" :class="{active:filter===status}" @click="filter=status">{{ status }}</button><button v-if="tracking?.failedCount" :class="{active:filter==='unverified'}" @click="filter='unverified'">待核对</button></div><div class="table-scroll"><table class="ltable"><thead><tr><th>ERP 单据 / 商品</th><th>仓库</th><th>ERP 最新状态</th><th>采购数量</th><th>下一步</th><th>核对时间</th></tr></thead><tbody><tr v-for="row in rows" :key="row.erpId"><td><b class="cell-title">{{ row.erpNumber }}</b><small>{{ row.skus.join(' / ') }}</small></td><td>{{ row.warehouseName }}</td><td><span class="chip" :class="row.verified && !error ? purchaseStatusTone(row.status) : 'review'">{{ row.verified && !error ? row.status : '状态待核对' }}</span><small v-if="!row.verified">上次记录 {{ row.previousStatus || '未知' }}</small><small v-if="error && row.status">上次核对 {{ row.status }}</small></td><td><span v-for="line in row.quantities" :key="line.sku" class="tracking-quantity">{{ line.ordered ?? '—' }} 件</span></td><td>{{ error ? '重新核对后再判断' : action(row) }}</td><td>{{ row.verifiedAt ? resultDate(row.verifiedAt) : '未核对成功' }}</td></tr></tbody></table></div><div v-if="!rows.length && !loading" class="empty-state"><h3>{{ error ? '暂时无法取得 ERP 状态' : '当前没有关联采购单据' }}</h3></div></section>
 <details class="panel secondary-details"><summary @click="loadRequisitions()">本平台的提交记录</summary><div class="details-content"><p v-if="requisitionRows.loading">正在读取本地提交回执…</p><p v-if="requisitionRows.failed">部分提交记录读取失败，请核对原分析。</p><div v-for="row in requisitionRows.items.filter(r=>r.requisition)" :key="row.task.taskRef.taskId"><b>{{ row.task.sku }}</b> · {{ row.requisition?.erpNumber || '单号待核对' }} · 本地流程 {{ row.requisition?.state }}</div><p v-if="requisitionRows.loaded && !requisitionRows.items.some(r=>r.requisition)">暂无提交记录。</p></div></details>
 </div>
</template>
<style scoped>.tracking-scope{display:flex;align-items:center;gap:9px;color:var(--muted);font-size:12px;margin:20px 0}.tracking-scope>span:last-child{margin-left:auto}.live-dot{height:6px;width:6px;border-radius:50%;background:#1b8171}.tracking-tabs{display:flex;gap:8px;padding:18px;border-bottom:1px solid var(--line)}.tracking-tabs button{border:0;background:#f1f4f3;color:#6b7b76;padding:8px 15px;border-radius:6px;cursor:pointer}.tracking-tabs button.active{background:#e4f1ec;color:#126b65;font-weight:600}td small{display:block;margin-top:7px;color:var(--subtle);font-size:11px}.ltable td{padding:23px 18px}.tracking-quantity{display:block}.secondary-details{margin-top:24px}</style>
