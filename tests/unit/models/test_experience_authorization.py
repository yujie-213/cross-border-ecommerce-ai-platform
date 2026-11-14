"""No network: explicit new authorization preserves the old bounded policy."""
from decimal import Decimal
import pytest
from commerce_hub.adapters.models.online import OnlineDeepSeekProvider,V2_AUTHORIZATION_ID,EXPERIENCE_AUTHORIZATION_ID,WORKFLOW_AUTHORIZATION_ID,DAILY_USE_AUTHORIZATION_ID
from tests.unit.models.test_evaluation_provider import settings


@pytest.mark.parametrize('old_id',[V2_AUTHORIZATION_ID,WORKFLOW_AUTHORIZATION_ID])
@pytest.mark.parametrize('new_id',[EXPERIENCE_AUTHORIZATION_ID,DAILY_USE_AUTHORIZATION_ID])
def test_new_owner_authorization_is_separate_and_keeps_per_call_reservation(tmp_path,old_id,new_id):
    old=OnlineDeepSeekProvider(settings(),tmp_path/'old',authorization_id=old_id).delegate.authorization
    new=OnlineDeepSeekProvider(settings(),tmp_path/'new',authorization_id=new_id).delegate.authorization
    assert old.max_requests==4 and old.max_total_cost_usd==Decimal('.20')
    assert new.authorization_id!=old.authorization_id and new.max_requests is None and new.max_total_cost_usd is None
    assert new.per_request_risk_usd==old.per_request_risk_usd==Decimal('.05')
    with pytest.raises(ValueError,match='UNKNOWN_ONLINE_MODEL_AUTHORIZATION'):
        OnlineDeepSeekProvider(settings(),tmp_path/'unknown',authorization_id='unapproved')


def test_daily_provider_exceeds_former_limit_and_still_rejects_duplicate_send(tmp_path):
    from tests.unit.models.test_evaluation_provider import OfflineConnection,direct_request
    from tests.unit.models.test_natural_explanation import context
    from commerce_hub.scenarios.s01.natural_explanation import NaturalExplanationBundle
    provider=OnlineDeepSeekProvider(settings(),tmp_path,authorization_id=DAILY_USE_AUTHORIZATION_ID)
    connection=OfflineConnection()
    provider.delegate.connection_factory=lambda *args,**kwargs:connection
    bundle=NaturalExplanationBundle(context())
    for i in range(6):
        request=direct_request(bundle,f'call-{i}',f'attempt-{i}')
        assert provider.invoke(request).status=='COMPLETED'
    assert len(connection.requests)==6
    with pytest.raises(ValueError,match='USAGE_MUST_BE_RECONCILED'):
        provider.delegate.invoke(request)
    assert len(connection.requests)==6


def test_local_default_assembles_uncapped_shared_policy_without_relaxing_single_task(monkeypatch,tmp_path):
    from types import SimpleNamespace
    import os
    from commerce_hub.bootstrap import local_platform,s01_v2
    monkeypatch.setattr(os,'environ',os.environ.copy())
    monkeypatch.setattr('commerce_hub.bootstrap.settings.load_settings',lambda:None)
    local_platform.configure(dict(modelEnabled=True,requisitionEnabled=False,sessionSeconds=28800,
        installationId='test',signingKey='test',webPort=5173,apiPort=8765))
    assert os.environ['COMMERCE_S01_V2_MODEL_AUTHORIZATION']==DAILY_USE_AUTHORIZATION_ID
    monkeypatch.setattr(s01_v2,'ROOT',tmp_path)
    monkeypatch.setattr(s01_v2,'assert_migration_target',lambda s:None)
    monkeypatch.setattr(s01_v2,'Database',lambda s:SimpleNamespace(engine=None))
    monkeypatch.setattr(s01_v2,'MonitorRegistry',lambda *a:SimpleNamespace(mappings=lambda:[]))
    monkeypatch.setattr(s01_v2,'V2Handler',lambda *a,**kw:SimpleNamespace())
    spec=s01_v2.registry(settings(environment='test'))['S01_V2_SINGLE']
    shared=spec.shared_model_authorization
    assert shared.authorization_id==DAILY_USE_AUTHORIZATION_ID
    assert (shared.max_calls,shared.max_tokens,shared.max_cost)==(None,None,None)
    assert shared.max_inflight==1
    assert (spec.max_calls,spec.max_tokens,spec.max_cost)==(1,24000,Decimal('.05'))
