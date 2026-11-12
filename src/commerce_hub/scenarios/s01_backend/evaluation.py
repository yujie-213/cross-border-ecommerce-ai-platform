"""One authorized evaluation task; all cases share the original O01 budget."""
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.scenarios.s01.natural_explanation import bundle_for_result
from . import S01BackendHandler, package_ref


class S01ModelEvaluationHandler:
    def __init__(self, entries, case_ids, scope, evaluation_ref, *, authorization_id,
                 provider=None, timeout_seconds=30, private_output=None, case_order=None,
                 tenant_id=None, principal_id="s01-model-evaluator", logical_namespace=None):
        if (not case_ids or (case_order is None and case_ids[0] != "A")
            or (case_order is not None and tuple(case_ids) != tuple(case_order)) or len(case_ids) != len(set(case_ids))
            or len(entries) != len(case_ids) or not set(case_ids) <= set("ABCDE")):
            raise ValueError("INVALID_EVALUATION_CASES")
        self.backend = S01BackendHandler(entries, provider=provider, timeout_seconds=timeout_seconds,
            explanation_mode="natural", request_cost_reservation=Decimal(".05"), logical_namespace=logical_namespace)
        self.entries, self.case_ids = deepcopy(entries), list(case_ids)
        self.scope, self.evaluation_ref = deepcopy(scope), evaluation_ref
        self.authorization_id = authorization_id
        identity = hashlib.sha256(authorization_id.encode()).hexdigest()[:32]
        self.command_key = "evaluation-" + identity
        self.tenant = tenant_id or "s01-eval-" + identity
        self.principal_id = principal_id
        if scope["tenantId"] != self.tenant:
            raise ValueError("EVALUATION_TENANT_MISMATCH")
        for entry in entries:
            self.backend.validate_scope(dict(packageRef=package_ref(entry["kind"], entry["payload"])), scope)
        self.provider, self.private_output = provider, Path(private_output) if private_output else None

    def validate(self, parameters):
        if parameters != dict(evaluationRef=self.evaluation_ref):
            raise ValueError("INVALID_EVALUATION_PARAMETERS")

    def validate_scope(self, parameters, scope):
        self.validate(parameters)
        if scope != self.scope:
            raise ValueError("EVALUATION_SCOPE_MISMATCH")

    def validate_command(self, principal, key):
        if (principal.tenant_id != self.tenant or principal.principal_id != self.principal_id
            or key != self.command_key):
            raise ValueError("FIXED_EVALUATION_COMMAND_REQUIRED")

    @staticmethod
    def _compact(case_id, result):
        return dict(caseId=case_id, packageRef=result.dataReport["scenarioSupplement"]["packageRef"],
            snapshotRef=result.snapshotRef, completeness=result.completeness, sourceNature=result.sourceNature,
            analysisReport=deepcopy(result.analysisReport))

    def _summary(self, rows):
        return dict(authorizationId=self.authorization_id, evaluationRef=self.evaluation_ref,
            status="PASS" if len(rows) == len(self.case_ids) and all(
                row["analysisReport"]["ai"]["status"] == "AVAILABLE" for row in rows) else "FAIL",
            requestedCases=self.case_ids, cases=[dict(caseId=row["caseId"], sourceNature=row["sourceNature"],
                snapshotRef=row["snapshotRef"], completeness=row["completeness"], ai=deepcopy(row["analysisReport"]["ai"]))
                for row in rows], notRunCases=self.case_ids[len(rows):])

    def _persist_private(self, context, rows):
        if self.private_output is None:
            return
        exchanges = []
        for row in rows:
            logical = self.backend.natural_logical_call(row["snapshotRef"])
            exchange = self.provider.exchange(logical) if hasattr(self.provider, "exchange") else None
            exchanges.append(dict(caseId=row["caseId"], exchange=asdict(exchange) if exchange else None))
        value = dict(taskRef=dict(tenantId=context.principal.tenant_id, taskId=context.task["task_id"]),
            authorizationId=self.authorization_id, evaluationRef=self.evaluation_ref,
            cases=rows, providerExchanges=exchanges)
        self.private_output.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if self.private_output.exists():
            prior = json.loads(self.private_output.read_text(encoding="utf-8"))
            if (prior.get("taskRef") != value["taskRef"] or prior.get("evaluationRef") != self.evaluation_ref):
                raise ValueError("PRIVATE_EVALUATION_OUTPUT_CONFLICT")
            previous_rows = prior.get("cases", [])
            if previous_rows != rows[:len(previous_rows)]:
                raise ValueError("PRIVATE_EVALUATION_OUTPUT_CONFLICT")
            if len(previous_rows) == len(rows):
                return
            history = prior.get("observations", [])
        history.append(deepcopy(value))
        value["observations"] = history
        temporary = self.private_output.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.private_output)

    def run(self, context, parameters):
        self.validate_command(context.principal, context.task["command_key"])
        self.validate_scope(parameters, context.task["scope"])
        # Resolve and bound every case before making the first request.
        snapshots = set()
        for entry in self.entries:
            deterministic = self.backend._rules_result(entry, self.scope)
            if deterministic.snapshotRef in snapshots:
                raise ValueError("DUPLICATE_EVALUATION_LOGICAL_CALL")
            snapshots.add(deterministic.snapshotRef)
            binding = dict(taskRef=dict(tenantId=context.principal.tenant_id, taskId=context.task["task_id"]),
                planVersion=str(context.task["plan_version"]), snapshotId=deterministic.snapshotRef, participantId="s01")
            payload, _ = bundle_for_result(deterministic, binding).resolve_content()
            token_upper = sum(len(m["content"].encode()) for m in payload["messages"]) + 4096 + payload["parameters"]["maxOutputTokens"]
            if token_upper > 24000:
                raise ValueError("TOKEN_ALLOWANCE_TOO_SMALL")
            if self.provider:
                self.provider.preflight(payload, Decimal(".05"))
        rows, primary = [], None
        for case_id, entry in zip(self.case_ids, self.entries):
            context.check()
            result = self.backend.run(context, dict(packageRef=package_ref(entry["kind"], entry["payload"])))
            if primary is None:
                primary = result
            rows.append(self._compact(case_id, result))
            self._persist_private(context, rows)
            if result.analysisReport["ai"]["status"] != "AVAILABLE":
                break
        data = deepcopy(primary.dataReport)
        data["evaluationResults"] = rows
        analysis = deepcopy(primary.analysisReport)
        analysis["evaluation"] = self._summary(rows)
        return primary.model_copy(update={"dataReport": data, "analysisReport": analysis})

    def _validate_results(self, result, task_ref, plan_version):
        rows = result.dataReport["evaluationResults"]
        if not 1 <= len(rows) <= len(self.case_ids):
            raise ValueError("INVALID_EVALUATION_RESULTS")
        reconstructed = []
        for index, row in enumerate(rows):
            case_id, entry = self.case_ids[index], self.entries[index]
            expected = self.backend._rules_result(entry, result.scope)
            expected = expected.model_copy(update={"analysisReport": row["analysisReport"]})
            if row != self._compact(case_id, expected):
                raise ValueError("EVALUATION_CASE_BINDING_MISMATCH")
            self.backend.validate_publication(expected, task_ref, plan_version)
            if index < len(rows) - 1 and expected.analysisReport["ai"]["status"] != "AVAILABLE":
                raise ValueError("EVALUATION_CONTINUED_AFTER_FAILURE")
            reconstructed.append(expected)
        clean = deepcopy(result)
        clean.dataReport.pop("evaluationResults")
        summary = clean.analysisReport.pop("evaluation")
        if clean != reconstructed[0] or summary != self._summary(rows):
            raise ValueError("EVALUATION_PRIMARY_BINDING_MISMATCH")
        return clean

    def validate_publication(self, result, task_ref, plan_version):
        try:
            self._validate_results(result, task_ref, plan_version)
        except (KeyError, TypeError, IndexError, AttributeError):
            raise ValueError("INVALID_EVALUATION_RESULTS") from None

    def validate_report_parameters(self, report, parameters):
        self.validate(parameters)
        if report["analysisReport"]["evaluation"]["evaluationRef"] != self.evaluation_ref:
            raise ValueError("EVALUATION_REPORT_BINDING_MISMATCH")

    def model_receipts(self, report):
        return [row["analysisReport"]["ai"] for row in report["dataReport"]["evaluationResults"]
            if row["analysisReport"]["ai"]["status"] == "AVAILABLE"]

    def report_view(self, report):
        result = DomainResult.model_validate({key: report[key] for key in DomainResult.model_fields})
        clean = self._validate_results(result, report["taskRef"], report["planVersion"])
        view = self.backend.report_view(dict(report, dataReport=clean.dataReport, analysisReport=clean.analysisReport))
        view["analysisReport"]["evaluation"] = deepcopy(result.analysisReport["evaluation"])
        return view
