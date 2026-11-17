"""A03 lightweight authorized exact filtering, then keyword ranking. No embeddings."""
from .common import digest, timestamp, require


def advice_block_reason(case):
    """Explain the first unmet prerequisite without widening policy applicability."""
    evidence=case.get('evidence') or {}
    if not case.get('messages'):return 'CUSTOMER_MESSAGE_REQUIRED'
    if evidence.get('latestUnverified'):return 'EVIDENCE_UNVERIFIED'
    if not evidence.get('facts'):return 'EVIDENCE_REQUIRED'
    if (case.get('identity') or {}).get('category') not in {'APPAREL','ELECTRONICS'}:return 'CATEGORY_UNSUPPORTED'
    if not case.get('businessDate'):return 'BUSINESS_DATE_REQUIRED'
    if any(case.get(k) in (None,'','UNKNOWN') for k in ('region','platform','language')):return 'POLICY_SCOPE_INCOMPLETE'
    return None


def validate_policy(body):
    required={'title','category','topics','sections','region','platform','language','effectiveFrom','effectiveUntil','source','terms'}
    require(isinstance(body,dict) and set(body)==required,'POLICY_INVALID')
    require(all(isinstance(body[k],str) and 0<len(body[k])<=1000 for k in ('title','category','region','platform','language','source')),'POLICY_INVALID')
    require(isinstance(body['topics'],list) and all(isinstance(t,str) and 0<len(t)<=100 for t in body['topics']) and len(body['topics'])<=30,'POLICY_INVALID')
    require(body['category'] in {'APPAREL','ELECTRONICS','ALL'} and body['region'] and body['platform'] and body['source'],'POLICY_SCOPE_REQUIRED')
    require(timestamp(body['effectiveFrom'])<timestamp(body['effectiveUntil']),'POLICY_DATES_INVALID')
    require(isinstance(body['sections'],list) and 1<=len(body['sections'])<=8,'POLICY_SECTIONS_INVALID')
    ids=set()
    for s in body['sections']:
        require(isinstance(s,dict) and set(s)=={'id','text'} and isinstance(s['id'],str) and 0<len(s['id'])<=64 and s['id'] not in ids and isinstance(s['text'],str) and 0<len(s['text'])<=4000,'POLICY_SECTION_INVALID')
        ids.add(s['id'])
    require(isinstance(body['terms'],list) and all(isinstance(t,str) for t in body['terms']) and set(body['terms'])<={'CLARIFY','MANUAL_REVIEW','SAFETY_ESCALATE'} and body['terms'],'POLICY_TERMS_INVALID')
    require('teacher' not in str(body).lower(),'TEACHER_ASSET_FORBIDDEN')
    return body


def applicable(policy,case,business_date):
    body=policy['body']; identity=case.get('identity') or {}
    return (policy['state']=='PUBLISHED' and business_date and identity.get('category')
        and body['category'] in {identity['category'],'ALL'} and body['region']==case.get('region')
        and body['platform']==case.get('platform') and body['language']==case.get('language')
        and timestamp(body['effectiveFrom'])<=timestamp(business_date)<timestamp(body['effectiveUntil']))


def retrieve(policies,case,business_date):
    selected=[];query=' '.join(m['text'] for m in case['messages'])
    keywords={'SIZE':['尺码','尺寸','大小'],'DESCRIPTION':['描述','说明'],'SAFETY':['冒烟','发热','起火','漏电'],
        'FUNCTION':['故障','断开','无法使用'],'COMPATIBILITY':['兼容','接口'],'RETURN':['退货','退款'],'REPLY':['回复','补证']}
    for p in policies:
        if not applicable(p,case,business_date):continue
        for s in p['body']['sections']:
            selected.append(dict(policyId=p['id'],version=p['revision'],sectionId=s['id'],hash=digest(s),text=s['text'],
                terms=p['body']['terms'],title=p['body']['title'],applicability='来源、地区、平台、语言、商品类目和业务日均匹配',
                score=sum(word.lower() in query.lower() or any(k in query for k in keywords.get(word,[])) for word in p['body']['topics'])))
    return sorted(selected,key=lambda s:(-s['score'],s['policyId']))[:8]


def validate_advice(output,refs):
    require(isinstance(output,dict) and set(output)=={'replyDraft','adviceCode','citations','missingEvidence','escalation'},'AI_SCHEMA_INVALID')
    require(output['adviceCode'] in {'CLARIFY','MANUAL_REVIEW','SAFETY_ESCALATE'},'UNSUPPORTED_PROMISE')
    allowed={(s['policyId'],s['version'],s['sectionId'],s['hash']):s for s in refs}
    require(isinstance(output['citations'],list) and output['citations'],'CITATIONS_REQUIRED')
    for c in output['citations']:
        require(isinstance(c,dict) and set(c)=={'policyId','version','sectionId','hash'} and tuple(c[k] for k in ('policyId','version','sectionId','hash')) in allowed,'CITATION_FORGED')
        require(output['adviceCode'] in allowed[tuple(c[k] for k in ('policyId','version','sectionId','hash'))]['terms'],'UNSUPPORTED_PROMISE')
    text=output['replyDraft']
    require(isinstance(text,str) and 0<len(text)<=4000 and not any(w in text.lower() for w in ('保证','已经退款','已退款','到账','认证安全','拆机','guarantee','refund issued','已确认缺陷','确定质量问题','绝对安全','已补发','赔偿')),'UNSUPPORTED_PROMISE')
    require(not any(w in text for w in ('建议客服','客服应','请客服','转人工核实后回复')),'INTERNAL_INSTRUCTION_IN_REPLY')
    # Unconstrained free numeric/date/currency promises are not accepted as AI prose.
    import re
    require(not re.search(r'\d|[¥$€]',text),'UNSUPPORTED_NUMERIC_CLAIM')
    require(isinstance(output['missingEvidence'],list) and all(isinstance(x,str) for x in output['missingEvidence']) and type(output['escalation']) is bool,'AI_SCHEMA_INVALID')
    return output
