from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from commerce_hub.capabilities.models.contracts import ModelRequest
from commerce_hub.scenarios.s01.explanation import ExplanationContext, S01Bundle


def fixture_bundle(tenant="tenant-fixture", task="task-fixture", **options):
    return S01Bundle(ExplanationContext(ref={"tenantId": tenant, "id": "context-s01", "version": "1"},
        taskRef={"tenantId": tenant, "taskId": task}, planVersion="1", participantId="p-s01",
        snapshotId="snapshot-s01", facts=[{"ref": "fact-1", "kind": "limitation", "text": "Synthetic facts only; human review is required."}],
        sourceNature="SIMULATED_ENGINEERING", trust="UNTRUSTED_DATA", sensitivity="SYNTHETIC_ONLY", omissions=["real-business-inputs"]), **options)


def fixture_request(bundle=None):
    bundle = bundle or fixture_bundle()
    return ModelRequest(schemaVersion="0.2", logicalCallId="call-1", attemptId="attempt-1", taskRef=bundle.context.taskRef,
        queryRef=None, planVersion="1", participantId="p-s01", snapshotId="snapshot-s01",
        principalRef={"tenantId": bundle.context.ref.tenantId, "principalId": "principal-fixture"},
        policyContextRef={"id": "fixture-policy", "version": "1"}, requiredCapabilities=["structured_output"],
        toolSpecRefs=[], allowanceRef={"tenantId": bundle.context.ref.tenantId, "id": "attempt-1", "version": "1"},
        deadline=datetime.now(timezone.utc)+timedelta(seconds=20), traceId="a"*32, parentSpanId="span-1", **bundle.refs())


def fixture_control():
    budget = Mock()
    budget.validate_model_call.side_effect = lambda **kw: dict(state="RESERVED", max_tokens=20000,
        max_cost=Decimal("1"), now=datetime.now(timezone.utc))
    budget.settle.return_value = "usage-fixture"
    budget.model_event.return_value = "audit-fixture"
    return SimpleNamespace(check=Mock(), budget=budget)
