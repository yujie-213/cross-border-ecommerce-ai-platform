"""Plan evaluation is the existing B01, isolated from ERP/model/submission."""
from copy import deepcopy
from datetime import date, timedelta
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from commerce_hub.entrypoints.http.s01_v2 import register_v2_routes
from commerce_hub.entrypoints.http.errors import install_error_handlers
from commerce_hub.scenarios.s01_v2.analysis import analyze
from commerce_hub.scenarios.s01_v2.plan_preview import preview_plan
from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.orchestration.service import TaskError
from tests.unit.data.test_product_demand import fixture


def item_for(tmp_path, **kwargs):
    source, reader, catalog, entity = fixture(tmp_path, **kwargs)
    return source, analyze(catalog, entity, reader)


def test_original_candidate_matches_existing_b01_exactly_and_plan_is_not_saved(tmp_path):
    source, item = item_for(tmp_path)
    original = deepcopy(item); calls = len(source.calls)
    candidate = item['ruleResult']['supplyDemand']['candidates'][0]
    result = preview_plan(item, int(candidate['quantity']), date.fromisoformat(candidate['availableDate']))
    assert result['evaluation']['series'] == candidate['evaluation']['series']
    assert item == original and len(source.calls) == calls and source.mutations == 0


def test_missing_quote_allows_hypothetical_supply_but_never_enables_submit(tmp_path):
    _, item = item_for(tmp_path, quotes=False)
    original = deepcopy(item)
    rows = item['decision']['baseline']['series']
    arrival = date.fromisoformat(rows[2]['day'])
    plan = preview_plan(item, 53, arrival)
    larger = preview_plan(item, 61, arrival)
    assert plan['evaluation']['series'][1] == rows[1]
    assert plan['evaluation']['series'][2]['arrivals'] == '53'
    assert float(larger['evaluation']['closingBalance']) - float(plan['evaluation']['closingBalance']) == 8
    assert plan['evaluation']['stockoutRisk']
    assert item == original and not item['procurementEligibility']['eligible']
    with pytest.raises(TaskError):
        V2RequisitionService.validate_quantity({'dataReport':{'item':item}},53,'')


def test_arrival_change_preserves_prearrival_shortages(tmp_path):
    _, item = item_for(tmp_path, stock=1)
    rows = item['decision']['baseline']['series']
    early = preview_plan(item,60,date.fromisoformat(rows[0]['day']))
    late = preview_plan(item,60,date.fromisoformat(rows[3]['day']))
    assert not early['evaluation']['stockoutRisk']
    assert late['evaluation']['firstShortageDate'] == rows[0]['day']
    assert early['evaluation']['closingBalance'] == late['evaluation']['closingBalance']


@pytest.mark.parametrize('quantity',[0,-1,100001,1.5,True])
def test_invalid_quantity_rejected(tmp_path,quantity):
    _, item=item_for(tmp_path)
    with pytest.raises(ValueError,match='PLAN_QUANTITY_INVALID'):
        preview_plan(item,quantity,date.fromisoformat(item['decision']['baseline']['series'][0]['day']))


def test_outside_window_or_incompatible_historical_curve_not_silently_reused(tmp_path):
    _, item=item_for(tmp_path)
    day=date.fromisoformat(item['decision']['baseline']['series'][0]['day'])
    for arrival in [day-timedelta(days=1), day+timedelta(days=90)]:
        with pytest.raises(ValueError,match='PLAN_DATE_OUTSIDE_WINDOW'):preview_plan(item,32,arrival)
    item['decision']['baseline']['series'][0]['closingBalance']='999'
    with pytest.raises(ValueError,match='PLAN_BASELINE_VERSION_MISMATCH'):preview_plan(item,32,day)
    item['decision']['baseline']=None
    with pytest.raises(ValueError,match='PLAN_BASELINE_UNAVAILABLE'):preview_plan(item,32,day)


def test_preview_endpoint_reads_scoped_item_and_checks_payload_without_write_authorization(tmp_path,monkeypatch):
    _, item=item_for(tmp_path,quotes=False)
    connection=MagicMock();engine=MagicMock();engine.begin.return_value=nullcontext(connection);engine.connect.return_value=nullcontext(connection)
    access=MagicMock();policy=SimpleNamespace(owned_only=True,opening_binding=lambda row:object(),can_write=lambda row:False)
    handler=SimpleNamespace(policy=policy,validate_scope=MagicMock())
    service=SimpleNamespace(engine=engine,access=access,registry={'S01_V2_BATCH':SimpleNamespace(handler=handler)},read=MagicMock(return_value={'scenarioId':'S01_V2_BATCH'}))
    monkeypatch.setattr(ItemStore,'read',lambda *args:{item['entityKey']:deepcopy(item)})
    app=FastAPI();install_error_handlers(app);app.state.tasks=service
    register_v2_routes(app,lambda:SimpleNamespace(tenant_id='test'))
    day=item['decision']['baseline']['series'][0]['day']
    with TestClient(app) as client:
        path='/api/v1/s01/v2/batches/batch/items/'+item['entityKey']+'/plan-preview'
        response=client.post(path,json={'quantity':53,'availableDate':day})
        assert response.status_code==200 and response.json()['sourceTaskId']=='batch'
        assert response.json()['semantics']=='HYPOTHETICAL_PLAN_NOT_CONFIRMED_SUPPLY'
        assert client.post(path,json={'quantity':1.5,'availableDate':day}).status_code==422
        assert client.post(path,json={'quantity':53,'availableDate':'invalid'}).status_code==422
        assert client.post(path,json={'quantity':53,'availableDate':day,'approved':True}).status_code==422
        with pytest.raises(TaskError,match='NOT_FOUND'):
            client.post(path.replace(item['entityKey'],'unknown'),json={'quantity':53,'availableDate':day})
        policy.opening_binding=lambda row:None
        with pytest.raises(TaskError,match='V2_BUSINESS_SCOPE_NOT_REGISTERED'):
            client.post(path,json={'quantity':53,'availableDate':day})
    assert all(call.args[2]=='tasks:read' for call in access.authorize.call_args_list)
