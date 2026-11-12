"""D03 snapshot IDs travel unchanged through A01, while unrelated refs stay bounded."""
import pytest
from pydantic import ValidationError

from commerce_hub.capabilities.models.contracts import ModelRequest
from commerce_hub.scenarios.s01.explanation import ExplanationContext
from tests.support.s01 import snapshot
from tests.unit.models.support import fixture_bundle, fixture_request


def test_actual_d03_snapshot_is_accepted_without_truncation():
    snapshot_id = snapshot().snapshotId
    assert len(snapshot_id) == 73
    request = fixture_request().model_dump()
    request["snapshotId"] = snapshot_id
    assert ModelRequest.model_validate(request).snapshotId == snapshot_id
    context = fixture_bundle().context.model_dump()
    context["snapshotId"] = snapshot_id
    assert ExplanationContext.model_validate(context).snapshotId == snapshot_id


@pytest.mark.parametrize("snapshot_id", ["a" * 129, "invalid/snapshot", "", 123])
def test_invalid_snapshot_identifiers_remain_rejected(snapshot_id):
    request = fixture_request().model_dump()
    request["snapshotId"] = snapshot_id
    with pytest.raises(ValidationError):
        ModelRequest.model_validate(request)
    context = fixture_bundle().context.model_dump()
    context["snapshotId"] = snapshot_id
    with pytest.raises(ValidationError):
        ExplanationContext.model_validate(context)


def test_snapshot_bound_does_not_expand_task_or_other_identifiers():
    request = fixture_request().model_dump()
    request["logicalCallId"] = "a" * 65
    with pytest.raises(ValidationError):
        ModelRequest.model_validate(request)
