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
    nature = snapshot.projection.input.sourceNature
    demand_method = ("EXPLICIT_TEACHING_DAILY_CURVE" if nature == "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"
        else "EXPLICIT_VERIFIED_DAILY_CURVE" if nature == "TEACHING_ERP_OBSERVED"
        else "EXPLICIT_ENGINEERING_DAILY_CURVE")
    gap = Decimal(baseline["gapQuantity"])
    if gap == 0:
        # Total coverage does not imply timely coverage. The current policy has
        # no approved rule for expediting/reallocating supply or sizing a bridge order.
        reason = "INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED" if baseline["stockoutRisk"] else "NO_REPLENISHMENT_NEEDED"
        return dict(baseline=baseline, candidates=[], limitations=[reason], selection=None,
                    demandMethod=demand_method)
    with localcontext() as ctx:
        ctx.prec = 50
        # Candidate search lives in B02; daily quantities/risks are always B01 results.
        quantity = (max(gap, policy.moq) / policy.orderMultiple).to_integral_value(
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
    admitted = snapshot.projection.input.sourceNature in {"TEACHING_ERP_OBSERVED", "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"}
    return dict(baseline=baseline, candidates=candidates,
                limitations=["PROCUREMENT_EXECUTION_NOT_AUTHORIZED" if admitted else "ENGINEERING_RULES_UNVERIFIED"],
                selection=None, demandMethod=demand_method)
