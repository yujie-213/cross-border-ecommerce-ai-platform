"""Default-off S01 DeepSeek evaluation with one persistent O01 task budget.

Token usage and cost are independent accounting dimensions. Official token counts
may be recorded while the explicit USD risk reservation remains occupied. This tool
can send up to five distinct A-E cases inside one persistent O01 task budget; it
never retries the same logical call. Offline validation remains available without
reading settings, credentials, the database, or the network.
"""
import argparse
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit


FIXED_AUTHORIZATION_ID = "s01-backend-20261112-v1"
STRUCTURED_AUTHORIZATION_ID = "s01-c04-structured-20261112-r1"


def evaluation_policy(authorization_id):
    """Explicit reviewed execution records; source catalog authorization is independent."""
    if authorization_id not in {FIXED_AUTHORIZATION_ID, STRUCTURED_AUTHORIZATION_ID}:
        raise ValueError("FIXED_MODEL_AUTHORIZATION_REQUIRED")
    successor = authorization_id == STRUCTURED_AUTHORIZATION_ID
    identity = _authorization_identity(authorization_id)
    return dict(authorization_id=authorization_id,
        tenant="s01-eval-" + _authorization_identity(FIXED_AUTHORIZATION_ID),
        principal_id="s01-model-evaluator-" + identity[:16] if successor else "s01-model-evaluator",
        catalog_authorization_id=FIXED_AUTHORIZATION_ID,
        max_requests=10 if successor else 5, max_cost=Decimal("1"), request_risk=Decimal(".05"),
        case_order=tuple("CDEAB") if successor else None,
        logical_namespace=identity[:12] if successor else None)


def evaluation_catalog(path, *, private_root, policy):
    ids, entries, scope = _load_private_catalog(path, private_root=private_root,
        authorization_id=policy["catalog_authorization_id"], tenant=policy["tenant"])
    if policy["case_order"] is not None:
        if set(ids) != set(policy["case_order"]):
            raise ValueError("AUTHORIZED_CASE_SET_REQUIRED")
        by_id = dict(zip(ids, entries))
        ids = list(policy["case_order"]); entries = [by_id[key] for key in ids]
    return ids, entries, scope


CATALOG_SCHEMA_VERSION = "s01-model-evaluation-catalog-v1"
IDENTITY_TTL_MINUTES = 16


def _authorization_identity(authorization_id):
    return hashlib.sha256(authorization_id.encode()).hexdigest()[:32]


def _identity_expiration(now):
    return now + timedelta(minutes=IDENTITY_TTL_MINUTES)


def _load_private_catalog(path, *, private_root, authorization_id, tenant):
    """Load fixed teaching-simulation cases without exposing their payloads.

    The catalog is private input, not an authority source.  Its authorization,
    tenant and every normalized execution scope must agree with the one fixed
    evaluation task before settings, credentials, database or network are used.
    """
    from commerce_hub.scenarios.s01_backend import S01BackendHandler

    catalog_path = Path(path).resolve()
    root = Path(private_root).resolve()
    if (not catalog_path.is_relative_to(root) or catalog_path.suffix.lower() != ".json"
            or not catalog_path.is_file()):
        raise ValueError("CONTROLLED_PRIVATE_CATALOG_REQUIRED")
    try:
        value = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("INVALID_PRIVATE_CATALOG") from None
    if (not isinstance(value, dict) or set(value) != {
            "schemaVersion", "authorizationId", "tenantId", "entries"} or
            value["schemaVersion"] != CATALOG_SCHEMA_VERSION or
            value["authorizationId"] != authorization_id or value["tenantId"] != tenant or
            not isinstance(value["entries"], list) or not 1 <= len(value["entries"]) <= 5):
        raise ValueError("PRIVATE_CATALOG_BINDING_REJECTED")
    selected = []
    case_ids = []
    expected_scope = None
    for row in value["entries"]:
        if (not isinstance(row, dict) or set(row) != {"caseId", "kind", "payload"} or
                row["caseId"] not in "ABCDE" or len(row["caseId"]) != 1 or
                row["kind"] != "TEACHING_SIMULATION" or not isinstance(row["payload"], dict)):
            raise ValueError("INVALID_PRIVATE_CATALOG_ENTRY")
        entry = {"kind": row["kind"], "payload": row["payload"]}
        _, scope = S01BackendHandler._prepare(entry)
        if scope.get("tenantId") != tenant:
            raise ValueError("PRIVATE_CATALOG_TENANT_MISMATCH")
        if expected_scope is None:
            expected_scope = scope
        elif scope != expected_scope:
            raise ValueError("PRIVATE_CATALOG_SCOPE_MISMATCH")
        case_ids.append(row["caseId"])
        selected.append(entry)
    if len(set(case_ids)) != len(case_ids) or case_ids != list("ABCDE")[:len(case_ids)]:
        raise ValueError("PRIVATE_CATALOG_CASE_SEQUENCE_REJECTED")
    return case_ids, selected, expected_scope


