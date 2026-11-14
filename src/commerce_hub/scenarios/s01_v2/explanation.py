"""V2 facts through the accepted A01 gateway and controlled natural-language validator."""
from decimal import Decimal
import json
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.scenarios.s01.explanation import reserve_request,digest
from commerce_hub.scenarios.s01.natural_explanation import NaturalFact,NaturalExplanationContext,NaturalExplanationBundle
from commerce_hub.orchestration.budget import BudgetError


def product_bundle(item,binding):
    """Concise operator advice, each proposition grounded and machine validated."""
    import re
    d=item['decision'];f=d['forecast'];facts=[]
    def add(ref,text,section,unknown=False,required=True):
        facts.append(NaturalFact(ref=ref,kind='limitation' if unknown else 'evidence',text=text,allowedPhrases=[text],
            sections=[section],requiredSections=[section] if required else [],certainty='UNKNOWN' if unknown else 'KNOWN',
            allowedNumbers=re.findall(r'-?\d+(?:\.\d+)?',text),allowedDates=re.findall(r'\d{4}-\d{2}-\d{2}',text)))
    label='建议补货' if d['status']=='REPLENISH' else '暂不补货' if d['status']=='NO_REPLENISHMENT' else '依据不足，先核实销量或库存'
    add('scope',f"{item['warehouseName']}：{label}。仅限当前店铺，其他仓分别判断",'recommendationReasons')
    if f.get('available'):
        add('demand',f"{f['sampleStart']}至{f['sampleEnd']}的{f['observedDays']}个有记录日期共售{f['totalSales']}件，未来{d['horizonDays']}天参考需求约{Decimal(d['forecastQuantity']):.1f}件",'keyEvidence')
        days=f.get('dailySales',[])
        if len(days)>=3 and days[0]['quantity']!=days[-1]['quantity']:
            add('recent-sales',f"首日{days[0]['day']}售{days[0]['quantity']}件，最近{days[-1]['day']}售{days[-1]['quantity']}件；未来走势未知，核对近期活动，均值不保证未来销量",'majorRisks',True)
    else:add('demand','可信销售需求尚未确认，未支付或未发货订单不能当作有效销量，也不能把缺少样本当作零需求','keyEvidence',True)
    available=item['inventory']['available'];ref=d['referenceReplenishmentQuantity']
    if available is not None and ref is not None:
        add('stock',f"当前库存{available}件，参考补充{ref}件；该数量未扣尚未核实的在途",'keyEvidence')
    else:add('stock','库存缺口尚未确认，不能据此确定采购数量','keyEvidence',True)
    if d['stockoutRisk']:
        add('priority','有缺货风险：先核对已有采购及到货日期；若交期赶不上缺货，再评估加急或调拨','recommendationReasons')
    elif d['status']=='NO_REPLENISHMENT':
        add('priority','当前库存能够覆盖本次参考周期，暂不追加采购，继续观察销售变化','recommendationReasons')
    else:add('priority','先补齐可信销售或库存依据，再决定是否采购','recommendationReasons')
    compare=item['erpComparison']
    if compare['difference'] is not None:
        add('erp',f"平台参考补充{compare['platformQuantity']}件，ERP建议{compare['erpQuantity']}件，差{compare['difference']}件；ERP口径未知，先核对再决定",'recommendationReasons',True)
    else:add('erp',compare['explanation'],'recommendationReasons',compare['recordCount']>0)
    risks=f.get('risks',[])
    risk='未来需求是否延续历史尚未确认，参考预测不保证销量；'
    if 'STALE_SALES_SAMPLES' in risks:risk+='最近样本偏旧，应核实近期是否仍有需求'
    elif 'LOW_SALES_SAMPLE' in risks:risk+='样本较少，先观察新增销售再提高采购承诺'
    elif 'HISTORY_DATES_WITHOUT_RECORDS_UNKNOWN' in risks:risk+='未记录日期实际需求未知，应同时查看有记录日均情景'
    else:risk+='若近期销售突然变化，应结合逐日销量核对，避免均值掩盖变化'
    add('uncertainty',risk,'majorRisks',True)
    if item.get('pendingPurchases') or any(p.get('warehouseMatch') for p in item.get('formalPurchases',[])):
        add('duplicate','同商品同仓已有待审批申请或正式采购，店铺归属及可售日期尚未确认；暂停重复申请，先核对原单和实际未收数量，不将它们直接抵扣库存','majorRisks',True)
    else:add('supply','已有采购的归属和实际可售日期仍需确认；未知在途未抵扣，不能把参考补充直接当成最终采购量','majorRisks',True)
    c=item['constraints']
    if c['moq'] and c['orderMultiple'] and d['purchasableQuantity']:
        add('purchase',f"采购候选{d['purchasableQuantity']}件，起订{c['moq']}件、每箱{c['orderMultiple']}件；核对报价与已有采购，人工确认不代替ERP审批",'humanConfirmations')
    else:add('purchase','正数量采购条件尚未确认；先核实有效供应商、报价、起订量与整箱条件，需求分析仍可查看','humanConfirmations',True)
    context=NaturalExplanationContext(ref=dict(tenantId=binding['taskRef']['tenantId'],id='v2-facts-'+digest(dict(item=item,binding=binding))[:48],version='s01-product-experience-v1'),
        **binding,facts=facts,sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',trust='AUTHORIZED_FACTS_ONLY',sensitivity='MINIMIZED_BUSINESS_FACTS',omissions=['raw-source-response','procurement-authorization'])
    return NaturalExplanationBundle(context)


def bundle(item,binding):
    if item.get('explanationVersion')=='s01-purchase-advice-v2':
        from .purchase_advice import purchase_advice_bundle
        return purchase_advice_bundle(item,binding)
    if item.get('explanationVersion')=='s01-product-experience-v1':return product_bundle(item,binding)
    facts=[]
    def add(ref,text,section,*,numbers=(),dates=(),unknown=False):
        facts.append(NaturalFact(ref=ref,kind='limitation' if unknown else 'evidence',text=text,allowedPhrases=[text],
            sections=[section],requiredSections=[section],certainty='UNKNOWN' if unknown else 'KNOWN',
            allowedNumbers=list(map(str,numbers)),allowedDates=list(dates)))
    if item.get('decisionVersion'):
        decision=item['decision'];f=decision['forecast']
        add('source','本次需求与库存补充来自平台独立参考试算，ERP建议仅作比较，人工确认数量另行校验','recommendationReasons')
        for i,text in enumerate(decision['explanation']):
            import re
            add('business-'+str(i),text,'keyEvidence',numbers=re.findall(r'\d+(?:\.\d+)?',text))
        for i,text in enumerate(decision['assumptions']):
            import re
            add('assumption-'+str(i),'以下为未确认的试算假设：'+text,'majorRisks',numbers=re.findall(r'\d+(?:\.\d+)?',text),unknown=True)
        compare=item['erpComparison']
        add('erp-basis',compare['explanation'],'recommendationReasons',unknown=bool(compare['recordCount']))
        if compare['difference'] is not None:
            n=compare['difference'];text=f"平台参考补充量与ERP建议相差 {n} 件，ERP算法未知，无法确认具体成因"
            add('erp-difference',text,'keyEvidence',numbers=[n],unknown=True)
    elif item['sourceGrade']=='RULE_CALCULATED':
        add('source','本次数量来自平台规则计算，库存与销量经过质量核验','recommendationReasons')
    elif item['sourceGrade']=='REFERENCE_ONLY':
        add('source','本次结果来自 ERP 参考建议，内部计算依据仍未确认','recommendationReasons',unknown=True)
    else:add('source','当前无法形成可靠正数量补货依据，必要数据仍未确认','recommendationReasons',unknown=True)
    if item['quantity']:
        text=f"当前建议数量为 {item['quantity']} 件，最终数量仍由业务人员确认" if item['unit']=='EA' else f"当前源建议数量为 {item['quantity']}，计量单位仍未确认"
        add('quantity',text,'keyEvidence',numbers=[item['quantity']],unknown=item['unit']!='EA')
    elif item.get('decision',{}).get('status')=='NO_REPLENISHMENT':
        add('quantity','当前参考试算判断暂不补货；最终采购数量尚未确认','keyEvidence',unknown=True)
    elif item.get('decisionVersion'):add('quantity','正数量采购依据尚未确认；参考需求与采购候选应分开查看','keyEvidence',unknown=True)
    else:add('quantity','当前没有可靠的正数量建议，不能将零值或缺失解释为无需补货','keyEvidence',unknown=True)
    available=item['inventory']['available']
    if available is not None:add('inventory',f'本次读取的可用库存为 {available} 件' if item['unit']=='EA' else f'源库存值为 {available}，计量单位仍未确认','keyEvidence',numbers=[available],unknown=item['unit']!='EA')
    else:add('inventory','当前库存数量或业务归属未确认','keyEvidence',unknown=True)
    add('uncertainty','ERP 内部算法、统计窗口和既有采购抵扣语义未确认，不能自行推断' if item['sourceGrade']!='RULE_CALCULATED' else '质量和实际可售日期仍未确认，规则候选不能代替采购审批','majorRisks',unknown=True)
    add('eta','采购计划到货不等于可售日期，跨仓和晚到风险仍未确认','majorRisks',unknown=True)
    add('human','提交前必须由有权人员核对业务范围、供应商报价、数量和采购条件；人工确认不代替领导审批','humanConfirmations')
    if item.get('formalPurchases'):
        count=len(item['formalPurchases'])
        add('formal-purchases',f'已读取 {count} 条同 SKU 正式采购明细，可售日期和店铺归属仍未确认，未作为有效供给抵扣','majorRisks',numbers=[count],unknown=True)
    if item.get('ruleResult') and not item.get('decisionVersion'):
        f=item['ruleResult']['forecast']
        add('sales-window',f"最近 {f['observationDays']} 个完整业务日的已核验销量为 {f['totalSales']} 件，需求采用简单移动平均",'keyEvidence',numbers=[f['observationDays'],f['totalSales']])
    elif item.get('sourceSuggestion') and item['sourceSuggestion'].get('daily_sales') is not None:
        n=item['sourceSuggestion']['daily_sales']
        add('source-sales',f'ERP 记录的日均销量值为 {n}，统计窗口和计算口径仍未确认','keyEvidence',numbers=[n],unknown=True)
    if item['unit']=='EA' and item['constraints']['moq'] and item['constraints']['orderMultiple']:
        c=item['constraints'];add('constraints',f"最小起订量为 {c['moq']} 件，整箱倍数为 {c['orderMultiple']} 件，最终数量须同时满足两项约束",'humanConfirmations',numbers=[c['moq'],c['orderMultiple']])
    context=NaturalExplanationContext(ref=dict(tenantId=binding['taskRef']['tenantId'],id='v2-facts-'+digest(dict(item=item,binding=binding))[:48],version='s01-v2-facts-v1'),
        **binding,facts=facts,sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',trust='AUTHORIZED_FACTS_ONLY',sensitivity='MINIMIZED_BUSINESS_FACTS',omissions=['raw-source-response','procurement-authorization'])
    return NaturalExplanationBundle(context)


def explain(item,context,provider):
    binding=dict(taskRef=dict(tenantId=context.task['tenant_id'],taskId=context.task['task_id']),planVersion=str(context.task['plan_version']),snapshotId=item['snapshotRef'],participantId='s01')
    ai=dict(status='NOT_ATTEMPTED',reason='MODEL_NOT_ENABLED',explanation=None,binding=binding)
    if provider is None:return ai
    try:
        b=bundle(item,binding)
        logical='s01-v2-'+digest(binding)[:32]
        request=reserve_request(context,b,logical_call_id=logical,attempt_id=logical+'-1',max_tokens=24000,max_cost=Decimal('.05'),trace_id=digest(binding)[:32])
        response=ModelGateway(provider,timeout_seconds=30).invoke(request,context,b)
        ai['adviceVersion']=item.get('explanationVersion')
        ai.update(status='AVAILABLE' if response.status=='SUCCESS' else 'UNAVAILABLE',reason=response.code,
            explanation=response.validatedObject if response.status=='SUCCESS' else None,provider='AUTHORIZED_PROVIDER',
            usageStatus=response.usageStatus,tokenUsageStatus=response.tokenUsageStatus,costStatus=response.costStatus,
            usage=response.usage.model_dump(mode='json') if response.usage else None,usageRef=response.usageRef,
            actualModelRevision=response.actualModelRevision,auditRef=response.auditRef,versionBundle=response.versionBundle)
    except BudgetError:ai.update(status='UNAVAILABLE',reason='MODEL_ALLOWANCE_UNAVAILABLE')
    except (ValueError,TypeError,KeyError):ai.update(status='UNAVAILABLE',reason='AI_FACT_CONTEXT_INVALID')
    return ai


def validate_ai(ai,item):
    if ai.get('status')=='NOT_ATTEMPTED':
        if ai.get('reason') not in {'MODEL_NOT_ENABLED','ANALYSIS_ONLY_REQUEST'} or ai.get('explanation') is not None:raise ValueError('V2_AI_INVALID')
        return
    if ai.get('status') not in {'AVAILABLE','UNAVAILABLE'}:raise ValueError('V2_AI_INVALID')
    if ai.get('status')=='AVAILABLE':
        b=bundle(item,ai['binding']);refs=b.refs();versions=ai['versionBundle']
        for key in ['deploymentRef','promptRef','contextBundleRef','outputSchemaRef','parametersRef','cachePolicyRef']:
            if versions.get(key)!=refs[key]:raise ValueError('V2_AI_VERSION_INVALID')
        if versions.get('digests')!=b.resolve_content()[1]:raise ValueError('V2_AI_DIGEST_INVALID')
        b.validate_output(json.dumps(ai['explanation'],ensure_ascii=False))
    elif ai.get('explanation') is not None:raise ValueError('V2_AI_INVALID')
