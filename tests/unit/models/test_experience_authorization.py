"""No network: explicit new authorization preserves the old bounded policy."""
from decimal import Decimal
import pytest
from commerce_hub.adapters.models.online import OnlineDeepSeekProvider,V2_AUTHORIZATION_ID,EXPERIENCE_AUTHORIZATION_ID
from tests.unit.models.test_evaluation_provider import settings


def test_new_owner_authorization_is_separate_and_keeps_per_call_reservation(tmp_path):
    old=OnlineDeepSeekProvider(settings(),tmp_path/'old',authorization_id=V2_AUTHORIZATION_ID).delegate.authorization
    new=OnlineDeepSeekProvider(settings(),tmp_path/'new',authorization_id=EXPERIENCE_AUTHORIZATION_ID).delegate.authorization
    assert old.max_requests==4 and old.max_total_cost_usd==Decimal('.20')
    assert new.authorization_id!=old.authorization_id and new.max_requests is None and new.max_total_cost_usd is None
    assert new.per_request_risk_usd==old.per_request_risk_usd==Decimal('.05')
    with pytest.raises(ValueError,match='UNKNOWN_ONLINE_MODEL_AUTHORIZATION'):
        OnlineDeepSeekProvider(settings(),tmp_path/'unknown',authorization_id='unapproved')
