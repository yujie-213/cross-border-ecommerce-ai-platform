"""Actual API/Worker/MySQL fault tests using an explicitly simulated test assembly."""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
from uuid import uuid4

import httpx
import jwt
import pytest
from sqlalchemy import func, select

from commerce_hub.governance.access.service import AccessControl, ALLOWED_ACTIONS
from commerce_hub.governance.observability.tables import audit_events
from commerce_hub.infrastructure.work_tables import work_items
from commerce_hub.orchestration.tables import budgets, tasks

pytestmark = pytest.mark.mysql
ROOT = Path(__file__).resolve().parents[3]


class OwnedProcess:
    """Only retains child output in memory; never renders it in assertions or errors."""
    def __init__(self, args, environment):
        self.lines = []
        self.process = subprocess.Popen(
            args, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.readers = []
        for pipe in [self.process.stdout, self.process.stderr]:
            reader = threading.Thread(target=self._read, args=(pipe,), daemon=True)
            reader.start()
            self.readers.append(reader)

    def _read(self, pipe):
        for line in iter(pipe.readline, b""):
            self.lines.append(line)

    def stop(self, crash=False):
        if self.process.poll() is None:
            if crash:
                self.process.kill()
            else:
                self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for reader in self.readers:
            reader.join(timeout=2)


class ProcessHarness:
    def __init__(self, database, mysql_settings):
        self.database = database
        self.processes = []
        self.client = None
        self.tenant = "process-" + uuid4().hex
        self.principal_id = "principal-fixture"
        self.token_id = uuid4().hex
        self.key = secrets.token_urlsafe(48)
        self.issuer = "https://fixture.invalid/" + uuid4().hex
        self.audience = "foundation-process-fixture"
        self.environment = dict(os.environ)
        self.environment.update({
            "COMMERCE_ENVIRONMENT": "test", "COMMERCE_FIXTURE_KIND": "o01.fixture." + uuid4().hex,
            "COMMERCE_AUTH_ISSUER": self.issuer, "COMMERCE_AUTH_AUDIENCE": self.audience,
            "COMMERCE_AUTH_SIGNING_KEY": self.key, "COMMERCE_LEASE_SECONDS": "1",
            "COMMERCE_HEARTBEAT_SECONDS": "0.15", "COMMERCE_POLL_SECONDS": "0.05",
            "COMMERCE_TASK_DEADLINE_SECONDS": "30", "COMMERCE_MAX_DELIVERY_ATTEMPTS": "3",
            "PYTHONUNBUFFERED": "1",
        })
        self.scope = {"tenantId": self.tenant, "storeIds": ["store-fixture"],
                      "warehouseIds": ["warehouse-fixture"], "canonicalSkuIds": ["sku-fixture"],
                      "fields": ["quantity"]}
        control = AccessControl(database.engine, self.issuer, self.audience, self.key)
        with database.engine.begin() as connection:
            control.provision_fixture(connection, tenant_id=self.tenant, principal_id=self.principal_id,
                                      token_id=self.token_id, expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
                                      grants_by_action={action: self.scope for action in ALLOWED_ACTIONS})
        now = int(datetime.now(timezone.utc).timestamp())
        self.token = jwt.encode({"iss": self.issuer, "aud": self.audience, "exp": now + 900,
                                 "iat": now, "nbf": now - 1, "sub": self.principal_id,
                                 "tid": self.tenant, "jti": self.token_id, "rev": 1}, self.key, algorithm="HS256")
        self.secrets = [self.key, self.token, mysql_settings.db_password.get_secret_value()]

    def start_api(self):
        if self.client is not None:
            self.client.close()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.api = OwnedProcess([sys.executable, "-m", "uvicorn", "tests.support.foundation:create_app", "--factory",
                                 "--host", "127.0.0.1", "--port", str(port), "--no-access-log", "--no-server-header"],
                                self.environment)
        self.processes.append(self.api)
        self.client = httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"Authorization": "Bearer " + self.token},
                                   timeout=3, trust_env=False)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.api.process.poll() is not None:
                pytest.fail("Owned API subprocess stopped before readiness; output withheld for credential safety", pytrace=False)
            try:
                ready = self.client.get("/health/ready")
                if ready.status_code == 200:
                    assert ready.json()["scope"] == "ENGINEERING_FOUNDATION_ONLY"
                    return
            except httpx.TransportError:
                pass
            time.sleep(0.1)
        pytest.fail("Owned API subprocess did not become ready; output withheld for credential safety", pytrace=False)

    def start_worker(self, *, empty_registry=False):
        arguments = [sys.executable, "-m", "commerce_hub.entrypoints.worker"] if empty_registry else [sys.executable, "-m", "tests.support.foundation", "worker"]
        worker = OwnedProcess(arguments, self.environment)
        self.processes.append(worker)
        return worker

    def submit(self, *, delay=0, fail_until=0, key=None):
        key = key or uuid4().hex
        payload = {"analysisMode": "SINGLE", "scenarioId": "ENGINEERING_FIXTURE",
                   "scope": {key: value for key, value in self.scope.items() if key != "tenantId"},
                   "parameters": {"delaySeconds": delay, "failUntilAttempt": fail_until}}
        response = self.client.post("/api/v1/analysis-tasks", json=payload, headers={"Idempotency-Key": key})
        assert response.status_code == 202
        value = response.json()
        assert value["sourceNature"] == "SIMULATED_ENGINEERING"
        assert value["reportRef"] is None
        return value, payload, key

    def row(self, task_id):
        with self.database.engine.connect() as connection:
            return dict(connection.execute(select(tasks).where(tasks.c.tenant_id == self.tenant,
                                                               tasks.c.task_id == task_id)).mappings().one())

    def budget(self, task_id):
        with self.database.engine.connect() as connection:
            return dict(connection.execute(select(budgets).where(budgets.c.tenant_id == self.tenant,
                                                                 budgets.c.task_id == task_id)).mappings().one())

    def work(self, task_id):
        task = self.row(task_id)
        with self.database.engine.connect() as connection:
            return dict(connection.execute(select(work_items).where(work_items.c.tenant_id == self.tenant,
                                                                    work_items.c.work_id == task["work_id"])).mappings().one())

    def audit_count(self, task_id, action):
        with self.database.engine.connect() as connection:
            return connection.scalar(select(func.count()).select_from(audit_events).where(
                audit_events.c.tenant_id == self.tenant, audit_events.c.task_id == task_id, audit_events.c.action == action))

    def wait_state(self, task_id, wanted, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = self.row(task_id)
            if value["state"] == wanted:
                return value
            if value["state"] in {"SUCCEEDED", "FAILED", "CANCELLED"} and value["state"] != wanted:
                pytest.fail("Engineering task reached an unexpected terminal state: " + value["state"], pytrace=False)
            time.sleep(0.05)
        pytest.fail("Timed out waiting for engineering task state: " + wanted, pytrace=False)

    def close(self):
        if self.client is not None:
            self.client.close()
        for process in self.processes:
            process.stop()
        for process in self.processes:
            output = b"".join(process.lines).decode("utf-8", errors="replace")
            leaked = any(secret and secret in output for secret in self.secrets)
            if leaked:
                pytest.fail("Credential appeared in child process output; output was not saved or displayed", pytrace=False)


@pytest.fixture
def harness(database, mysql_settings):
    instance = ProcessHarness(database, mysql_settings)
    try:
        instance.start_api()
        yield instance
    finally:
        instance.close()


def test_api_restart_preserves_queued_task_and_idempotency(harness):
    task, payload, key = harness.submit()
    task_id = task["taskRef"]["taskId"]
    deadline = harness.row(task_id)["deadline"]
    harness.api.stop()
    harness.start_api()
    existing = harness.client.get("/api/v1/analysis-tasks/" + task_id)
    assert existing.status_code == 200
    assert existing.json()["state"] == "QUEUED"
    replay = harness.client.post("/api/v1/analysis-tasks", json=payload, headers={"Idempotency-Key": key})
    assert replay.status_code == 202 and replay.json()["taskRef"] == task["taskRef"]
    harness.start_worker()
    harness.wait_state(task_id, "SUCCEEDED")
    assert harness.row(task_id)["deadline"] == deadline
    assert harness.audit_count(task_id, "TASK_CREATED") == 1
    assert harness.audit_count(task_id, "TASK_COMPLETED") == 1


def test_killed_worker_recovers_same_task_deadline_and_budget(harness):
    task, _, _ = harness.submit(delay=1.8)
    task_id = task["taskRef"]["taskId"]
    original_budget = harness.budget(task_id)
    original_deadline = harness.row(task_id)["deadline"]
    first = harness.start_worker()
    harness.wait_state(task_id, "RUNNING")
    first.stop(crash=True)
    harness.start_worker()
    harness.wait_state(task_id, "SUCCEEDED")
    assert harness.row(task_id)["deadline"] == original_deadline
    assert harness.budget(task_id) == original_budget
    assert harness.work(task_id)["attempt"] == 2
    assert harness.audit_count(task_id, "TASK_COMPLETED") == 1


def test_production_empty_registry_cannot_recover_fixture_delivery(harness):
    task, _, _ = harness.submit(delay=1.5)
    task_id = task["taskRef"]["taskId"]
    fixture_worker = harness.start_worker()
    harness.wait_state(task_id, "RUNNING")
    fixture_worker.stop(crash=True)
    empty_worker = harness.start_worker(empty_registry=True)
    time.sleep(1.4)
    assert empty_worker.process.poll() is None
    work = harness.work(task_id)
    assert work["state"] == "LEASED" and work["attempt"] == 1
    assert harness.row(task_id)["state"] == "RUNNING"
    empty_worker.stop()
    harness.start_worker()
    harness.wait_state(task_id, "SUCCEEDED")
    assert harness.work(task_id)["attempt"] == 2


def test_two_actual_workers_do_not_complete_a_task_twice(harness):
    task, _, _ = harness.submit(delay=0.6)
    task_id = task["taskRef"]["taskId"]
    harness.start_worker()
    harness.start_worker()
    harness.wait_state(task_id, "SUCCEEDED")
    time.sleep(0.25)
    assert harness.work(task_id)["attempt"] == 1
    assert harness.audit_count(task_id, "TASK_COMPLETED") == 1


def test_running_cancel_blocks_late_completion(harness):
    task, _, _ = harness.submit(delay=1.5)
    task_id = task["taskRef"]["taskId"]
    harness.start_worker()
    running = harness.wait_state(task_id, "RUNNING")
    cancelled = harness.client.post("/api/v1/analysis-tasks/" + task_id + "/cancel",
                                    json={"expectedRevision": running["revision"]},
                                    headers={"Idempotency-Key": uuid4().hex})
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "CANCELLED"
    time.sleep(1.8)
    assert harness.row(task_id)["state"] == "CANCELLED"
    assert harness.work(task_id)["state"] == "CANCELLED"
    assert harness.audit_count(task_id, "TASK_COMPLETED") == 0


def test_revoked_identity_is_rechecked_by_actual_worker(harness):
    task, _, _ = harness.submit()
    task_id = task["taskRef"]["taskId"]
    revoked = harness.client.delete("/api/v1/session")
    assert revoked.status_code == 200
    harness.start_worker()
    failed = harness.wait_state(task_id, "FAILED")
    assert failed["error_code"] == "POLICY_DENIED"
    assert harness.audit_count(task_id, "TASK_COMPLETED") == 0


def test_actual_worker_retry_exhaustion_is_bounded(harness):
    task, _, _ = harness.submit(fail_until=3)
    task_id = task["taskRef"]["taskId"]
    deadline = harness.row(task_id)["deadline"]
    harness.start_worker()
    harness.wait_state(task_id, "FAILED")
    work = harness.work(task_id)
    assert work["state"] == "DEAD" and work["attempt"] == 3
    assert harness.audit_count(task_id, "TASK_RETRY") == 2
    time.sleep(0.3)
    assert harness.work(task_id)["attempt"] == 3
    assert harness.row(task_id)["deadline"] == deadline
    assert harness.audit_count(task_id, "TASK_COMPLETED") == 0
