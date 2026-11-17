import type { Asset } from './api'

export function storeLabel(name?:string) {
  return name==='SIM-AS-20261116-R1-SHOP'?'澄屿生活馆 · 美国站':name || '—'
}

const reasons:Record<string,string>={
  CUSTOMER_MESSAGE_REQUIRED:'请先补充客户的问题，再生成回复。',
  EVIDENCE_UNVERIFIED:'订单资料未更新成功，请先重新核实订单。',
  EVIDENCE_REQUIRED:'请先核实订单资料。',
  CATEGORY_UNSUPPORTED:'这类商品尚无可用的回复政策，请先人工处理或联系主管维护政策。',
  BUSINESS_DATE_REQUIRED:'客户问题的业务日期待核实，请先更新订单资料。',
  POLICY_SCOPE_INCOMPLETE:'地区或平台待核实，请先更新订单资料。',
  POLICY_NOT_APPLICABLE:'没有匹配此商品、地区和日期的已发布政策，可补充政策或先填写回复。',
  B_MODEL_AUTHORIZATION_REQUIRED:'AI 暂不可用，请先人工填写回复。',
  B_MODEL_ALLOWANCE_UNAVAILABLE:'本次 AI 额度不足，请联系主管或先人工处理。',
  INVALID_OUTPUT:'AI 回复未通过校验，请重新生成或先人工填写。',
  TIMEOUT:'AI 响应超时，请稍后重试。',
  B_MODEL_CONTEXT_INVALID:'本次资料无法用于生成回复，请更新订单资料后重试。'
}
export function adviceReason(reason?:string) {return reasons[reason || ''] || '这次未生成回复，请稍后重试或先人工填写。'}
export function adviceResult(asset?:Asset) {
  const advice=asset?.body.advice?.at(-1)
  return advice?.ai.status==='AVAILABLE'?'回复已生成，请核对后保存。':adviceReason(advice?.ai.reason)
}
export function reviewData(asset:Asset,text:string,decision='SAVE',reason='') {
  if(decision!=='SAVE' && !reason.trim())throw new Error('请填写处理原因')
  const advice=asset.body.advice?.at(-1)
  const accepted=advice?.ai.status==='AVAILABLE' && advice.caseRevision===asset.revision
  const action=decision==='SAVE'?(accepted?'ACCEPT':'MANUAL'):decision
  return {adviceVersion:advice?.version || null,text,decision:action,
    reason:reason || (action==='ACCEPT'?'人工核对当前AI建议及回复后保存':'人工填写并核对回复后保存')}
}
