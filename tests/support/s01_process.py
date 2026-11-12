"""Owned local processes, generated test identity and guarded synthetic S01 demo."""
import socket
import sys
import time
from uuid import uuid4

import httpx

from tests.integration.processes.test_foundation_processes import OwnedProcess, ProcessHarness
from tests.support.s01 import example


class S01ProcessHarness(ProcessHarness):
    def __init__(self, database, settings, *, recovery_fixture=False):
        super().__init__(database, settings)
        self.module = "tests.support.s01_worker" if recovery_fixture else "commerce_hub.bootstrap.engineering"

    def start_api(self):
        if self.client is not None:
            self.client.close()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.api = OwnedProcess([sys.executable, "-m", "uvicorn", self.module + ":create_app", "--factory",
            "--host", "127.0.0.1", "--port", str(port), "--no-access-log", "--no-server-header"], self.environment)
        self.processes.append(self.api)
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": "Bearer " + self.token}, timeout=3, trust_env=False)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if self.api.process.poll() is not None:
                raise RuntimeError("Owned engineering API stopped; raw output withheld")
            try:
                if self.client.get("/health/ready").status_code == 200:
                    return
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        raise RuntimeError("Owned engineering API did not become ready; raw output withheld")

    def start_worker(self):
        worker = OwnedProcess([sys.executable, "-m", self.module, "worker"], self.environment)
        self.processes.append(worker)
        return worker

    def submit(self, *, parameters=None, key=None):
        payload = {"analysisMode": "SINGLE", "scenarioId": "ENGINEERING_S01",
            "scope": {k: v for k, v in self.scope.items() if k != "tenantId"},
            "parameters": parameters or example()}
        key = key or uuid4().hex
        response = self.client.post("/api/v1/analysis-tasks", json=payload, headers={"Idempotency-Key": key})
        assert response.status_code == 202
        return response.json(), payload, key

    def report(self, task_id):
        response = self.client.get("/api/v1/analysis-tasks/" + task_id + "/report")
        assert response.status_code == 200
        return response.json()
