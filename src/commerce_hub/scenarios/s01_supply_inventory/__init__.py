"""S01 fixed workflow integration, explicitly synthetic and Mock-only."""
from copy import deepcopy
from decimal import Decimal
import json

from pydantic import ValidationError

from commerce_hub.adapters.models.mock import MockProvider
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.orchestration.budget import BudgetError
from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.scenarios.s01 import S01EngineeringHandler
from commerce_hub.scenarios.s01.explanation import Explanation, ExplanationContext, S01Bundle, digest, reserve_request

SEMANTIC_POLICY = "s01-exact-facts-v1"
LOGICAL_CALL = "s01-explanation-v1"
ATTEMPT = "s01-explanation-attempt-v1"


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def facts_for(result):
    """Select already computed quantity facts; never recalculate B01/B02 values.

    Exact fact quotation is deliberate: arbitrary prose is not semantically proven
    by checking numbers or forbidden words. This bounded engineering policy only
    accepts the complete four-category quotation set below.
    """
    data = result.dataReport
    supply = data["supplyDemand"]
    facts = [dict(ref="decision", kind="limitation", text="Engineering analysis only; completeness=" + result.completeness + "; procurement eligibility remains false.")]
    baseline = supply["baseline"]
    public_evidence = {item["fieldPath"]: item["evidenceId"] for item in data["evidence"] if item["fieldPath"].startswith("supplyDemand/")}
    if baseline is not None:
        fields = ("availableQuantity", "inTransitQuantity", "gapQuantity", "firstShortageDate", "stockoutRisk", "metricVersion", "metricResultRef")
        facts.append(dict(ref="baseline", kind="metric", text="B01 baseline " + _json(dict({k: baseline[k] for k in fields}, evidenceId=public_evidence["supplyDemand/baseline"]))))
    else:
        facts.append(dict(ref="baseline-missing", kind="gap", text="Baseline unavailable because required calculation inputs are missing or invalid."))
    for i, candidate in enumerate(supply["candidates"]):
        fields = ("candidateId", "quantity", "availableDate", "constraintVersion", "procurementEligible")
        facts.append(dict(ref=f"candidate-{i}", kind="candidate", text="B02 candidate " + _json(dict({k: candidate[k] for k in fields}, evaluationRef=candidate["evaluation"]["metricResultRef"], evidenceId=public_evidence[f"supplyDemand/candidates/{i}"]))))
    facts.append(dict(ref="quality", kind="limitation", text="Quality issues " + _json(sorted({issue["code"] for issue in data["quality"]})) + "; AI cannot clear required quality checks or investigations."))
    facts.append(dict(ref="limitations", kind="limitation", text="B02 limitations " + _json(supply["limitations"]) + "; all real business admission gates remain BLOCKED."))
    facts.append(dict(ref="human-review", kind="limitation", text="Human review of identity, data coverage, supply dates, constraints and quality is required. No procurement confirmation, approval or execution is authorized."))
    if data.get('forecast'):
        forecast = data['forecast']
        facts.append(dict(ref='forecast', kind='metric', text='Owner approved SMA policy ' + _json({k: forecast[k] for k in
            ('method','observationDays','windowStart','windowEnd','totalSales','averageDailyDemand','forecastDays','forecastQuantity','leadDays','coverageDays','calculationHorizonDays')})))
        facts.append(dict(ref='constraints', kind='limitation', text='ERP quote and advisory constraints ' + _json(forecast['constraints'])))
        if any(c['evaluation']['stockoutRisk'] for c in supply['candidates']):
            facts.append(dict(ref='candidate-arrival-risk', kind='limitation', text='Candidate arrival does not prevent the intermediate shortage shown by B01.'))
    return facts


def canonical_explanation(facts):
    by_ref = {f["ref"]: f for f in facts}
    def item(ref):
        return dict(text=by_ref[ref]["text"], supportRefs=[ref])
    baseline = "baseline" if "baseline" in by_ref else "baseline-missing"
    return dict(recommendationReasons=[item("decision")],
        keyEvidence=[item(baseline)] + [item(f["ref"]) for f in facts if f["kind"] == "candidate"],
        majorRisks=[item("quality"), item("limitations")], humanConfirmations=[item("human-review")])


