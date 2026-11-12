"""Versioned server-side S01 inputs; existing D01-D04/B01/B02/O01 own the work."""
from copy import deepcopy
from decimal import Decimal

from commerce_hub.data.contracts import FixtureInput, AdmittedInput, fingerprint
from commerce_hub.data.sync import FixtureConnector
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture
from commerce_hub.data.evidence import locator
from commerce_hub.capabilities.forecasting import propose
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.orchestration.budget import BudgetError
from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.scenarios.s01_teaching import TeachingS01AdmissionHandler
from commerce_hub.scenarios.s01_supply_inventory import (
    S01MockProvider, facts_for, canonical_explanation, explanation_context,
    validate_semantics, validate_versions, LOGICAL_CALL, ATTEMPT, SEMANTIC_POLICY,
)
from commerce_hub.scenarios.s01.explanation import S01Bundle, digest, reserve_request
from commerce_hub.scenarios.s01.natural_explanation import (
    NATURAL_SEMANTIC_POLICY, NATURAL_SEMANTIC_POLICIES, bundle_for_result, validate_result_versions, validate_result_explanation,
)


def package_ref(kind, payload):
    return fingerprint(dict(kind=kind, payload=payload))


class S01BackendHandler:
    """Only a trusted composition root installs source packages, never HTTP clients."""
    def __init__(self, packages, *, provider=None, timeout_seconds=15, explanation_mode="mock", request_cost_reservation=Decimal(".01"), logical_namespace=None):
        if not isinstance(packages, list) or not 1 <= len(packages) <= 24:
            raise ValueError("INVALID_BACKEND_CATALOG")
        self.packages = {}
        for entry in deepcopy(packages):
            if set(entry) != {"kind", "payload"} or entry["kind"] not in {"OBSERVATION", "SIMULATED", "ADMITTED", "TEACHING_SIMULATION"}:
                raise ValueError("INVALID_BACKEND_PACKAGE")
            key = package_ref(entry["kind"], entry["payload"])
            if key in self.packages:
                raise ValueError("DUPLICATE_BACKEND_PACKAGE")
            self._prepare(entry)
            self.packages[key] = entry
        if explanation_mode not in {"mock", "natural"}:
            raise ValueError("INVALID_EXPLANATION_MODE")
        if provider is not None and explanation_mode == "mock" and not isinstance(provider, S01MockProvider):
            raise ValueError("BACKEND_LIVE_MODE_REQUIRES_SEPARATE_EVALUATION")
        if logical_namespace is not None and (len(logical_namespace) != 12 or any(c not in "0123456789abcdef" for c in logical_namespace)):
            raise ValueError("INVALID_LOGICAL_CALL_NAMESPACE")
        self.logical_namespace = logical_namespace
        self.provider = provider
        self.explanation_mode = explanation_mode
        from commerce_hub.orchestration.budget import amount
        self.request_cost_reservation = amount(request_cost_reservation)
        self.gateway = ModelGateway(provider, timeout_seconds=timeout_seconds) if provider else None

    def natural_logical_call(self, snapshot):
        return "s01-natural-" + (self.logical_namespace + "-" + snapshot[-32:] if self.logical_namespace else snapshot[-40:])

    @staticmethod
    def _prepare(entry):
        kind, payload = entry["kind"], entry["payload"]
        if kind == "OBSERVATION":
            handler = TeachingS01AdmissionHandler(payload)
            return handler, handler.projection.scope
        if kind == "SIMULATED":
            value, _ = FixtureConnector().read(payload)
        else:
            from commerce_hub.data.admission import normalize
            if kind == "TEACHING_SIMULATION":
                from commerce_hub.data.admission import TeachingAdmissionConnector
                value, _ = TeachingAdmissionConnector(payload).read()
            else:
                value = AdmittedInput.model_validate(normalize(payload))
        mapping = value.mapping
        # Tenant lives in the server package, not in source ERP business identifiers.
        tenant = payload["scope"]["tenantId"] if kind in {"ADMITTED", "TEACHING_SIMULATION"} else None
        return value, dict(tenantId=tenant, canonicalSkuIds=[mapping.canonicalSkuId],
            storeIds=[mapping.storeId], warehouseIds=[mapping.warehouseId], fields=["quantity"])

    @staticmethod
    def _parameters(parameters):
        if not isinstance(parameters, dict) or set(parameters) - {"packageRef", "_previousReportRef"} or not isinstance(parameters.get("packageRef"), str):
            raise ValueError("INVALID_BACKEND_PARAMETERS")
        previous = parameters.get("_previousReportRef")
        if previous is not None and (not isinstance(previous, dict) or set(previous) != {"tenantId", "reportId"}
            or any(not isinstance(v, str) or not 1 <= len(v) <= 64 for v in previous.values())):
            raise ValueError("INVALID_PREVIOUS_REPORT_REFERENCE")
        return parameters["packageRef"], previous

    def validate(self, parameters):
        key, _ = self._parameters(parameters)
        if key not in self.packages:
            raise ValueError("BACKEND_PACKAGE_NOT_AVAILABLE")

    def validate_scope(self, parameters, scope):
        self.validate(parameters)
        key, previous = self._parameters(parameters)
        _, expected = self._prepare(self.packages[key])
        if expected["tenantId"] is None:
            expected["tenantId"] = scope.get("tenantId")
        if scope != expected or not scope.get("tenantId"):
            raise ValueError("BACKEND_SCOPE_MISMATCH")
        if previous is not None and previous["tenantId"] != scope["tenantId"]:
            raise ValueError("PREVIOUS_REPORT_TENANT_MISMATCH")

    def bind_previous_report(self, parameters, reference):
        self.validate(parameters)
        value = dict(parameters, _previousReportRef=deepcopy(reference))
        self._parameters(value)
        return value

    def options(self, tenant_id):
        choices = []
        for key, entry in self.packages.items():
            prepared, scope = self._prepare(entry)
            if scope["tenantId"] not in {None, tenant_id}:
                continue
            scope["tenantId"] = tenant_id
            as_of = entry["payload"].get("asOf", entry["payload"].get("observedAt"))
            choices.append(dict(packageRef=key, sourceMode=entry["kind"], scope=scope, asOf=as_of,
                sourceNature=prepared.sourceNature if entry["kind"] != "OBSERVATION" else "TEACHING_ERP_OBSERVED"))
        return choices

    @staticmethod
    def _rules_result(entry, scope):
        value, _ = S01BackendHandler._prepare(entry)
        ref = package_ref(entry["kind"], entry["payload"])
        snapshot = capture(project(value, "source-package-" + ref))
        supply = propose(snapshot)
        paths = ["supplyDemand/baseline"] if supply["baseline"] is not None else []
        paths += [f"supplyDemand/candidates/{i}" for i in range(len(supply["candidates"]))]
        if snapshot.projection.inventory:
            paths.append("reliableFacts/inventory")
        paths.append("quality")
        issues = [issue.model_dump() for issue in snapshot.issues]
        inventory_valid = not any(i.severity == "BLOCK" and (i.path.startswith("inventory") or i.path in {"mapping", "coverageComplete"}) for i in snapshot.issues)
        reliable = dict(inventory=[dict(availableQuantity=str(row.availableQty), sourceUpdatedAt=row.sourceUpdatedAt.isoformat(), unit=row.unit)
            for row in snapshot.projection.inventory if row.availableQty is not None] if inventory_valid else [])
        simulated = entry["kind"] == "SIMULATED"
        teaching = entry["kind"] == "TEACHING_SIMULATION"
        supplement = dict(scenarioId="S01", engineeringFixture=simulated, procurementEligible=False,
            unverifiedRules=["ENGINEERING_RULES_UNVERIFIED"] if simulated else ["TEACHING_RULES_ONLY"] if teaching else [],
            realAdmission="BLOCKED" if simulated or teaching else "ADMITTED_READONLY_ANALYSIS",
            sourceMode=entry["kind"], sourceSynthetic=True if simulated else entry["payload"].get("sourceSynthetic", True),
            packageRef=ref, ruleVersion=value.policy.version, asOf=value.asOf.isoformat(),
            calculationStatus="BLOCKED" if not snapshot.calculation_allowed else "PASS",
            previousReportRef=None)
        return DomainResult(contractVersion="0.1.0", sourceNature=value.sourceNature,
            completeness="BLOCKED" if not snapshot.calculation_allowed else "PARTIAL" if not snapshot.candidates_allowed else "RULES_ONLY",
            scope=scope, snapshotRef=snapshot.snapshotId,
            dataReport=dict(manifest=snapshot.manifest, inputProjection=snapshot.projection.model_dump(mode="json"),
                sourcePackage=entry, quality=issues, supplyDemand=supply, reliableFacts=reliable,
                scenarioSupplement=supplement, evidence=[locator(snapshot.snapshotId, path) for path in paths]),
            analysisReport={})

    def run(self, context, parameters):
        self.validate_scope(parameters, context.task["scope"])
        key, previous = self._parameters(parameters)
        entry = self.packages[key]
        context.check()
        if entry["kind"] == "OBSERVATION":
            delegate, _ = self._prepare(entry)
            observed = delegate.run(context, {"packageRef": delegate.projection.revision})
            observed.dataReport.update(sourcePackage=deepcopy(entry))
            observed.dataReport["scenarioSupplement"].update(packageRef=key, previousReportRef=previous, sourceMode="OBSERVATION")
            return observed
        result = self._rules_result(entry, deepcopy(context.task["scope"]))
        result.dataReport["scenarioSupplement"]["previousReportRef"] = previous
        binding = dict(taskRef=dict(tenantId=context.principal.tenant_id, taskId=context.task["task_id"]),
            planVersion=str(context.task["plan_version"]), snapshotId=result.snapshotRef, participantId="s01")
        ai = dict(status="NOT_ATTEMPTED", explanation=None, reason="MODEL_NOT_ENABLED", binding=binding)
        if self.gateway and (entry["kind"] == "SIMULATED" or self.explanation_mode == "natural"):
            facts = facts_for(result)
            natural = self.explanation_mode == "natural"
            ai = dict(status="UNAVAILABLE", explanation=None, reason="AI_EXPLANATION_UNAVAILABLE", provider="MOCK",
                realModelAcceptance="NOT_RUN", semanticPolicy=SEMANTIC_POLICY, binding=binding,
                supportCatalog=facts, usageStatus="NOT_SENT", versionBundle={})
            if natural:
                ai.update(provider="AUTHORIZED_PROVIDER", realModelAcceptance="REVIEW", semanticPolicy=NATURAL_SEMANTIC_POLICY)
            try:
                bundle = bundle_for_result(result, binding) if natural else S01Bundle(explanation_context(binding, facts))
                logical = self.natural_logical_call(result.snapshotRef) if natural else LOGICAL_CALL
                attempt = logical + "-1" if natural else ATTEMPT
                request = reserve_request(context, bundle, logical_call_id=logical, attempt_id=attempt,
                    max_tokens=24000, max_cost=self.request_cost_reservation, trace_id=digest(binding)[:32])
                response = self.gateway.invoke(request, context, bundle)
                context.check()
                ai.update(reason=response.code, usageStatus=response.usageStatus, versionBundle=response.versionBundle,
                    tokenUsageStatus=response.tokenUsageStatus, costStatus=response.costStatus,
                    usage=response.usage.model_dump(mode="json") if response.usage else None, usageRef=response.usageRef,
                    actualModelRevision=response.actualModelRevision, auditRef=response.auditRef)
                if response.status == "SUCCESS":
                    ai.update(status="AVAILABLE", reason="OK", explanation=response.validatedObject if natural else validate_semantics(response.validatedObject, facts))
            except BudgetError:
                ai["reason"] = "MODEL_ALLOWANCE_UNAVAILABLE"
            except (ValueError, TypeError, KeyError):
                ai["reason"] = "EXPLANATION_SEMANTICS_REJECTED"
        result = result.model_copy(update={"analysisReport": dict(ai=ai)})
        context.check()
        self.validate_publication(result, binding["taskRef"], binding["planVersion"])
        return result

    def validate_publication(self, result, task_ref, plan_version):
        try:
            self._validate_publication(result, task_ref, plan_version)
        except (KeyError, TypeError, IndexError, AttributeError):
            raise ValueError("BACKEND_RESULT_BINDING_REJECTED") from None

    def _validate_publication(self, result, task_ref, plan_version):
        data = result.dataReport
        entry = data["sourcePackage"]
        key = package_ref(entry["kind"], entry["payload"])
        previous = data["scenarioSupplement"].get("previousReportRef")
        # Publication requires an installed package; historical reading validates its persisted copy.
        if key not in self.packages or self.packages[key] != entry:
            raise ValueError("BACKEND_PACKAGE_BINDING_REJECTED")
        self.validate_scope(dict(packageRef=key, _previousReportRef=previous), result.scope)
        if entry["kind"] == "OBSERVATION":
            delegate, _ = self._prepare(entry)
            clean = deepcopy(result)
            clean.dataReport.pop("sourcePackage")
            for field in ("packageRef", "previousReportRef", "sourceMode"):
                clean.dataReport["scenarioSupplement"].pop(field)
            delegate.validate_publication(clean, task_ref, plan_version)
            return
        expected = self._rules_result(entry, result.scope)
        expected.dataReport["scenarioSupplement"]["previousReportRef"] = previous
        if result.dataReport != expected.dataReport or result.snapshotRef != expected.snapshotRef or result.completeness != expected.completeness or result.sourceNature != expected.sourceNature:
            raise ValueError("BACKEND_CALCULATION_BINDING_REJECTED")
        ai = result.analysisReport["ai"]
        binding = dict(taskRef=task_ref, planVersion=str(plan_version), snapshotId=result.snapshotRef, participantId="s01")
        if ai["binding"] != binding:
            raise ValueError("BACKEND_TASK_BINDING_REJECTED")
        if ai["status"] == "NOT_ATTEMPTED":
            if ai != dict(status="NOT_ATTEMPTED", explanation=None, reason="MODEL_NOT_ENABLED", binding=binding):
                raise ValueError("BROKEN_BACKEND_AI")
        else:
            facts = facts_for(result)
            natural = ai.get("semanticPolicy") in NATURAL_SEMANTIC_POLICIES
            if ((not natural and (entry["kind"] != "SIMULATED" or ai["provider"] != "MOCK"
                    or ai["semanticPolicy"] != SEMANTIC_POLICY or ai["realModelAcceptance"] != "NOT_RUN"))
                or natural and (ai["provider"] != "AUTHORIZED_PROVIDER" or ai["realModelAcceptance"] != "REVIEW")
                or ai["supportCatalog"] != facts
                or ai["usageStatus"] not in {"KNOWN", "UNKNOWN", "NOT_SENT"}):
                raise ValueError("BROKEN_BACKEND_AI")
            if natural:
                if ai["versionBundle"]:
                    validate_result_versions(ai, result)
                elif ai["status"] == "AVAILABLE":
                    raise ValueError("BROKEN_BACKEND_AI")
            else:
                validate_versions(ai, facts)
            if ai["status"] == "AVAILABLE":
                if ai["reason"] != "OK" or ai["usageStatus"] not in {"KNOWN", "UNKNOWN"}:
                    raise ValueError("BROKEN_BACKEND_AI")
                if natural:
                    validate_result_explanation(ai, result)
                else:
                    validate_semantics(ai["explanation"], facts)
            elif ai["status"] != "UNAVAILABLE" or ai["explanation"] is not None:
                raise ValueError("BROKEN_BACKEND_AI")

    def validate_report_parameters(self, report, parameters):
        key, previous = self._parameters(parameters)
        supplement = report["dataReport"]["scenarioSupplement"]
        entry = report["dataReport"]["sourcePackage"]
        if (supplement["packageRef"] != key or package_ref(entry["kind"], entry["payload"]) != key
            or supplement.get("previousReportRef") != previous):
            raise ValueError("BACKEND_REPORT_INPUT_BINDING_REJECTED")

    def model_receipts(self, report):
        ai = report["analysisReport"]["ai"]
        # Only successful explanations expose a trusted usage receipt. Error facts
        # may still arrive late; they never authorize a result or a new request.
        return [ai] if ai.get("status") == "AVAILABLE" else []

    def report_view(self, report):
        result = DomainResult.model_validate({key: report[key] for key in DomainResult.model_fields})
        entry = result.dataReport["sourcePackage"]
        historical = S01BackendHandler([entry])
        historical.validate_publication(result, report["taskRef"], report["planVersion"])
        if entry["kind"] == "OBSERVATION":
            clean = deepcopy(report)
            clean["dataReport"].pop("sourcePackage")
            supplement = clean["dataReport"]["scenarioSupplement"]
            extra = {key: supplement.pop(key) for key in ("packageRef", "previousReportRef", "sourceMode")}
            view = TeachingS01AdmissionHandler(entry["payload"]).report_view(clean)
            view["dataReport"]["scenarioSupplement"].update(extra)
            return view
        view = {key: deepcopy(report[key]) for key in ("contractVersion", "sourceNature", "completeness", "scope",
            "snapshotRef", "taskRef", "reportRef", "planVersion", "scenarioId", "scenarioVersion", "participants")}
        view["dataReport"] = {key: deepcopy(result.dataReport[key]) for key in
            ("quality", "supplyDemand", "reliableFacts", "scenarioSupplement", "evidence")}
        view["dataReport"]["quality"] = [{key: item[key] for key in ("code", "severity", "affects")} for item in result.dataReport["quality"]]
        view["analysisReport"] = deepcopy(result.analysisReport)
        return view
