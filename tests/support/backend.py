"""Explicitly simulated five-case gold set, never ERP returned values."""
from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

from tests.support.s01 import example
from tests.support.s01_process import S01ProcessHarness
from commerce_hub.scenarios.s01_backend import package_ref


def cases():
    values = {key: example() for key in "ABCDE"}
    values["B"]["inventory"][0]["availableQty"] = "100"
    values["C"]["inventory"][0]["availableQty"] = "5"
    values["C"]["supply"][0].update(remainingQty="100", availableDate="2026-11-21")
    values["D"]["demand"].pop()
    values["E"]["policy"]["qualityDisposition"] = "INVESTIGATE"
    for key, value in values.items():
        value["fixtureId"] = "backend-simulated-" + key
    return {key: dict(kind="SIMULATED", payload=value) for key, value in values.items()}


class BackendHarness(S01ProcessHarness):
    def __init__(self, database, settings, entries=None, *, mock=True):
        super().__init__(database, settings)
        self.entries = deepcopy(entries if entries is not None else list(cases().values()))
        self.module = "commerce_hub.bootstrap.s01_backend"
        path = Path(__file__).resolve().parents[2] / ".tmp" / ("backend-catalog-" + uuid4().hex + ".json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(self.entries, ensure_ascii=False), encoding="utf-8")
        self.environment.update(COMMERCE_MODEL_PROVIDER="mock", COMMERCE_MODEL_NETWORK_ENABLED="false",
            COMMERCE_S01_CATALOG_PATH=str(path), COMMERCE_S01_EXPLANATION_MODE="mock" if mock else "off")

    def submit(self, *, entry=None, key=None, previous=None):
        entry = entry or self.entries[0]
        body = dict(analysisMode="SINGLE", scenarioId="S01_BACKEND",
            scope={key:value for key,value in self.scope.items() if key != "tenantId"},
            parameters=dict(packageRef=package_ref(entry["kind"], entry["payload"])))
        if previous:
            body["previousReportRef"] = previous
        key = key or uuid4().hex
        response = self.client.post("/api/v1/analysis-tasks", json=body, headers={"Idempotency-Key":key})
        assert response.status_code == 202, response.json().get("code")
        return response.json(), body, key
