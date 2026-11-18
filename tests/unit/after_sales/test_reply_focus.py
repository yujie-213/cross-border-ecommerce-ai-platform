import json

import pytest

from commerce_hub.scenarios.after_sales.model import Advice, Bundle
from commerce_hub.scenarios.after_sales.policies import reply_focus, retrieve, validate_policy
from commerce_hub.scenarios.after_sales.policy_templates import policy_starters


BUSINESS_DATE = '2026-11-17T12:00:00+08:00'


def case(*messages, category='APPAREL'):
    return dict(erpTicketId='91', identity={'category': category}, region='US', platform='Amazon', language='zh',
                messages=[dict(role='CUSTOMER', text=message) for message in messages])


def published_starters():
    return [dict(id=p['id'], state='PUBLISHED', revision=3, body=validate_policy({k:v for k,v in p.items() if k!='id'}))
            for p in policy_starters('US','Amazon')]


def test_praise_never_inherits_return_policy_or_solicits_followup():
    record = case('之前想问退货。', '尺码合适，发货及时，穿着舒服。')
    focus = reply_focus(record)
    assert focus == dict(topics=[], acknowledgmentOnly=True, safetySignal=False)
    assert retrieve(published_starters(), record, BUSINESS_DATE) == []
    bundle = Bundle({}, 'b.case.advice.v1', dict(policies=[], replyFocus=focus), Advice)
    output = dict(replyDraft='谢谢您的反馈，很高兴尺码合适，也让您穿得舒服。', adviceCode='CLARIFY',
                  citations=[], missingEvidence=[], escalation=False)
    assert bundle.validate_output(json.dumps(output)) == output
    for reply, error in [
        ('感谢反馈。如果后续需要换货或退货，请告诉我吊牌情况。', 'UNREQUESTED_RETURN_GUIDANCE'),
        ('谢谢您的反馈。您的订单已支付并已发货。', 'ACKNOWLEDGMENT_ADDED_ACTION'),
        ('感谢认可。请问还需要什么帮助吗？', 'ACKNOWLEDGMENT_ADDED_ACTION'),
    ]:
        with pytest.raises(ValueError, match=error):
            bundle.validate_output(json.dumps(output | dict(replyDraft=reply)))


@pytest.mark.parametrize('question,expected', [
    ('东西到哪了？能查运单吗？', 'shipping'),
    ('显示签收，但是我没收到。', 'delivery'),
    ('我想改地址，请问可以吗？', 'order-change'),
    ('请问这件衣服怎么洗？', 'product-info'),
    ('包裹缺件，少发一件。', 'item-issue'),
    ('支持开发票吗？', 'billing'),
])
def test_topic_specific_policy_with_older_unrelated_return(question, expected):
    record = case('上次我问过是否可退货。', question, category='UNKNOWN')
    assert {ref['policyId'] for ref in retrieve(published_starters(), record, BUSINESS_DATE)} == {expected}


def test_no_unpublished_rules_and_explicit_returns_still_work():
    record = case('尺码偏小，可以退货吗？')
    policies = published_starters()
    refs = retrieve(policies, record, BUSINESS_DATE)
    assert 'returns' in {ref['policyId'] for ref in refs}
    bundle = Bundle({}, 'b.case.advice.v1', dict(policies=refs, replyFocus=reply_focus(record)), Advice)
    citation = next(ref for ref in refs if ref['policyId'] == 'returns')
    output = dict(replyDraft='如果满足退换货条件，可以申请退货。请确认商品是否穿洗过。', adviceCode='CLARIFY',
                  citations=[{k:citation[k] for k in ('policyId','version','sectionId','hash')}], missingEvidence=[], escalation=False)
    assert bundle.validate_output(json.dumps(output)) == output
    assert retrieve([p | dict(state='DRAFT') for p in policies], record, BUSINESS_DATE) == []
    assert reply_focus(case('这件可以退货吗？','吊牌还在，没穿洗。'))['topics'] == ['RETURN']


def test_reply_without_policy_still_escalates_actual_safety_signal():
    focus = reply_focus(case('设备冒烟了。', '谢谢您。', category='ELECTRONICS'))
    assert focus['safetySignal'] and not focus['acknowledgmentOnly']
    bundle = Bundle({}, 'b.case.advice.v1', dict(policies=[], replyFocus=focus, safetySignal=True), Advice)
    result = dict(replyDraft='请先停止使用，我们会安排人工核查。', adviceCode='SAFETY_ESCALATE',
                  citations=[], missingEvidence=[], escalation=True)
    assert bundle.validate_output(json.dumps(result)) == result
