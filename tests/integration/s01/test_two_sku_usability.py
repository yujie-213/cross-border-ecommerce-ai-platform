from datetime import datetime,timezone
import pytest
from sqlalchemy import select
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService
from commerce_hub.orchestration.worker import Worker
from tests.integration.orchestration.test_s01_reports import make_s01
from tests.integration.s01.test_v2_workflow import environment,run
from tests.support.admission_runtime import AdmissionERP

pytestmark=pytest.mark.mysql


def test_reference_survives_worker_api_history_and_cannot_purchase(make_s01,tmp_path,monkeypatch,mysql_settings):
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    import jwt
    import commerce_hub.data.sync.v2 as v2
    from commerce_hub.entrypoints.http.app import create_app
    monkeypatch.setattr(v2,'now',lambda:'2026-11-14T06:00:05+00:00')
    e=environment(make_s01,tmp_path,1);e.erp=AdmissionERP();e.policy.owned_mappings=[e.erp.mapping]
    tid,report=run(e)
    assert report['dataReport']['summary']['historicalReference']==1
    with e.database.engine.connect() as c:item=next(iter(ItemStore.read(c,e.tenant,tid).values()))
    assert item['analysisState']=='HISTORICAL_REFERENCE' and item['quantity'] is None
    with pytest.raises(Exception,match='REQUISITION_SOURCE_NOT_ELIGIBLE'):
        V2RequisitionService.validate_quantity(dict(dataReport=dict(item=item)),48,'manual')
    settings=mysql_settings.model_copy(update=dict(environment='test',auth_issuer='fixture-issuer',auth_audience='fixture-audience',auth_signing_key=SecretStr('fixture-key-'+'x'*64),browser_origin='https://testserver'))
    stamp=int(datetime.now(timezone.utc).timestamp())
    token=jwt.encode(dict(iss='fixture-issuer',aud='fixture-audience',sub=e.principal.principal_id,tid=e.tenant,jti=e.principal.token_id,rev=1,exp=stamp+600,iat=stamp,nbf=stamp-1),'fixture-key-'+'x'*64,algorithm='HS256')
    with TestClient(create_app(settings,e.service.registry),base_url='https://testserver') as client:
        client.app.state.tasks=e.service
        assert client.post('/api/v1/session',headers={'Authorization':'Bearer '+token}).status_code==200
        data=client.get(f'/api/v1/s01/v2/batches/{tid}/items/{item["entityKey"]}').json()
        assert data['sourceGrade']=='HISTORICAL_REFERENCE' and data['demandWindow']['referenceDays']==7
    monkeypatch.setattr(v2,'now',lambda:'2026-11-15T06:00:05+00:00')
    e.service.create(e.principal,'next','S01_V2_BATCH',e.scope,{},'synthetic');assert Worker(e.service).once()
    assert e.service.read_report(e.principal,tid)==report and e.erp.mutations==0