def _sample_case():
    # Build the gold facts through the accepted production D01/D02/D03/B01/B02
    # functions. Values below are never copied into this tool as hand-authored facts.
    from commerce_hub.capabilities.forecasting import propose
    from commerce_hub.capabilities.metrics import evaluate
    from commerce_hub.data.projection import project
    from commerce_hub.data.quality import capture
    from commerce_hub.data.sync import FixtureConnector
    example = json.loads((Path(__file__).resolve().parents[1] / "examples" / "s01_single_sku.json").read_text(encoding="utf-8"))
    value, batch = FixtureConnector().read(example)
    snapshot = capture(project(value, batch))
    baseline = evaluate(snapshot)
    proposal = propose(snapshot)
    if (proposal.get("baseline") != baseline or len(proposal.get("candidates", [])) != 1 or
            proposal["candidates"][0].get("procurementEligible") is not False):
        raise ValueError("OFFLINE_GOLD_CONTRACT_CHANGED")
    candidate = proposal["candidates"][0]
    quantity = candidate["quantity"]
    gap = baseline["gapQuantity"]
    shortage_date = baseline["firstShortageDate"]
    if not shortage_date or not baseline["stockoutRisk"]:
        raise ValueError("OFFLINE_GOLD_CONTRACT_CHANGED")
    return dict(
        caseId="A",
        facts=[
            dict(ref="reason", kind="candidate",
                 text=f"{candidate['candidateId']} quantity={quantity}; procurementEligible=false.",
                 allowedPhrases=[f"工程样例生成了 {quantity} 件补货候选"], sections=["recommendationReasons"],
                 requiredSections=["recommendationReasons"], allowedNumbers=[quantity]),
            dict(ref="evidence", kind="metric", text=baseline["metricResultRef"],
                 allowedPhrases=[f"基线补货缺口为 {gap} 件，并在 {shortage_date} 首次缺货"], sections=["keyEvidence"],
                 requiredSections=["keyEvidence"], allowedNumbers=[gap], allowedDates=[shortage_date]),
            dict(ref="risk", kind="gap", text=f"{baseline['metricResultRef']} stockoutRisk=true.",
                 allowedPhrases=["到货前仍存在缺货风险"], sections=["majorRisks"],
                 requiredSections=["majorRisks"]),
            dict(ref="confirm", kind="limitation", text=";".join(proposal["limitations"]),
                 allowedPhrases=["工程规则未验证，需要人工确认"], sections=["humanConfirmations"]),
        ],
        sourceNature="SIMULATED_ENGINEERING",
        trust="AUTHORIZED_FACTS_ONLY",
        sensitivity="SYNTHETIC_ONLY",
        omissions=["real-purchase-approval"],
        scope=dict(storeIds=["evaluation-store"], warehouseIds=["evaluation-warehouse"],
                   canonicalSkuIds=["evaluation-sku"], fields=["explanation"]),
    )


def _context(case, *, tenant, task_ref):
    from commerce_hub.scenarios.s01.natural_explanation import NaturalExplanationContext
    case_id = case["caseId"]
    return NaturalExplanationContext(
        ref={"tenantId": tenant, "id": "s01-eval-" + case_id.lower(), "version": "1"},
        taskRef=task_ref,
        planVersion="1",
        participantId="s01-evaluation",
        snapshotId="s01-evaluation-" + case_id.lower(),
        facts=case["facts"],
        sourceNature=case["sourceNature"],
        trust=case["trust"],
        sensitivity=case["sensitivity"],
        omissions=case.get("omissions", []),
    )


