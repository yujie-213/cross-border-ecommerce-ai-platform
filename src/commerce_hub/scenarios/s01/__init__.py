"""Explicit engineering-only S01 workflow; no real source or model registration."""
from copy import deepcopy

from commerce_hub.capabilities.forecasting import propose
from commerce_hub.data.sync import FixtureConnector
from commerce_hub.data.projection import project, verify
from commerce_hub.data.quality import capture
from commerce_hub.data.evidence import locator, resolve
from commerce_hub.data.contracts import fingerprint
from commerce_hub.capabilities.metrics import METRIC_VERSION
from commerce_hub.orchestration.contracts import DomainResult


class S01EngineeringHandler:
    def report_view(self, report):
        """Fixed quantity-only engineering DTO, never an unrestricted asset dump.

        Full projection/manifest stay internal. Raw evidence locators are not
        capabilities and cannot be resolved through this public view.
        """
        data = report["dataReport"]
        self.validate_scope(data["inputProjection"]["input"], report["scope"])
        if report["sourceNature"] != "SIMULATED_ENGINEERING":
            raise ValueError("UNSUPPORTED_REPORT_SOURCE")
        def pick(value, fields):
            return {key: deepcopy(value[key]) for key in fields}
        def metric(value):
            if value is None:
                return None
            result = pick(value, ("metricVersion", "snapshotRef", "scenario", "availableQuantity",
                "inTransitQuantity", "averageDailyDemand", "coverageDays", "targetQuantity", "gapQuantity",
                "firstShortageDate", "closingBalance", "stockoutRisk", "overstockRisk", "semantics", "metricResultRef"))
            result["series"] = [pick(row, ("day", "demand", "arrivals", "closingBalance", "inBuffer")) for row in value["series"]]
            return result
        supply = data["supplyDemand"]
        if supply["selection"] is not None:
            raise ValueError("UNSUPPORTED_ENGINEERING_SELECTION")
        public_supply = pick(supply, ("limitations", "selection"))
        if "demandMethod" in supply:
            public_supply["demandMethod"] = supply["demandMethod"]
        public_supply["baseline"] = metric(supply["baseline"])
        public_supply["candidates"] = []
        paths = set()
        if supply["baseline"] is not None:
            paths.add("supplyDemand/baseline")
        for i, candidate in enumerate(supply["candidates"]):
            item = pick(candidate, ("candidateId", "quantity", "availableDate", "constraintVersion", "constraintRefs", "procurementEligible"))
            item["evaluation"] = metric(candidate["evaluation"])
            public_supply["candidates"].append(item)
            paths.add(f"supplyDemand/candidates/{i}")
        view = pick(report, ("contractVersion", "sourceNature", "completeness", "scope", "snapshotRef",
            "taskRef", "reportRef", "planVersion", "scenarioId", "scenarioVersion"))
        view["participants"] = [pick(item, ("scenarioId", "snapshotRef")) for item in report["participants"]]
        view["dataReport"] = dict(
            quality=[pick(issue, ("code", "severity", "affects")) for issue in data["quality"]],
            supplyDemand=public_supply,
            scenarioSupplement=pick(data["scenarioSupplement"], ("scenarioId", "engineeringFixture",
                "procurementEligible", "unverifiedRules", "realAdmission")),
            evidence=[deepcopy(item) for item in data["evidence"] if item["fieldPath"] in paths
                      and item == locator(report["snapshotRef"], item["fieldPath"])])
        # Only the disabled-model engineering status is supported in this slice.
        view["analysisReport"] = dict(ai=dict(status="NOT_ATTEMPTED", explanation=None, reason="MODEL_ADMISSION_BLOCKED"))
        return view

    def validate(self, parameters):
        FixtureConnector().read(parameters)

    def validate_scope(self, parameters, scope):
        value, _ = FixtureConnector().read(parameters)
        mapping = value.mapping
        if (scope.get("canonicalSkuIds") != [mapping.canonicalSkuId]
            or scope.get("storeIds") != [mapping.storeId]
            or scope.get("warehouseIds") != [mapping.warehouseId]
            or set(scope.get("fields", [])) != {"quantity"}):
            raise ValueError("FIXTURE_SCOPE_MISMATCH")

    def run(self, context, parameters):
        self.validate_scope(parameters, context.task["scope"])
        context.check()
        value, batch_id = FixtureConnector().read(parameters)
        snapshot = capture(project(value, batch_id))
        context.check()
        result = propose(snapshot)
        evidence = [locator(snapshot.snapshotId, "manifest")]
        if snapshot.projection.inventory:
            evidence.append(locator(snapshot.snapshotId, "inputProjection/inventory/0"))
        if result["baseline"] is not None:
            evidence.append(locator(snapshot.snapshotId, "supplyDemand/baseline"))
        for i, _ in enumerate(result["candidates"]):
            evidence.append(locator(snapshot.snapshotId, f"supplyDemand/candidates/{i}"))
        data = dict(manifest=snapshot.manifest, inputProjection=snapshot.projection.model_dump(mode="json"),
                    quality=[i.model_dump() for i in snapshot.issues], supplyDemand=result, evidence=evidence,
                    scenarioSupplement=dict(scenarioId="S01", engineeringFixture=True,
                    fixtureId=value.fixtureId, procurementEligible=False,
                    unverifiedRules=["identity-and-units", "demand-reservation", "availability-calendar",
                                     "buffer-and-backlog", "MOQ-and-order-multiple", "quality-and-hard-constraints"],
                    realAdmission="BLOCKED"))
        context.check()
        domain = DomainResult(contractVersion="0.1.0", sourceNature="SIMULATED_ENGINEERING",
                            completeness="BLOCKED" if not snapshot.calculation_allowed else
                            "PARTIAL" if not snapshot.candidates_allowed else "RULES_ONLY",
                            scope=context.task["scope"], snapshotRef=snapshot.snapshotId, dataReport=data,
                            analysisReport=dict(ai=dict(status="NOT_ATTEMPTED", explanation=None,
                            reason="MODEL_ADMISSION_BLOCKED")))
        self.validate_result(domain)
        return domain

    def validate_result(self, result):
        """Check asset bindings at publication without repeating business calculations."""
        if not isinstance(result, DomainResult):
            raise ValueError("INVALID_S01_RESULT")
        data = result.dataReport
        try:
            manifest, projection = data["manifest"], data["inputProjection"]
            verify(projection)
            self.validate_scope(projection["input"], result.scope)
            digest = fingerprint({k: v for k, v in manifest.items() if k != "fingerprint"})
            valid = (manifest["fingerprint"] == digest and result.snapshotRef == "snapshot-" + digest
                     and manifest["projectionRevision"] == projection["revision"]
                     and manifest["sourceBatchIds"] == [projection["sourceBatchId"]]
                     and manifest["sourceNature"] == result.sourceNature
                     and manifest["policyVersion"] == projection["input"]["policy"]["version"])
            metrics = [data["supplyDemand"]["baseline"]] + [c["evaluation"] for c in data["supplyDemand"]["candidates"]]
            for metric in metrics:
                if metric is not None:
                    valid = valid and (metric["snapshotRef"] == result.snapshotRef and metric["metricVersion"] == METRIC_VERSION
                        and metric["metricResultRef"] == "metric-" + fingerprint({k: v for k, v in metric.items() if k != "metricResultRef"}))
            report = result.model_dump(mode="json")
            for item in data["evidence"]:
                valid = valid and (item == locator(result.snapshotRef, item["fieldPath"])
                                   and resolve(report, item["evidenceId"]) is not None)
            if not valid:
                raise ValueError("BROKEN_S01_ASSET_BINDING")
        except (KeyError, TypeError, IndexError):
            raise ValueError("BROKEN_S01_ASSET_BINDING") from None
