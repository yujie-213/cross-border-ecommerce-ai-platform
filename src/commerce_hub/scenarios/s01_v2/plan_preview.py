"""Read-only plan evaluation over the sealed product decision; no ERP or model."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from commerce_hub.capabilities.metrics import evaluate
from commerce_hub.data.contracts import fingerprint
from .decision import snapshot_for


def preview_plan(item, quantity, available_date):
    decision = item.get('decision') or {}
    baseline = decision.get('baseline') or {}
    rows = baseline.get('series') or []
    if not item.get('identityVerified') or not rows or not decision.get('forecast', {}).get('available'):
        raise ValueError('PLAN_BASELINE_UNAVAILABLE')
    if type(quantity) is not int or not 1 <= quantity <= 100000:
        raise ValueError('PLAN_QUANTITY_INVALID')
    start, end = date.fromisoformat(rows[0]['day']), date.fromisoformat(rows[-1]['day'])
    if not start <= available_date <= end:
        raise ValueError('PLAN_DATE_OUTSIDE_WINDOW')
    # Reconstruct exactly the existing product-demand snapshot. Never infer a
    # new daily demand curve from totals or include unverified existing supply.
    constraints = dict(item.get('constraints') or {}, leadDays=decision.get('leadDays'))
    snapshot = snapshot_for(item, datetime.fromisoformat(item['observedAt']), start - timedelta(days=1),
        baseline['availableQuantity'], decision['forecast']['averageDailyDemand'], decision['horizonDays'], constraints)
    original = evaluate(snapshot)
    if original['series'] != rows or original['metricVersion'] != baseline.get('metricVersion'):
        raise ValueError('PLAN_BASELINE_VERSION_MISMATCH')
    candidate = dict(candidateId='preview-' + fingerprint([item['entityKey'], quantity, available_date.isoformat(), snapshot.snapshotId]),
        quantity=Decimal(quantity), availableDate=available_date)
    evaluation = evaluate(snapshot, candidate=candidate)
    return dict(entityKey=item['entityKey'], observedAt=item['observedAt'], quantity=quantity,
        availableDate=available_date.isoformat(), windowStart=start.isoformat(), windowEnd=end.isoformat(),
        evaluation=evaluation, semantics='HYPOTHETICAL_PLAN_NOT_CONFIRMED_SUPPLY')