def _offline_cases():
    cases = [_sample_case()]
    variants = {
        "B": [
            ("reason", "candidate", "工程样例当前无需补货", "recommendationReasons", "KNOWN", "NOT_APPLICABLE"),
            ("evidence", "metric", "工程样例供需已经满足", "keyEvidence", "KNOWN", "NOT_APPLICABLE"),
            ("risk", "limitation", "仍需监控后续需求变化", "majorRisks", "KNOWN", "NOT_APPLICABLE"),
            ("confirm", "limitation", "需要人工确认工程规则适用性", "humanConfirmations", "KNOWN", "NOT_APPLICABLE"),
        ],
        "C": [
            ("reason", "candidate", "当前候选不能消除中途缺货", "recommendationReasons", "KNOWN", "NOT_APPLICABLE"),
            ("evidence", "metric", "工程样例在 2026-11-20 发生中途缺货", "keyEvidence", "KNOWN", "NOT_APPLICABLE"),
            ("risk", "gap", "总量不能掩盖日期边界风险", "majorRisks", "KNOWN", "NOT_APPLICABLE"),
            ("confirm", "limitation", "需要人工确认到货日期", "humanConfirmations", "KNOWN", "NOT_APPLICABLE"),
        ],
        "D": [
            ("reason", "gap", "需求数据未知，无法形成确定性补货候选", "recommendationReasons", "UNKNOWN", "NOT_APPLICABLE"),
            ("evidence", "gap", "未来需求缺失，需要确认", "keyEvidence", "UNKNOWN", "NOT_APPLICABLE"),
            ("risk", "limitation", "数据不确定，无法确定缺货风险", "majorRisks", "UNKNOWN", "NOT_APPLICABLE"),
            ("confirm", "limitation", "需求来源未确认，需要确认", "humanConfirmations", "UNKNOWN", "NOT_APPLICABLE"),
        ],
        "E": [
            ("reason", "candidate", "质量门仍阻断，不能形成采购适用结论", "recommendationReasons", "KNOWN", "BLOCKED"),
            ("evidence", "evidence", "质量门仍阻断，质量调查未结束", "keyEvidence", "KNOWN", "BLOCKED"),
            ("risk", "limitation", "质量门仍阻断，不能解除", "majorRisks", "KNOWN", "BLOCKED"),
            ("confirm", "limitation", "质量门仍阻断，需要人工复核", "humanConfirmations", "KNOWN", "BLOCKED"),
        ],
    }
    for case_id, rows in variants.items():
        facts = []
        for ref, kind, phrase, section, certainty, quality in rows:
            fact = dict(ref=ref, kind=kind, text=f"SIMULATED_ENGINEERING case {case_id}.",
                        allowedPhrases=[phrase], sections=[section], requiredSections=[section],
                        certainty=certainty, qualityGate=quality)
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", phrase)
            if dates:
                fact["allowedDates"] = dates
            facts.append(fact)
        cases.append(dict(caseId=case_id, facts=facts, sourceNature="SIMULATED",
                          trust="AUTHORIZED_FACTS_ONLY", sensitivity="SYNTHETIC_ONLY",
                          omissions=["real-business-inputs"], scope=_sample_case()["scope"]))
    return cases


def _offline_suite():
    from commerce_hub.scenarios.s01.natural_explanation import NaturalExplanationBundle
    tenant = "s01-eval-offline"
    accepted = 0
    first_bundle = first_valid = None
    for case in _offline_cases():
        bundle = NaturalExplanationBundle(_context(case, tenant=tenant, task_ref={"tenantId": tenant, "taskId": "offline"}))
        valid = {section: [] for section in ["recommendationReasons", "keyEvidence", "majorRisks", "humanConfirmations"]}
        for fact in bundle.context.facts:
            section = fact.sections[0]
            valid[section].append({"text": f"{fact.allowedPhrases[0]} [{fact.ref}]", "supportRefs": [fact.ref]})
        bundle.validate_output(json.dumps(valid, ensure_ascii=False))
        accepted += 1
        if case["caseId"] == "A":
            first_bundle, first_valid = bundle, valid
    rejected = 0
    for text in ["工程样例生成了 21 件补货候选 [reason]", "库存足够 [reason]", "采购已批准 [reason]"]:
        changed = json.loads(json.dumps(first_valid, ensure_ascii=False))
        changed["recommendationReasons"][0]["text"] = text
        try:
            first_bundle.validate_output(json.dumps(changed, ensure_ascii=False))
        except (TypeError, ValueError):
            rejected += 1
    return dict(status="PASS" if accepted == 5 and rejected == 3 else "FAIL", accepted=accepted, rejected=rejected,
                network="NOT_USED", c04="NOT_RUN")


def _catalog_evaluation_ref(authorization_id, case_ids, entries):
    content = json.dumps(
        dict(authorizationId=authorization_id, caseIds=case_ids, entries=entries),
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode()
    return "s01-eval-" + hashlib.sha256(content).hexdigest()


def _validate_api_base_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment or
            parsed.path not in {"", "/"}):
        raise ValueError("LOCAL_API_BASE_URL_REQUIRED")
    return value.rstrip("/")