def validate_semantics(output, facts):
    value = Explanation.model_validate(output).model_dump()
    if value != canonical_explanation(facts):
        raise ValueError("EXPLANATION_SEMANTICS_REJECTED")
    return value


def explanation_context(binding, facts):
    return ExplanationContext(ref=dict(tenantId=binding["taskRef"]["tenantId"],
        id="s01-context-" + digest(dict(binding=binding, facts=facts))[:48], version=SEMANTIC_POLICY),
        **binding, facts=facts, sourceNature="SIMULATED_ENGINEERING", trust="UNTRUSTED_DATA",
        sensitivity="SYNTHETIC_ONLY", omissions=["real-data", "real-model", "procurement-authorization"])


def validate_versions(ai, facts):
    versions = ai["versionBundle"]
    bundle = S01Bundle(explanation_context(ai["binding"], facts))
    expected = bundle.refs()
    refs = {key: expected[key] for key in ("deploymentRef", "promptRef", "contextBundleRef", "outputSchemaRef", "parametersRef", "cachePolicyRef")}
    if not isinstance(versions, dict) or set(versions) - (set(refs) | {"digests", "configuredModel"}):
        raise ValueError("BROKEN_S01_EXPLANATION_VERSIONS")
    if versions:
        if any(versions.get(key) != value for key,value in refs.items()) or versions.get("configuredModel") != "mock-s01-v1":
            raise ValueError("BROKEN_S01_EXPLANATION_VERSIONS")
        hashes = versions.get("digests", {})
        # Reuse the sender's pure resolver so all six hashes bind to the actual
        # Prompt, current Context, parameters, Schema and empty tool set.
        _, expected_hashes = bundle.resolve_content()
        if not isinstance(hashes, dict) or hashes != expected_hashes:
            raise ValueError("BROKEN_S01_EXPLANATION_VERSIONS")
    elif ai["status"] == "AVAILABLE":
        raise ValueError("BROKEN_S01_EXPLANATION_VERSIONS")


class S01MockProvider(MockProvider):
    """Use the existing Mock accounting/fault behavior with contextual success."""
    def invoke(self, request):
        result = super().invoke(request)
        if self.mode == "success":
            facts = json.loads(request.payload.messages[1].content)["facts"]
            result = result.model_copy(update={"content": _json(canonical_explanation(facts))})
        return result


