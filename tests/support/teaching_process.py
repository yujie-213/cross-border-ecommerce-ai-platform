"""Owned isolated API/Worker harness. Input provenance is supplied explicitly by the caller."""
from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import update
from commerce_hub.governance.access.tables import grants
from commerce_hub.data.projection.observed import project_observations
from tests.support.teaching import observed_fixture
from tests.support.s01_process import S01ProcessHarness

ROOT=Path(__file__).resolve().parents[2]

class TeachingProcessHarness(S01ProcessHarness):
    def __init__(self,database,settings,projection=None):
        super().__init__(database,settings)
        value=deepcopy(projection) if projection is not None else observed_fixture()
        value["scope"]["tenantId"]=self.tenant
        value.pop("revision",None)
        self.projection=project_observations(value).model_dump(mode="json")
        self.scope=self.projection["scope"]
        with database.engine.begin() as conn:
            conn.execute(update(grants).filter_by(tenant_id=self.tenant,principal_id=self.principal_id).values(scope=self.scope))
        path=ROOT/".tmp"/("teaching-package-"+uuid4().hex+".json")
        path.parent.mkdir(exist_ok=True);path.write_bytes((json.dumps(self.projection,ensure_ascii=False)+"\n").encode())
        self.module="commerce_hub.bootstrap.teaching_erp"
        self.environment.update(COMMERCE_MODEL_PROVIDER="mock",COMMERCE_MODEL_NETWORK_ENABLED="false",COMMERCE_TEACHING_PACKAGE_PATH=str(path))

    def submit(self,*,key=None,package_ref=None):
        body=dict(analysisMode="SINGLE",scenarioId="TEACHING_S01_ADMISSION",
            scope={k:v for k,v in self.scope.items() if k!="tenantId"},parameters=dict(packageRef=package_ref or self.projection["revision"]))
        key=key or uuid4().hex
        response=self.client.post("/api/v1/analysis-tasks",json=body,headers={"Idempotency-Key":key})
        assert response.status_code==202,response.json().get("code")
        return response.json(),body,key
