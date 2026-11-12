"""Default-off, one-request synthetic DeepSeek connectivity probe. Not a C-04 evaluation.

Never run --execute without separate human paid-call authorization and a stated USD cap.
Without --execute this module performs no settings read, DB access or network activity.
"""
import argparse
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
import os
import re
import threading


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true",help="Requires separate explicit paid-call authorization")
    parser.add_argument("--authorization-id",help="Stable ID for this human authorization; cannot be reused for a second probe")
    parser.add_argument("--max-cost-usd",help="Explicit maximum USD exposure for this ONE request (<=1 USD)")
    args=parser.parse_args(argv)
    if not args.execute:
        print(json.dumps(dict(status="NOT_RUN",network="DISABLED",reason="Separate paid-call authorization and USD budget required")))
        return 0
    if not args.authorization_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}",args.authorization_id) or not args.max_cost_usd:
        raise ValueError("EXPLICIT_AUTHORIZATION_AND_BUDGET_REQUIRED")
    from commerce_hub.orchestration.budget import amount
    cap=amount(args.max_cost_usd)
    if not Decimal("0")<cap<=Decimal("1"):
        raise ValueError("INVALID_PROBE_CAP")
    from sqlalchemy import func,select
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database,assert_migration_target
    from commerce_hub.infrastructure.work import WorkStore
    from commerce_hub.governance.access import AccessControl
    from commerce_hub.governance.observability.service import Audit
    from commerce_hub.orchestration.service import TaskService,HandlerSpec
    from commerce_hub.orchestration.worker import ExecutionContext
    from commerce_hub.adapters.models.deepseek import DeepSeekProvider,ConnectivityAuthorization
    from commerce_hub.capabilities.models.gateway import ModelGateway
    from commerce_hub.scenarios.s01.explanation import ExplanationContext,S01Bundle,reserve_request
    settings=load_settings()
    if settings.environment!="test" or settings.model_provider!="deepseek" or not settings.model_network_enabled:
        raise ValueError("EXPLICIT_TEST_ENVIRONMENT_AND_NETWORK_ENABLE_REQUIRED")
    assert_migration_target(settings)
    provider=DeepSeekProvider(settings,authorization=ConnectivityAuthorization(args.authorization_id,cap))
    # Stable tenant and command prevent a restarted process from consuming the same authorization again.
    identity=hashlib.sha256(args.authorization_id.encode()).hexdigest()[:32]
    tenant="c01-probe-"+identity
    scope=dict(tenantId=tenant,storeIds=["synthetic-store"],warehouseIds=["synthetic-warehouse"],
        canonicalSkuIds=["synthetic-sku"],fields=["status"])
    database=Database(settings)
    try:
        if not database.schema_ready(): raise ValueError("EXPLICIT_MIGRATION_REQUIRED")
        access=AccessControl(database.engine,"c01-connectivity-fixture","c01-connectivity-fixture",os.urandom(48))
        # Unique fixture principal insertion is the durable one-use authorization marker. Duplicate fails closed.
        with database.engine.begin() as conn:
            now=conn.scalar(select(func.utc_timestamp(6)))
            principal=access.provision_fixture(conn,tenant_id=tenant,principal_id="synthetic-probe",token_id=identity,
                expires_at=now+timedelta(minutes=2),grants_by_action={a:scope for a in ["tasks:create","tasks:read","engineering:execute"]})
        class ProbeHandler:
            def validate(self,parameters):
                if parameters!={"sourceNature":"SYNTHETIC_CONNECTIVITY_ONLY"}: raise ValueError("INVALID_PROBE")
        spec=HandlerSpec("ENGINEERING_C01_CONNECTIVITY","1","c01.connectivity."+identity,ProbeHandler(),
            max_calls=1,max_tokens=20000,max_cost=cap,policy_version="c01-connectivity-peak-ceiling-20261112")
        queue=WorkStore(database.engine,lease_seconds=60)
        service=TaskService(database.engine,access,queue,Audit(),{spec.scenario_id:spec},deadline_seconds=45,max_attempts=1)
        view=service.create(principal,"connectivity-once",spec.scenario_id,scope,{"sourceNature":"SYNTHETIC_CONNECTIVITY_ONLY"},identity)
        lease=queue.claim([spec.work_kind])
        if lease is None: raise ValueError("PROBE_ALREADY_CLAIMED")
        task=service.start(lease,principal)
        context=ExecutionContext(service,lease,principal,dict(task),threading.Event())
        bundle=S01Bundle(ExplanationContext(ref={"tenantId":tenant,"id":"synthetic-context","version":"1"},
            taskRef=view["taskRef"],planVersion="1",participantId="synthetic-s01",snapshotId="synthetic-snapshot",
            facts=[{"ref":"fact-1","kind":"limitation","text":"Synthetic training example only. Human review is required; no purchase is authorized."}],
            sourceNature="SIMULATED_ENGINEERING",trust="UNTRUSTED_DATA",sensitivity="SYNTHETIC_ONLY",omissions=["all-real-business-data"]),
            deployment_id="deepseek-connectivity",model="deepseek-flash",max_output_tokens=128)
        # Preflight before send is also applied inside A01 and the provider. No secret/body is printed.
        request=reserve_request(context,bundle,logical_call_id="connectivity-1",attempt_id="connectivity-attempt-1",
            max_tokens=20000,max_cost=cap,trace_id=identity)
        result=ModelGateway(provider,timeout_seconds=min(settings.model_timeout_seconds,20),max_concurrent=1).invoke(request,context,bundle)
        # Reportless engineering task. Accounting UNKNOWN remains reserved even after this task terminates.
        service.fail(lease,result.code,retryable=False)
        print(json.dumps(dict(status=result.status,code=result.code,usageStatus=result.usageStatus,
            taskRef=view["taskRef"],maxRequests=1,maxOutputTokens=128,maxCostUsd=str(cap),
            model=result.actualModelRevision,auditRef=result.auditRef,usageRef=result.usageRef,
            sourceNature="SYNTHETIC_CONNECTIVITY_ONLY",purposeAdmission="BLOCKED",c04="NOT_RUN")))
        return 0 if result.code=="USAGE_UNKNOWN" else 1
    finally:
        database.close()


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit("Connectivity probe stopped safely; no credential, prompt or raw exception displayed") from None
