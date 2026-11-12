"""Fixed real teaching-source admission workflow; no real business/AI mode is enabled."""
from copy import deepcopy
from commerce_hub.data.projection.observed import verify_observations
from commerce_hub.data.quality.observed import capture_observations
from commerce_hub.data.evidence import locator
from commerce_hub.capabilities.forecasting import propose
from commerce_hub.orchestration.contracts import DomainResult

class TeachingS01AdmissionHandler:
    def __init__(self, projection):
        self.projection = verify_observations(deepcopy(projection))

    def validate(self, parameters):
        if parameters != {"packageRef": self.projection.revision}:
            raise ValueError("TEACHING_PACKAGE_MISMATCH")

    def validate_scope(self, parameters, scope):
        self.validate(parameters)
        if scope != self.projection.scope or scope.get("fields") != ["quantity"]:
            raise ValueError("TEACHING_SCOPE_MISMATCH")

    def run(self, context, parameters):
        self.validate_scope(parameters, context.task["scope"])
        context.check()
        snapshot = capture_observations(self.projection)
        # Existing B02 observes the existing quality gate; B01 must not run on missing inputs.
        supply = propose(snapshot)
        result = DomainResult(contractVersion="0.1.0", sourceNature="TEACHING_ERP_OBSERVED", completeness="BLOCKED",
            scope=deepcopy(context.task["scope"]), snapshotRef=snapshot.snapshotId,
            dataReport=dict(manifest=snapshot.manifest, observationProjection=self.projection.model_dump(mode="json"),
                observedDomains=[d.model_dump(mode="json") for d in self.projection.domains],
                quality=[i.model_dump() for i in snapshot.issues], supplyDemand=supply,
                scenarioSupplement=dict(engineeringFixture=False, sourceSynthetic=self.projection.sourceSynthetic,
                    ownerConfirmed=self.projection.ownerConfirmed, sampleRef="SKU-B", realAdmission="BLOCKED",
                    procurementEligible=False, deterministicCalculation="NOT_RUN_INPUTS_AND_RULES_BLOCKED"),
                evidence=[locator(snapshot.snapshotId, "observedDomains")]),
            analysisReport=dict(ai=dict(status="NOT_ATTEMPTED", reason="DETERMINISTIC_ADMISSION_ONLY"),
                binding=dict(taskRef=dict(tenantId=context.principal.tenant_id, taskId=context.task["task_id"]),
                    planVersion=str(context.task["plan_version"]))))
        context.check()
        self.validate_publication(result, result.analysisReport["binding"]["taskRef"], str(context.task["plan_version"]))
        return result

    def validate_result(self, result):
        try:
            self.validate_scope({"packageRef":self.projection.revision}, result.scope)
            expected = capture_observations(self.projection)
            data = result.dataReport
            if (result.sourceNature != "TEACHING_ERP_OBSERVED" or result.completeness != "BLOCKED"
                or result.snapshotRef != expected.snapshotId or data["manifest"] != expected.manifest
                or data["observationProjection"] != self.projection.model_dump(mode="json")
                or data["observedDomains"] != [d.model_dump(mode="json") for d in self.projection.domains]
                or data["quality"] != [i.model_dump() for i in expected.issues]
                or data["supplyDemand"] != propose(expected)
                or data["scenarioSupplement"] != dict(engineeringFixture=False,sourceSynthetic=self.projection.sourceSynthetic,
                    ownerConfirmed=self.projection.ownerConfirmed,sampleRef="SKU-B",realAdmission="BLOCKED",procurementEligible=False,
                    deterministicCalculation="NOT_RUN_INPUTS_AND_RULES_BLOCKED")
                or data["evidence"] != [locator(expected.snapshotId,"observedDomains")]
                or result.analysisReport["ai"] != dict(status="NOT_ATTEMPTED",reason="DETERMINISTIC_ADMISSION_ONLY")):
                raise ValueError("TEACHING_RESULT_BINDING_REJECTED")
        except (KeyError, TypeError, AttributeError):
            raise ValueError("TEACHING_RESULT_BINDING_REJECTED") from None

    def validate_publication(self, result, task_ref, plan_version):
        self.validate_result(result)
        if result.analysisReport["binding"] != dict(taskRef=task_ref,planVersion=str(plan_version)):
            raise ValueError("TEACHING_PUBLICATION_BINDING_REJECTED")

    def report_view(self, report):
        result = DomainResult.model_validate({k:report[k] for k in DomainResult.model_fields})
        historical = TeachingS01AdmissionHandler(result.dataReport["observationProjection"])
        historical.validate_publication(result,report["taskRef"],report["planVersion"])
        view = {k:deepcopy(report[k]) for k in ("contractVersion","sourceNature","completeness","scope","snapshotRef",
            "taskRef","reportRef","planVersion","scenarioId","scenarioVersion","participants")}
        view["dataReport"] = {k:deepcopy(result.dataReport[k]) for k in
            ("observedDomains","quality","supplyDemand","scenarioSupplement","evidence")}
        view["analysisReport"] = deepcopy(result.analysisReport)
        return view
