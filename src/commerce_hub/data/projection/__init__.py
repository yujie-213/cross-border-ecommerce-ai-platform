"""D02 mapping, exact unit conversion and immutable projection; no metrics."""
from commerce_hub.data.contracts import Issue, Projection, fingerprint, CanonicalInventory, CanonicalDemand, CanonicalSupply
from decimal import localcontext


def project(value, batch_id):
    mapping, issues = value.mapping, []
    if mapping.sourceUnit == "EA" and mapping.unitsPerSourceUnit != 1:
        issues.append(Issue(code="UNIT_CONFLICT", severity="BLOCK", path="mapping", affects="CALCULATION"))
    projected = {}
    for group, quantities in (("inventory", ("availableQty", "reservedQty")),
                              ("demand", ("quantity",)), ("supply", ("remainingQty",))):
        seen, rows = {}, []
        for row in getattr(value, group):
            path = group + "/" + row.recordId
            if (row.sku, row.store, row.warehouse, row.unit) != (
                mapping.sourceSku, mapping.sourceStore, mapping.sourceWarehouse, mapping.sourceUnit
            ):
                issues.append(Issue(code="UNMAPPED_IDENTITY_OR_UNIT", severity="BLOCK", path=path, affects="CALCULATION"))
                continue
            # Supply mirrors use the business line identity, never the purchase header.
            key = row.supplyId if group == "supply" else row.recordId
            semantic = row.model_dump(exclude={"recordId"})
            if key in seen:
                issues.append(Issue(code="DUPLICATE_RECORD" if seen[key] == semantic else "CONFLICTING_RECORD",
                                    severity="WARN" if seen[key] == semantic else "BLOCK", path=path, affects="CALCULATION"))
                continue
            seen[key] = semantic
            updates = dict(sku=mapping.canonicalSkuId, store=mapping.storeId, warehouse=mapping.warehouseId, unit=mapping.unit)
            for field in quantities:
                number = getattr(row, field)
                with localcontext() as ctx:
                    ctx.prec = 50
                    updates[field] = None if number is None else number * mapping.unitsPerSourceUnit
            model = {"inventory": CanonicalInventory, "demand": CanonicalDemand, "supply": CanonicalSupply}[group]
            rows.append(model.model_validate(dict(row.model_dump(), **updates)))
        projected[group] = tuple(sorted(rows, key=lambda row: row.recordId))
    result = Projection(revision="", sourceBatchId=batch_id, input=value, issues=tuple(issues), **projected)
    body = result.model_dump(mode="json", exclude={"revision"})
    return result.model_copy(update={"revision": fingerprint(body)})


def verify(payload):
    """Validate a persisted projection's version, shape and content revision."""
    value = Projection.model_validate(payload)
    if value.revision != fingerprint(value.model_dump(mode="json", exclude={"revision"})):
        raise ValueError("PROJECTION_REVISION_MISMATCH")
    return value