class S01SupplyInventoryHandler:
    def __init__(self, provider=None, *, timeout_seconds=15):
        self.provider = provider if provider is not None else S01MockProvider()
        if not isinstance(self.provider, MockProvider):
            raise ValueError("S01_ENGINEERING_REQUIRES_MOCK_PROVIDER")
        self.gateway = ModelGateway(self.provider, timeout_seconds=timeout_seconds)
        self.rules = S01EngineeringHandler()

    @staticmethod
    def _parameters(parameters):
        if not isinstance(parameters, dict):
            raise ValueError("INVALID_PARAMETERS")
        value = deepcopy(parameters)
        previous = value.pop("_previousReportRef", None)
        if previous is not None and (not isinstance(previous, dict)
            or set(previous) != {"tenantId", "reportId"}
            or any(not isinstance(v, str) or not 1 <= len(v) <= 128 for v in previous.values())):
            raise ValueError("INVALID_PREVIOUS_REPORT_REFERENCE")
        return value, previous

    def bind_previous_report(self, parameters, reference):
        self.validate(parameters)
        value = deepcopy(parameters)
        value["_previousReportRef"] = deepcopy(reference)
        self._parameters(value)
        return value

    def validate(self, parameters):
        value, _ = self._parameters(parameters)
        self.rules.validate(value)

    def validate_scope(self, parameters, scope):
        value, previous = self._parameters(parameters)
        self.rules.validate_scope(value, scope)
        if previous is not None and previous["tenantId"] != scope["tenantId"]:
            raise ValueError("PREVIOUS_REPORT_TENANT_MISMATCH")

    @staticmethod
    def _binding(context, result):
        return dict(taskRef=dict(tenantId=context.principal.tenant_id, taskId=context.task["task_id"]),
            planVersion=str(context.task["plan_version"]), snapshotId=result.snapshotRef, participantId="s01")

    def run(self, context, parameters):
        # Existing D01/D02/D03/B01/B02 pipeline owns all authoritative assets.
        self.validate_scope(parameters, context.task["scope"])
        value, previous = self._parameters(parameters)
        result = self.rules.run(context, value)
        # Linkage is workflow metadata and cannot alter the fixed data manifest.
        result.dataReport["scenarioSupplement"]["previousReportRef"] = previous
        context.check()
        binding = self._binding(context, result)
        facts = facts_for(result)
        ai = dict(status="UNAVAILABLE", explanation=None, reason="AI_EXPLANATION_UNAVAILABLE",
            provider="MOCK", realModelAcceptance="NOT_RUN", semanticPolicy=SEMANTIC_POLICY,
            binding=binding, supportCatalog=facts, usageStatus="NOT_SENT", versionBundle={})
        try:
            context_value = explanation_context(binding, facts)
            bundle = S01Bundle(context_value)
            request = reserve_request(context, bundle, logical_call_id=LOGICAL_CALL, attempt_id=ATTEMPT,
                max_tokens=24000, max_cost=Decimal(".01"), trace_id=digest(binding)[:32])
            response = self.gateway.invoke(request, context, bundle)
            context.check()
            ai.update(reason=response.code, usageStatus=response.usageStatus, versionBundle=response.versionBundle)
            if response.status == "SUCCESS":
                ai["explanation"] = validate_semantics(response.validatedObject, facts)
                ai.update(status="AVAILABLE", reason="OK")
        except BudgetError:
            # Re-entry never changes call keys or reclaims the original allowance.
            ai["reason"] = "MODEL_ALLOWANCE_UNAVAILABLE"
        except (ValidationError, ValueError, TypeError, KeyError):
            ai["reason"] = "EXPLANATION_SEMANTICS_REJECTED"
        context.check()
        result = result.model_copy(update={"analysisReport": dict(ai=ai)})
        self.validate_publication(result, binding["taskRef"], binding["planVersion"])
        return result

    def validate_result(self, result):
        self.rules.validate_result(result)
        try:
            ai = result.analysisReport["ai"]
            facts = facts_for(result)
            if (set(ai) != {"status", "explanation", "reason", "provider", "realModelAcceptance", "semanticPolicy", "binding", "supportCatalog", "usageStatus", "versionBundle"}
                or ai["provider"] != "MOCK" or ai["realModelAcceptance"] != "NOT_RUN"
                or ai["semanticPolicy"] != SEMANTIC_POLICY or ai["supportCatalog"] != facts
                or ai["binding"]["snapshotId"] != result.snapshotRef
                or ai["binding"]["participantId"] != "s01"
                or ai["binding"]["taskRef"]["tenantId"] != result.scope["tenantId"]
                or ai["usageStatus"] not in {"KNOWN", "UNKNOWN", "NOT_SENT"}):
                raise ValueError("BROKEN_S01_EXPLANATION_BINDING")
            validate_versions(ai, facts)
            if ai["status"] == "AVAILABLE":
                if ai["reason"] != "OK" or ai["usageStatus"] not in {"KNOWN", "UNKNOWN"}:
                    raise ValueError("BROKEN_S01_EXPLANATION_BINDING")
                validate_semantics(ai["explanation"], facts)
            elif ai["status"] != "UNAVAILABLE" or ai["explanation"] is not None:
                raise ValueError("BROKEN_S01_EXPLANATION_BINDING")
        except (KeyError, TypeError, IndexError):
            raise ValueError("BROKEN_S01_EXPLANATION_BINDING") from None

    def validate_publication(self, result, task_ref, plan_version):
        self.validate_result(result)
        binding = result.analysisReport["ai"]["binding"]
        if binding["taskRef"] != task_ref or binding["planVersion"] != str(plan_version):
            raise ValueError("BROKEN_S01_TASK_BINDING")

    def report_view(self, report):
        result = DomainResult.model_validate({key: report[key] for key in DomainResult.model_fields})
        self.validate_publication(result, report["taskRef"], report["planVersion"])
        view = self.rules.report_view(report)
        # Every catalog value was selected from the same safe quantity facts.
        # No provider raw content, source fields, manifest or projection is exposed.
        view["dataReport"]["scenarioSupplement"]["previousReportRef"] = deepcopy(result.dataReport["scenarioSupplement"].get("previousReportRef"))
        view["analysisReport"] = deepcopy(result.analysisReport)
        return view
