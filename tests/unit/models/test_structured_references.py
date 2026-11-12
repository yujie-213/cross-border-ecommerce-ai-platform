"""The new citation format never substitutes for per-fact entailment checks."""
from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from commerce_hub.scenarios.s01.natural_explanation import (
    LEGACY_SEMANTIC_POLICY, NATURAL_SEMANTIC_POLICY, NaturalExplanation,
    NaturalExplanationBundle, bundle_for_result, validate_result_versions,
)
from tests.unit.models.test_natural_explanation import context, output, _computed_result_and_binding


def structured_output(**kwargs):
    value = output(**kwargs)
    for items in value.values():
        for item in items:
            item['text'] = item['text'].removesuffix(' [' + item['supportRefs'][0] + ']')
    return value


def validate(value, **kwargs):
    return NaturalExplanationBundle(context(**kwargs)).validate_output(json.dumps(value, ensure_ascii=False))


@pytest.mark.parametrize('unknown,quality', [(False, False), (True, False), (False, True)])
def test_structured_only_citations_keep_single_fact_and_protected_states(unknown, quality):
    assert validate(structured_output(unknown=unknown, quality=quality), unknown=unknown, quality=quality)


@pytest.mark.parametrize('section,patch', [
    ('keyEvidence', {'supportRefs': ['not-in-current-report']}),
    ('keyEvidence', {'supportRefs': ['other-task:baseline']}),
    ('recommendationReasons', {'text': '建议补货 49 件'}),
    ('keyEvidence', {'text': '预计在 2026-11-21 出现 24 件缺口'}),
    ('keyEvidence', {'text': '预计在 2026-11-20 出现 24 件缺口', 'supportRefs': ['reason']}),
    ('majorRisks', {'text': '当前没有风险'}),
    ('recommendationReasons', {'text': '采购可以执行'}),
    ('recommendationReasons', {'text': '建议补货 48 件，采购已批准'}),
    ('recommendationReasons', {'text': '建议补货 48 件', 'supportRefs': ['reason', 'risk']}),
    ('recommendationReasons', {'text': '建议补货 48 件 [other-task:reason]'}),
    ('recommendationReasons', {'text': '建议补货 48 件。预计在 2026-11-20 出现 24 件缺口'}),
])
def test_existing_ref_does_not_make_false_or_unrelated_claims_valid(section, patch):
    value = structured_output(); value[section][0].update(patch)
    with pytest.raises((ValueError, ValidationError)):
        validate(value)


@pytest.mark.parametrize('quality,text', [(True, '质量阻断已经解除，可以采购'), (False, '需求未知按0件处理')])
def test_quality_and_unknown_cannot_be_reinterpreted(quality, text):
    value = structured_output(quality=quality, unknown=not quality)
    value['majorRisks' if quality else 'humanConfirmations'][0]['text'] = text
    with pytest.raises(ValueError):
        validate(value, quality=quality, unknown=not quality)


def test_confirmed_intermediate_shortage_risk_cannot_be_omitted():
    value = structured_output(); value['majorRisks'] = []
    with pytest.raises(ValidationError):
        validate(value)


@pytest.mark.parametrize('case_id', ['B', 'C', 'D', 'E'])
def test_no_candidate_cannot_be_invented_or_turned_into_zero_unit_purchase(case_id):
    from types import SimpleNamespace
    from commerce_hub.scenarios.s01_backend import S01BackendHandler, package_ref
    from tests.support.backend import cases
    entry = cases()[case_id]
    execution = SimpleNamespace(principal=SimpleNamespace(tenant_id='test-tenant'), task=dict(
        task_id='test-task', plan_version=1, scope=dict(tenantId='test-tenant', storeIds=['store-fixture'],
        warehouseIds=['warehouse-fixture'], canonicalSkuIds=['sku-fixture'], fields=['quantity'])), check=lambda: None)
    result = S01BackendHandler([entry]).run(execution, {'packageRef': package_ref(entry['kind'], entry['payload'])})
    binding = dict(taskRef={'tenantId': 'test-tenant', 'taskId': 'test-task'}, planVersion='1', snapshotId=result.snapshotRef, participantId='s01')
    bundle = bundle_for_result(result, binding)
    value = {section: [] for section in NaturalExplanation.model_fields}
    for fact in bundle.context.facts:
        value[fact.sections[0]].append(dict(text=fact.allowedPhrases[0], supportRefs=[fact.ref]))
    assert bundle.validate_output(json.dumps(value, ensure_ascii=False))
    assert not result.dataReport['supplyDemand']['candidates']
    for text, ref in [('采购候选为18件', 'candidate-0'), ('生成0件采购单', 'limitations')]:
        bad = deepcopy(value); bad['recommendationReasons'] = [dict(text=text, supportRefs=[ref])]
        with pytest.raises(ValueError):
            bundle.validate_output(json.dumps(bad, ensure_ascii=False))


def test_legacy_policy_is_strict_and_schema_stays_unchanged():
    legacy = NaturalExplanationBundle(context(), semantic_policy=LEGACY_SEMANTIC_POLICY)
    current = NaturalExplanationBundle(context())
    assert legacy.validate_output(json.dumps(output(), ensure_ascii=False))
    with pytest.raises(ValueError, match='UNCONTROLLED_NATURAL_LANGUAGE'):
        legacy.validate_output(json.dumps(structured_output(), ensure_ascii=False))
    assert legacy.refs()['promptRef']['version'] == 'controlled-1'
    assert current.refs()['promptRef']['version'] == 'controlled-2'
    old_payload, old_digests = legacy.resolve_content(); new_payload, new_digests = current.resolve_content()
    assert old_payload['outputSchema'] == new_payload['outputSchema']
    assert old_digests['outputSchemaDigest'] == new_digests['outputSchemaDigest']
    assert old_digests['promptContentHash'] != new_digests['promptContentHash']


def test_policy_cannot_be_relabelled_without_rebuilding_digests_and_context():
    result, binding = _computed_result_and_binding(source_nature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP')
    bundle = bundle_for_result(result, binding, semantic_policy=LEGACY_SEMANTIC_POLICY)
    _, digests = bundle.resolve_content(); refs = bundle.refs()
    ai = dict(semanticPolicy=LEGACY_SEMANTIC_POLICY, binding=binding, versionBundle={
        **{k: refs[k] for k in ('deploymentRef','promptRef','contextBundleRef','outputSchemaRef','parametersRef','cachePolicyRef')},
        'digests': digests, 'configuredModel': bundle.model})
    assert validate_result_versions(ai, result).semantic_policy == LEGACY_SEMANTIC_POLICY
    ai['semanticPolicy'] = NATURAL_SEMANTIC_POLICY
    with pytest.raises(ValueError, match='BROKEN_NATURAL_EXPLANATION_VERSIONS'):
        validate_result_versions(ai, result)