def _ensure_fixed_identity(database, settings, *, tenant, identity, scope, expires_at, principal_id="s01-model-evaluator"):
    """Provision once or verify the exact existing fixed evaluation identity."""
    from sqlalchemy import select, update
    from commerce_hub.governance.access import AccessControl
    from commerce_hub.governance.access.tables import grants, principals, sessions

    if not settings.auth_configured:
        raise ValueError("TRUSTED_API_IDENTITY_CONFIGURATION_REQUIRED")
    actions = ["tasks:create", "tasks:read", "engineering:execute"]
    access = AccessControl(
        database.engine, settings.auth_issuer, settings.auth_audience,
        settings.auth_signing_key.get_secret_value().encode(),
    )
    with database.engine.begin() as connection:
        principal = connection.execute(select(principals).where(
            principals.c.tenant_id == tenant, principals.c.principal_id == principal_id,
        )).mappings().one_or_none()
        existing_grants = connection.execute(select(grants.c.action, grants.c.scope).where(
            grants.c.tenant_id == tenant, grants.c.principal_id == principal_id,
        )).all()
        session = connection.execute(select(sessions).where(
            sessions.c.tenant_id == tenant, sessions.c.principal_id == principal_id,
            sessions.c.token_id == identity,
        )).mappings().one_or_none()
        if principal is None and not existing_grants and session is None:
            access.provision_fixture(
                connection, tenant_id=tenant, principal_id=principal_id, token_id=identity,
                expires_at=expires_at, grants_by_action={action: scope for action in actions},
            )
            revision = 1
        else:
            grant_map = {row.action: row.scope for row in existing_grants}
            if (principal is None or principal["active"] is not True or principal["revision"] != 1 or
                    set(grant_map) != set(actions) or any(grant_map[action] != scope for action in actions) or
                    session is None or session["active"] is not True):
                raise ValueError("FIXED_EVALUATION_IDENTITY_MISMATCH")
            connection.execute(update(sessions).where(
                sessions.c.tenant_id == tenant, sessions.c.principal_id == principal_id,
                sessions.c.token_id == identity,
            ).values(expires_at=expires_at))
            revision = principal["revision"]
    return principal_id, revision


def _issue_token(settings, *, tenant, principal_id, identity, revision, now, expires_at):
    import jwt
    return jwt.encode(
        dict(iss=settings.auth_issuer, aud=settings.auth_audience,
             exp=int(expires_at.timestamp()), iat=int(now.timestamp()), nbf=int(now.timestamp()) - 1,
             sub=principal_id, tid=tenant, jti=identity, rev=revision),
        settings.auth_signing_key.get_secret_value(), algorithm="HS256",
    )


def _create_and_wait(client, *, body, command_key, wait_seconds, poll_seconds=0.5):
    """Create/replay one task, then read it; never claims work or resends a model call."""
    response = client.post("/api/v1/analysis-tasks", json=body, headers={"Idempotency-Key": command_key})
    if response.status_code != 202:
        raise ValueError("EVALUATION_TASK_CREATE_REJECTED")
    created = response.json()
    task_id = created.get("taskRef", {}).get("taskId")
    if not isinstance(task_id, str):
        raise ValueError("EVALUATION_TASK_REFERENCE_MISSING")
    deadline = time.monotonic() + wait_seconds
    current = created
    while current.get("state") not in {"SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED"}:
        if time.monotonic() >= deadline:
            return created, current, None
        time.sleep(poll_seconds)
        response = client.get("/api/v1/analysis-tasks/" + task_id)
        if response.status_code != 200:
            raise ValueError("EVALUATION_TASK_READ_REJECTED")
        current = response.json()
    report = None
    if current.get("state") == "SUCCEEDED":
        response = client.get("/api/v1/analysis-tasks/" + task_id + "/report")
        if response.status_code != 200:
            raise ValueError("EVALUATION_REPORT_READ_REJECTED")
        report = response.json()
    return created, current, report


