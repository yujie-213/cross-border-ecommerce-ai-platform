"""Isolated buyer scenarios; not live ERP or model evidence."""
from copy import deepcopy
import json
import pytest
from tests.unit.data.test_product_demand import fixture
from commerce_hub.scenarios.s01_v2.analysis import analyze
from commerce_hub.scenarios.s01_v2.explanation import bundle
from commerce_hub.scenarios.s01_v2.purchase_advice import VERSION


def advice(item):
    return bundle(item, dict(taskRef=dict(tenantId='fixture',taskId='advice-test'),
        planVersion='1',snapshotId=item['ruleResult']['snapshotId'] if item.get('ruleResult') else 'fixture-snapshot',participantId='s01'))


def output(b):
    value = dict(recommendationReasons=[],keyEvidence=[],majorRisks=[],humanConfirmations=[])
    for fact in b.context.facts:
        for section in fact.requiredSections:
            value[section].append(dict(text=fact.allowedPhrases[0],supportRefs=[fact.ref]))
    return value


def test_buyer_advice_explains_quantity_rounding_and_arrival_gap(tmp_path):
    _,reader,c,e=fixture(tmp_path)
    item=analyze(c,e,reader);b=advice(item)
    assert item['explanationVersion']==VERSION
    text={f.ref:f.text for f in b.context.facts}
    assert '普通采购可能赶不上' in text['conclusion']
    assert '参考补充30件' in text['quantity-basis'] and '32件' in text['quantity-basis']
    assert '整箱倍数8件' in text['quantity-basis']
    assert item['decision']['firstShortageDate'] in text['next-step']
    value=output(b)
    assert b.validate_output(json.dumps(value,ensure_ascii=False))==value
    assert b.refs()['promptRef']['version']=='buyer-2'


def test_missing_quote_and_sufficient_stock_have_different_decisions(tmp_path):
    _,reader,c,e=fixture(tmp_path,quotes=False)
    no_quote=analyze(c,e,reader);text={f.ref:f.text for f in advice(no_quote).context.facts}
    assert '补齐有效报价' in text['conclusion'] and '唯一有效' in text['next-step']
    assert 'lead-unknown' in text and no_quote['decision']['purchasableQuantity'] is None
    c['inventory']['rows'][0]['available']=500
    enough=analyze(c,e,reader);text={f.ref:f.text for f in advice(enough).context.facts}
    assert '无需追加采购' in text['conclusion'] and '暂不新增' in text['next-step']
    assert '调拨' not in text['next-step']


def test_existing_purchases_take_priority_over_new_procurement(tmp_path):
    _,reader,c,e=fixture(tmp_path)
    c['pendingPurchases']=dict(complete=True,rows=[dict(id=88,status_text='待审核',order_sn='pending',
        warehouse_name='Synthetic Warehouse',item_list=[dict(sku=e['sku'],quantity=32)])])
    item=analyze(c,e,reader);b=advice(item);text={f.ref:f.text for f in b.context.facts}
    assert '避免重复请购' in text['conclusion'] and '原单状态' in text['next-step']
    assert not item['procurementEligibility']['eligible']


@pytest.mark.parametrize('fault',['number','ref','omit-quantity','omit-risk','approval','duplicate'])
def test_advice_cannot_invent_or_omit_decision_critical_facts(tmp_path,fault):
    _,reader,c,e=fixture(tmp_path);b=advice(analyze(c,e,reader));value=output(b)
    if fault=='number':value['keyEvidence'][0]['text']='当前库存999件'
    elif fault=='ref':value['keyEvidence'][0]['supportRefs']=['other-warehouse']
    elif fault=='omit-quantity':value['keyEvidence']=[x for x in value['keyEvidence'] if x['supportRefs']!=['quantity-basis']]
    elif fault=='omit-risk':value['majorRisks']=[]
    elif fault=='approval':value['recommendationReasons'][0]['text']='采购已批准，请下单'
    else:value['humanConfirmations']*=2
    with pytest.raises(ValueError):b.validate_output(json.dumps(value,ensure_ascii=False))


def test_sealed_legacy_bundle_keeps_original_versions_and_text(tmp_path):
    _,reader,c,e=fixture(tmp_path);item=analyze(c,e,reader)
    old=deepcopy(item);old['explanationVersion']='s01-product-experience-v1'
    legacy=advice(old)
    assert legacy.refs()['promptRef']['version']=='controlled-2'
    assert any(f.ref=='scope' for f in legacy.context.facts)
    assert not any(f.ref=='conclusion' for f in legacy.context.facts)
