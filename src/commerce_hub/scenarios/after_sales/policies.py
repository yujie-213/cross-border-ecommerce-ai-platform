"""A03 lightweight authorized exact filtering, then keyword ranking. No embeddings."""
import re

from .common import digest, timestamp, require, safety


TOPIC_WORDS = {
    'SIZE': ('尺码', '尺寸', '偏小', '偏大', 'size', 'sizing', 'measurements'),
    'DESCRIPTION': ('描述', '说明书', '和图片', '实物不符', 'description', 'as pictured'),
    'SAFETY': ('冒烟', '发热', '起火', '漏电', '触电', '烫伤', 'smoke', 'fire', 'burn'),
    'FUNCTION': ('故障', '断开', '无法使用', '用不了', '不工作', 'does not work'),
    'COMPATIBILITY': ('兼容', '接口', '适配', 'compatible', 'compatibility'),
    'RETURN': ('退换', '退货', '退款', '换货', '退回', '退掉', '寄回', '退运费', '退钱', '退单', 'refund', 'return', 'exchange', 'send it back', 'money back'),
    'LOGISTICS': ('物流', '什么时候发货', '何时发货', '多久发', '还没发货', '到哪', '什么时候到', '运单', '到货时间', 'shipping', 'tracking', 'ship out', 'delivery date'),
    'NOT_RECEIVED': ('没收到', '未收到', '收不到', '显示签收', '送错', '丢件', '包裹丢', 'not received', 'not delivered', 'missing package', 'marked delivered'),
    'ORDER_CHANGE': ('改地址', '修改地址', '改收件', '修改订单', '改订单', '取消订单', '取消发货', '取消这单', 'change address', 'change my order', 'cancel'),
    'PRODUCT_INFO': ('材质', '成分', '怎么用', '使用方法', '怎么洗', '如何清洗', '保养', '可以水洗', '洗涤', '说明书', 'material', 'care instructions', 'wash', 'how to use'),
    'ITEM_ISSUE': ('破损', '开裂', '断裂', '漏发', '少发', '缺件', '错发', '发错', '多发', '包装破', '损坏', '开线', 'damaged', 'broken', 'wrong item', 'missing item'),
    'PAYMENT': ('支付失败', '扣款', '付款', '发票', '收据', '优惠券', '优惠码', '折扣', 'invoice', 'receipt', 'charge', 'coupon', 'discount', 'payment'),
}
PRAISE = ('感谢', '谢谢', '很满意', '很喜欢', '非常满意', '尺码合适', '发货及时', '发货很快', '穿着舒服',
          '穿着舒适', '做工很好', '质量不错', '好评', 'thank you', 'thanks', 'love it', 'very happy', 'fits well')
REQUEST_CUES = ('不', '但', '想', '希望', '请问', '怎么', '如何', '何时', '多少', '需要', '能否', '是否',
                '可以', '麻烦', '建议', '遗憾', '问题', '？', '?', ' but ', ' how ', ' can ', ' please ', ' wish ')
DECLINES_RETURN = re.compile(r'(?:不用|不想|不需要|无需|不要|不考虑)(?:申请|办理|再)?(?:退换|退货|退款|换货)|no (?:refund|return|exchange)|don.t (?:need|want) (?:a )?(?:refund|return|exchange)', re.I)
RETURN_OUTPUT = (
    *TOPIC_WORDS['RETURN'], '退件', '更换商品', '更换一件', '换一件', '换一款', '换个', '换成其他',
    '更换尺码', '换尺码', 'replacement', 'request a new one',
)


def _contains(text, terms):
    return any(re.search(r'(?<![a-z])' + re.escape(term) + r'(?![a-z])', text) if term.isascii()
               else term in text for term in terms)


def reply_focus(case):
    """Route on the customer's latest turn; keep safety signals from the full case."""
    messages = [m['text'] for m in case.get('messages', []) if m.get('role', 'CUSTOMER') == 'CUSTOMER']
    latest = messages[-1].lower() if messages else ''
    topic_text = latest.replace('尺码合适', '').replace('尺码很合适', '').replace('size fits well', '')
    topics = {topic for topic, terms in TOPIC_WORDS.items() if _contains(topic_text, terms)}
    declines_return = bool(DECLINES_RETURN.search(latest))
    if declines_return:
        topics.discard('RETURN')
    # A follow-up that only supplies an answer to a requested condition can
    # continue the immediately preceding customer's explicit return request.
    if not declines_return and len(messages) > 1 and not topics and _contains(latest, ('吊牌', '未穿洗', '没有穿洗', '未使用')):
        prior = messages[-2].lower()
        if not DECLINES_RETURN.search(prior) and _contains(prior, TOPIC_WORDS['RETURN']):
            topics.add('RETURN')
    safety_signal = safety(' '.join(messages))
    if safety_signal:
        topics.add('SAFETY')
    acknowledgment = not topics and _contains(latest, PRAISE) and not any(cue in latest for cue in REQUEST_CUES)
    return dict(topics=sorted(topics), acknowledgmentOnly=acknowledgment, safetySignal=safety_signal)


