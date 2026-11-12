"""B02: bounded explicit demand scenario and MOQ/multiple candidate construction."""
from decimal import Decimal, ROUND_CEILING, localcontext

from commerce_hub.capabilities.metrics import evaluate
from commerce_hub.data.contracts import fingerprint


def propose(snapshot, evaluator=evaluate):
    if not snapshot.calculation_allowed:
        return dict(baseline=None, candidates=[], limitations=["DATA_QUALITY_BLOCKED"], selection=None)
    baseline = evaluator(snapshot)
    if not snapshot.candidates_allowed:
        return dict(baseline=baseline, candidates=[], limitations=["CANDIDATE_RULES_OR_QUALITY_BLOCKED"], selection=None)
    policy = snapshot.projection.input.policy
    with localcontext() as ctx:
        ctx.prec = 50
        gap = Decimal(baseline["gapQuantity"])
        # Candidate search lives in B02; daily quantities/risks are always B01 results.
        quantity = Decimal(0) if gap == 0 else (max(gap, policy.moq) / policy.orderMultiple).to_integral_value(
            rounding=ROUND_CEILING) * policy.orderMultiple
    if quantity > policy.maxOrderQty:
        return dict(baseline=baseline, candidates=[], limitations=["NO_FEASIBLE_QUANTITY"], selection=None)
    candidates = []
    for day in sorted(set(policy.candidateDates)):
        candidate_id = "candidate-" + fingerprint([snapshot.snapshotId, str(quantity), day.isoformat()])
        value = dict(candidateId=candidate_id, quantity=quantity, availableDate=day)
        evaluation = evaluator(snapshot, candidate=value)
        candidates.append(dict(candidateId=candidate_id, quantity=str(quantity), availableDate=day.isoformat(),
                               constraintVersion=policy.version, constraintRefs=[snapshot.snapshotId + "#/inputProjection/input/policy"],
                               evaluation=evaluation, procurementEligible=False))
    # No invented weights/optimality. Unresolved intermediate shortages remain visible.
    return dict(baseline=baseline, candidates=candidates, limitations=["ENGINEERING_RULES_UNVERIFIED"],
                selection=None, demandMethod="EXPLICIT_ENGINEERING_DAILY_CURVE")
