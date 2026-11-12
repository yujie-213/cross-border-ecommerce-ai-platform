"""D04 locators only. Assets are read through the authorized O01 report port."""
from commerce_hub.data.contracts import fingerprint


def locator(snapshot_id, path):
    module = {"inputProjection": "D02", "manifest": "D03"}.get(path.split("/")[0], "B01" if path == "supplyDemand/baseline" else "B02")
    return dict(evidenceId="evidence-" + fingerprint([snapshot_id, path]),
                snapshotId=snapshot_id, sourceModuleId=module, fieldPath=path)


def resolve(report, evidence_id):
    """Caller must supply a report returned by its current-authorized read port."""
    for item in report["dataReport"]["evidence"]:
        if item["evidenceId"] == evidence_id:
            value = report["dataReport"]
            try:
                for part in item["fieldPath"].split("/"):
                    value = value[int(part)] if isinstance(value, list) else value[part]
            except (KeyError, IndexError, TypeError, ValueError):
                return None
            return dict(locator=item, value=value)
    return None
