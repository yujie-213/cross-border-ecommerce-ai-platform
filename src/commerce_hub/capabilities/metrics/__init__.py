"""B01: the only evaluator of inventory, daily balances and shortage metrics."""
from datetime import timedelta
from decimal import Decimal, localcontext

from commerce_hub.data.contracts import fingerprint

METRIC_VERSION = "s01-engineering-daily-v1"


def evaluate(snapshot, *, candidate=None):
    if not snapshot.calculation_allowed:
        raise ValueError("DATA_QUALITY_BLOCKED")
    # Fixed engineering semantics: D0 is asOf UTC date; D1 follows D0;
    # same-day supply enters before incremental demand; negative balances backlog.
    with localcontext() as ctx:
        ctx.prec = 50
        projection = snapshot.projection
        policy = projection.input.policy
        start = projection.input.asOf.date()
        horizon_end = start + timedelta(days=policy.horizonDays)
        end = horizon_end + timedelta(days=policy.bufferDays)
        available = projection.inventory[0].availableQty
        arrivals = {day: Decimal(0) for day in (d.day for d in projection.demand)}
        for supply in projection.supply:
            if supply.status == "OPEN" and supply.availableDate in arrivals:
                arrivals[supply.availableDate] += supply.remainingQty
        existing = sum(arrivals.values(), Decimal(0))
        if candidate is not None:
            quantity, day = candidate["quantity"], candidate["availableDate"]
            if quantity < 0 or day not in arrivals:
                raise ValueError("INVALID_CANDIDATE")
            arrivals[day] += quantity
        balance, first, rows = available, None, []
        target = sum((d.quantity for d in projection.demand), Decimal(0))
        operational = sum((d.quantity for d in projection.demand if d.day <= horizon_end), Decimal(0))
        for demand in sorted(projection.demand, key=lambda d: d.day):
            balance += arrivals[demand.day] - demand.quantity
            if balance < 0 and first is None:
                first = demand.day
            rows.append(dict(day=demand.day.isoformat(), demand=str(demand.quantity),
                             arrivals=str(arrivals[demand.day]), closingBalance=str(balance),
                             inBuffer=demand.day > horizon_end))
        avg = operational / Decimal(policy.horizonDays)
        result = dict(metricVersion=METRIC_VERSION, snapshotRef=snapshot.snapshotId,
                      scenario="BASELINE" if candidate is None else candidate["candidateId"],
                      availableQuantity=str(available), inTransitQuantity=str(existing),
                      averageDailyDemand=str(avg), coverageDays=None if avg == 0 else str(available / avg),
                      targetQuantity=str(target), gapQuantity=str(max(Decimal(0), target - available - existing)),
                      firstShortageDate=None if first is None else first.isoformat(),
                      closingBalance=str(balance), stockoutRisk=first is not None,
                      overstockRisk=balance > target, series=rows,
                      semantics="NET_AVAILABLE;INCREMENTAL_EXCLUDES_RESERVED;D1_AFTER_D0;SUPPLY_BEFORE_DEMAND;BACKLOG;BUFFER_INCLUDED")
        result["metricResultRef"] = "metric-" + fingerprint(result)
        return result
