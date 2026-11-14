"""D03 owns stable public admission capabilities and recovery explanations.

This projection is sealed as part of the existing immutable V2 result manifest.
It never rewrites a stored legacy report to claim a new admission decision.
"""
MESSAGES={
    'DEMAND_DAY_COVERAGE_INCOMPLETE':('部分日期缺少完整销量证据，可查看历史趋势，暂不能计算当前规则数量。','核对每日销售覆盖后重新分析'),
    'STOCK_MOVEMENT_COVERAGE_INCOMPLETE':('库存流水未完整获取，当前库存尚不能完成守恒核验。','重新读取库存流水或由负责人核实可信基点'),
    'STOCK_MOVEMENT_RECONCILIATION_FAILED':('库存与基点后的真实变动不一致。','核对出入库及调整凭证，不能直接重置期初'),
    'STOCK_EVENT_CHAIN_GAP':('库存流水之间存在余额断点。','补齐缺失凭证并独立回读'),
    'DUPLICATE_STOCK_EVENT':('库存流水存在重复记录。','核对来源分页与真实凭证'),
    'STOCK_EVENT_TYPE_UNSUPPORTED':('当前库存变动类型尚未完成接口核验。','保留事实并由负责人核验事件语义'),
    'INBOUND_POSTING_PROOF_MISSING':('检测到入库流水，但缺少独立过账凭证。','核对真实入库及可售状态，不将数量直接加为有效供给'),
    'ACQUISITION_TIME_BOUNDARY_EXPIRED':('本次采集已跨业务日或超过有效时限。','新建分析以读取当前事实，旧任务保留原时间'),
}


def failed_admission(code):
    return dict(admissionVersion='s01-runtime-v1',
        dataQuality={k:dict(status='UNKNOWN',reasons=[code]) for k in ('identity','demand','inventory','procurement')},
        demandWindow=None,inventoryBasis=None,riskResult=None,
        capabilities={k:dict(enabled=False,reasons=[code]) for k in ('facts','reference','risk','rules','requisition')},
        recoveryHints=[dict(code=code,message='本次数据处理未完成，历史报告仍可查看。',action='核对失败原因后重新分析')])


def public_admission(admission,item,*,requisition_authorized=None):
    rules=admission['ruleResult'];risk=(rules or {}).get('supplyDemand',{}).get('baseline')
    window=admission['demandWindow'];basis=admission['inventoryBasis']
    def capability(enabled,reasons):return dict(enabled=bool(enabled),reasons=[] if enabled else reasons)
    failures=admission['ruleFailureCodes'];quality=admission['dataQuality']
    codes=sorted(set(failures+item['procurementEligibility']['hardBlocks']))
    hints=[dict(code=code,message=MESSAGES.get(code,('相关业务条件尚未核实，当前能力受到限制。','核对相关业务条件后重新分析'))[0],
                action=MESSAGES.get(code,('','核对相关业务条件后重新分析'))[1]) for code in codes]
    write_reasons=item['procurementEligibility']['hardBlocks'][:]
    if requisition_authorized is not True:write_reasons.append('WRITE_SCOPE_NOT_EVALUATED' if requisition_authorized is None else 'WRITE_SCOPE_NOT_AUTHORIZED')
    return dict(admissionVersion=admission['admissionVersion'],dataQuality=quality,demandWindow=window,inventoryBasis=basis,
        riskResult=risk,capabilities=dict(
            facts=capability(quality['identity']['status']=='VERIFIED',['IDENTITY_OR_UNIT_UNVERIFIED']),
            reference=capability(bool(window['observedHistory']) or item['sourceSuggestion'] is not None,['NO_OBSERVED_REFERENCE_SAMPLE']),
            risk=capability(risk is not None,failures),
            rules=capability(rules is not None and not admission['riskOnly'],failures or item['constraints']['hardBlocks']),
            requisition=dict(capability(item['procurementEligibility']['eligible'] and requisition_authorized is True,write_reasons),
                permissionCheck='G01_RECHECK_REQUIRED_AT_SUBMISSION')),
        recoveryHints=hints,observedAt=basis.get('observedAt') or item['observedAt'])