def _process_environment(*, repository, catalog_path, evaluation_ref, private_output, authorization_id=FIXED_AUTHORIZATION_ID):
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    roots = [str(Path(repository) / "src"), str(repository)]
    environment["PYTHONPATH"] = os.pathsep.join(roots + ([existing] if existing else []))
    environment.update(
        COMMERCE_S01_MODEL_EVALUATION_ENABLED="true",
        COMMERCE_S01_MODEL_EVALUATION_AUTHORIZATION_ID=authorization_id,
        COMMERCE_S01_MODEL_EVALUATION_REF=evaluation_ref,
        COMMERCE_S01_MODEL_EVALUATION_PRIVATE_OUTPUT=str(private_output),
        COMMERCE_MAX_DELIVERY_ATTEMPTS="1",
        COMMERCE_TASK_DEADLINE_SECONDS="600",
    )
    if catalog_path:
        environment["COMMERCE_S01_MODEL_EVALUATION_CATALOG_PATH"] = str(Path(catalog_path).resolve())
    else:
        environment.pop("COMMERCE_S01_MODEL_EVALUATION_CATALOG_PATH", None)
    return environment


def _start_managed_processes(*, environment, readiness_seconds=15):
    """Start owned API and Worker subprocesses; return their local API URL."""
    import httpx

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    common = dict(env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL, creationflags=creationflags)
    api = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "commerce_hub.bootstrap.s01_model_evaluation:create_app",
        "--factory", "--host", "127.0.0.1", "--port", str(port), "--no-access-log", "--no-server-header",
    ], **common)
    processes = [api]
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + readiness_seconds
    try:
        with httpx.Client(base_url=base_url, timeout=1, trust_env=False) as client:
            while time.monotonic() < deadline:
                if api.poll() is not None:
                    raise ValueError("EVALUATION_API_START_FAILED")
                try:
                    if client.get("/health/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            else:
                raise ValueError("EVALUATION_API_NOT_READY")
        worker = subprocess.Popen([
            sys.executable, "-m", "commerce_hub.bootstrap.s01_model_evaluation", "worker",
        ], **common)
        processes.append(worker)
        return base_url, processes
    except Exception:
        _stop_managed_processes(processes)
        raise


def _stop_managed_processes(processes):
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    for process in reversed(processes):
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-suite", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Explicit paid-call mode; up to five A-E cases")
    parser.add_argument("--authorization-id")
    parser.add_argument("--max-cost-usd")
    parser.add_argument("--request-risk-usd")
    parser.add_argument("--max-requests", type=int, default=5)
    parser.add_argument("--private-output", help="Raw result path under data/private/")
    parser.add_argument("--catalog-path", help="Controlled teaching-simulation catalog under data/private/")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--external-processes", action="store_true",
                        help="Use an already-running evaluation API/Worker instead of owned subprocesses")
    parser.add_argument("--wait-seconds", type=int, default=660)
    args = parser.parse_args(argv)
    if args.offline_suite and args.execute:
        raise ValueError("CHOOSE_ONE_MODE")
    if args.offline_suite:
        print(json.dumps(_offline_suite(), ensure_ascii=False))
        return 0
    if not args.execute:
        print(json.dumps(dict(status="NOT_RUN", network="DISABLED", reason="Explicit evaluation authorization required")))
        return 0
    if (not args.authorization_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", args.authorization_id) or
            not args.max_cost_usd or not args.request_risk_usd or not args.private_output):
        raise ValueError("EXPLICIT_AUTHORIZATION_BUDGET_AND_PRIVATE_OUTPUT_REQUIRED")

    from commerce_hub.orchestration.budget import amount
    cap = amount(args.max_cost_usd)
    request_risk = amount(args.request_risk_usd)
    policy = evaluation_policy(args.authorization_id)
    if (cap != policy["max_cost"] or args.max_requests != policy["max_requests"] or request_risk != policy["request_risk"]):
        raise ValueError("INVALID_EVALUATION_CAP")
    repository = Path(__file__).resolve().parents[1]
    private_root = (repository / "data" / "private").resolve()
    private_output = Path(args.private_output).resolve()
    if not private_output.is_relative_to(private_root):
        raise ValueError("PRIVATE_OUTPUT_REQUIRED")

    from datetime import datetime, timezone
    import httpx
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database, assert_migration_target
    from commerce_hub.scenarios.s01_backend import S01BackendHandler

    identity = _authorization_identity(args.authorization_id)
    tenant = policy["tenant"]
    if args.catalog_path:
        case_ids, entries, scope = evaluation_catalog(args.catalog_path, private_root=private_root, policy=policy)
    else:
        if policy["case_order"] is not None:
            raise ValueError("CONTROLLED_TEACHING_CATALOG_REQUIRED")
        from tests.support.backend import cases as backend_cases
        entries_by_id = backend_cases()
        case_ids = list("ABCDE")
        entries = [entries_by_id[key] for key in case_ids]
        prepared = S01BackendHandler._prepare(entries[0])[1]
        scope = {**prepared, "tenantId": tenant}
    evaluation_ref = _catalog_evaluation_ref(args.authorization_id, case_ids, entries)
    api_base_url = _validate_api_base_url(args.api_base_url)
    if not 660 <= args.wait_seconds <= 900:
        raise ValueError("INVALID_EVALUATION_WAIT")
    settings = load_settings()
    if (settings.environment != "test" or settings.model_provider != "deepseek" or
            not settings.model_network_enabled or settings.model_name != "deepseek-flash"):
        raise ValueError("EXPLICIT_TEST_DEEPSEEK_FLASH_CONFIGURATION_REQUIRED")
    if args.external_processes and (
            settings.max_delivery_attempts != 1 or settings.task_deadline_seconds != 600):
        raise ValueError("EXTERNAL_EVALUATION_PROCESS_POLICY_MISMATCH")
    assert_migration_target(settings)
    database = Database(settings)
    try:
        if not database.schema_ready():
            raise ValueError("EXPLICIT_MIGRATION_REQUIRED")
        now = datetime.now(timezone.utc)
        # Cover the complete 600-second task deadline plus the bounded 660-900
        # second polling window without refreshing or replacing the fixed token.
        expires_at = _identity_expiration(now)
        principal_id, revision = _ensure_fixed_identity(
            database, settings, tenant=tenant, identity=identity, scope=scope, expires_at=expires_at, principal_id=policy["principal_id"],
        )
        token = _issue_token(
            settings, tenant=tenant, principal_id=principal_id, identity=identity,
            revision=revision, now=now, expires_at=expires_at,
        )
        body = dict(
            analysisMode="SINGLE", scenarioId="S01_MODEL_EVALUATION",
            scope={key: value for key, value in scope.items() if key != "tenantId"},
            parameters=dict(evaluationRef=evaluation_ref),
        )
        command_key = "evaluation-" + identity
        worker_private_output = private_output
        client_private_output = private_output.with_name(private_output.stem + "-client" + private_output.suffix)
        managed_processes = []
        try:
            if not args.external_processes:
                environment = _process_environment(
                    repository=repository, catalog_path=args.catalog_path,
                    evaluation_ref=evaluation_ref, private_output=worker_private_output, authorization_id=args.authorization_id,
                )
                api_base_url, managed_processes = _start_managed_processes(environment=environment)
            with httpx.Client(
                base_url=api_base_url, headers={"Authorization": "Bearer " + token},
                timeout=min(settings.model_timeout_seconds, 30), trust_env=False,
            ) as client:
                created, current, public = _create_and_wait(
                    client, body=body, command_key=command_key, wait_seconds=args.wait_seconds,
                    poll_seconds=max(0.2, min(settings.poll_seconds, 2)),
                )
        finally:
            _stop_managed_processes(managed_processes)
        if created.get("taskRef") != current.get("taskRef"):
            raise ValueError("EVALUATION_TASK_IDENTITY_CHANGED")
        evaluation = (public or {}).get("analysisReport", {}).get("evaluation", {})
        evaluation_status = evaluation.get("status")
        report = dict(
            status="PASS" if current.get("state") == "SUCCEEDED" and evaluation_status == "PASS" else
                "PENDING" if public is None and current.get("state") not in {"FAILED", "CANCELLED", "EXPIRED"} else "FAIL",
            taskRef=created["taskRef"], state=current.get("state"),
            authorizationId=args.authorization_id, evaluationRef=evaluation_ref,
            requestedCases=case_ids, configuredModel="deepseek-flash",
            publishedReportRef=public.get("reportRef") if public else None,
            evaluationStatus=evaluation_status, publicReport=public,
            maxRequests=args.max_requests, maxTotalCostUsd=str(cap), perRequestRiskUsd=str(request_risk),
        )
        client_private_output.parent.mkdir(parents=True, exist_ok=True)
        client_private_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        public_summary = {key: report[key] for key in (
            "status", "taskRef", "state", "evaluationRef", "requestedCases", "evaluationStatus", "publishedReportRef",
            "maxRequests", "maxTotalCostUsd", "perRequestRiskUsd",
        )}
        print(json.dumps(public_summary, ensure_ascii=False))
        return 0 if report["status"] == "PASS" else 2 if report["status"] == "PENDING" else 1
    finally:
        database.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit("S01 model evaluation stopped safely; no credential, prompt, raw response, or exception displayed") from None