def advice_block_reason(case):
    """Explain the first unmet prerequisite without widening policy applicability."""
    evidence=case.get('evidence') or {}
    if not case.get('messages'):return 'CUSTOMER_MESSAGE_REQUIRED'
    if evidence.get('latestUnverified'):return 'EVIDENCE_UNVERIFIED'
    if not evidence.get('facts'):return 'EVIDENCE_REQUIRED'
    if not case.get('identity'):return 'IDENTITY_UNRESOLVED'
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


def retrieve(policies,case,business_date,*,focus=None):
    focus = focus if focus is not None else reply_focus(case)
    if focus['acknowledgmentOnly']:
        return []
    query = next((m['text'].lower() for m in reversed(case['messages']) if m.get('role','CUSTOMER') == 'CUSTOMER'), '')
    active = set(focus['topics'])
    selected=[]
    for p in policies:
        if not applicable(p,case,business_date):continue
        topics = p['body']['topics']
        if focus['safetySignal'] and 'SAFETY_ESCALATE' not in p['body']['terms']:continue
        if not focus['safetySignal'] and 'SAFETY' in topics and 'SAFETY_ESCALATE' in p['body']['terms']:continue
        # Preserve literal matching for user-defined topics, but only use a
        # reserved topic when the latest customer turn actually calls for it.
        if 'RETURN' in topics and 'RETURN' not in active and not (set(topics) & active):continue
        score = sum(word in active or word == 'REPLY' and _contains(query, ('回复','补证'))
                    or word not in TOPIC_WORDS and word != 'REPLY' and _contains(query, (word.lower(),))
                    for word in topics)
        if not score:continue
        for s in p['body']['sections']:
            selected.append(dict(policyId=p['id'],version=p['revision'],sectionId=s['id'],hash=digest(s),text=s['text'],
                terms=p['body']['terms'],title=p['body']['title'],applicability='来源、地区、平台、语言、商品类目和业务日均匹配',
                score=score))
    return sorted(selected,key=lambda s:(-s['score'],s['policyId']))[:8]


def validate_advice(output,refs,*,focus=None):
    require(isinstance(output,dict) and set(output)=={'replyDraft','adviceCode','citations','missingEvidence','escalation'},'AI_SCHEMA_INVALID')
    require(output['adviceCode'] in {'CLARIFY','MANUAL_REVIEW','SAFETY_ESCALATE'},'UNSUPPORTED_PROMISE')
    allowed={(s['policyId'],s['version'],s['sectionId'],s['hash']):s for s in refs}
    require(isinstance(output['citations'],list) and (bool(output['citations']) if refs else not output['citations']),'CITATIONS_REQUIRED')
    if not refs and not (focus and focus['safetySignal']):require(output['adviceCode'] in {'CLARIFY','MANUAL_REVIEW'},'UNSUPPORTED_PROMISE')
    for c in output['citations']:
        require(isinstance(c,dict) and set(c)=={'policyId','version','sectionId','hash'} and tuple(c[k] for k in ('policyId','version','sectionId','hash')) in allowed,'CITATION_FORGED')
        require(output['adviceCode'] in allowed[tuple(c[k] for k in ('policyId','version','sectionId','hash'))]['terms'],'UNSUPPORTED_PROMISE')
    text=output['replyDraft']
    require(isinstance(text,str) and 0<len(text)<=4000 and not any(w in text.lower() for w in ('保证','已经退款','已退款','到账','认证安全','拆机','guarantee','refund issued','已确认缺陷','确定质量问题','绝对安全','已补发','赔偿')),'UNSUPPORTED_PROMISE')
    require(not any(w in text for w in ('建议客服','客服应','请客服','转人工核实后回复')),'INTERNAL_INSTRUCTION_IN_REPLY')
    # Unconstrained free numeric/date/currency promises are not accepted as AI prose.
    require(not re.search(r'\d|[¥$€]',text),'UNSUPPORTED_NUMERIC_CLAIM')
    require(isinstance(output['missingEvidence'],list) and all(isinstance(x,str) for x in output['missingEvidence']) and type(output['escalation']) is bool,'AI_SCHEMA_INVALID')
    if focus:
        if 'RETURN' not in focus['topics']:
            require(not _contains(text.lower(), RETURN_OUTPUT),'UNREQUESTED_RETURN_GUIDANCE')
        if focus['acknowledgmentOnly']:
            require(not output['missingEvidence'] and not output['escalation'] and '?' not in text and '？' not in text
                    and not _contains(text.lower(), ('已支付','已发货','无退款','请提供','请问','麻烦您','确认订单','查看物流',
                                                      'please provide','order status','paid','has shipped')),
                    'ACKNOWLEDGMENT_ADDED_ACTION')
    return output
