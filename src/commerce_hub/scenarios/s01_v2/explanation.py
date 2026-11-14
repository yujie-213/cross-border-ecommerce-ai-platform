"""V2 facts through the accepted A01 gateway and controlled natural-language validator."""
from decimal import Decimal
import json
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.scenarios.s01.explanation import reserve_request,digest
from commerce_hub.scenarios.s01.natural_explanation import NaturalFact,NaturalExplanationContext,NaturalExplanationBundle
from commerce_hub.orchestration.budget import BudgetError


def bundle(item,binding):
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
    else:add('quantity','正数量采购依据尚未确认；参考需求与采购候选应分开查看','keyEvidence',unknown=True)
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
        if ai.get('reason')!='MODEL_NOT_ENABLED' or ai.get('explanation') is not None:raise ValueError('V2_AI_INVALID')
        return
    if ai.get('status') not in {'AVAILABLE','UNAVAILABLE'}:raise ValueError('V2_AI_INVALID')
    if ai.get('status')=='AVAILABLE':
        b=bundle(item,ai['binding']);refs=b.refs();versions=ai['versionBundle']
        for key in ['deploymentRef','promptRef','contextBundleRef','outputSchemaRef','parametersRef','cachePolicyRef']:
            if versions.get(key)!=refs[key]:raise ValueError('V2_AI_VERSION_INVALID')
        if versions.get('digests')!=b.resolve_content()[1]:raise ValueError('V2_AI_DIGEST_INVALID')
        b.validate_output(json.dumps(ai['explanation'],ensure_ascii=False))
    elif ai.get('explanation') is not None:raise ValueError('V2_AI_INVALID')
