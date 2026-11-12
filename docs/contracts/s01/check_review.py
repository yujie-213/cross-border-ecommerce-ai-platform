"""A-01 文档评审自检；不是业务校验器，不读.env内容，不联网或连接数据库。"""
import sys
sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import argparse
import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = "e9433ef5b433167ca6499778407c6bc6c80edf0d"
sys.path.insert(0, str(ROOT / "docs/planning"))
from task_io import cycles
from repository_audit import RULES


def git(*args):
    return subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=ROOT, capture_output=True)


def read_tasks(text):
    return {t["id"]: t for t in map(json.loads, re.findall(r"```json\s*(.*?)```", text, re.S))}


def utc(value):
    assert value.endswith("Z")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def model_errors(obj, controls):
    # Only selected documented invariants, not a complete ModelRequest Schema or authorization check.
    fields = set(EXAMPLES["modelRequest"])
    errors = set()
    if set(obj) != fields:
        errors.add("UNKNOWN_MODEL_FIELD")
    if set(obj["taskRef"]) != {"tenantId", "taskId"}:
        errors.add("TASK_REF_SHAPE")
    if obj["queryRef"] is not None:
        errors.add("S01_TASK_ONLY")
    tenant = obj["taskRef"]["tenantId"]
    if any(obj[k]["tenantId"] != tenant for k in ["principalRef", "contextBundleRef", "allowanceRef"]):
        errors.add("TENANT_MISMATCH")
    for value in obj.values():
        if isinstance(value, dict) and "version" in value and value["version"] in ["", "latest"]:
            errors.add("UNPINNED_REF")
    if obj["toolSpecRefs"]:
        errors.add("S01_TOOLS_FORBIDDEN")
    if utc(obj["deadline"]) > utc(controls["taskDeadline"]):
        errors.add("DEADLINE_OUTSIDE_TASK")
    if utc(obj["deadline"]) <= utc(controls["now"]):
        errors.add("DEADLINE_EXPIRED")
    return errors


def ai_structure_errors(obj):
    errors = set()
    if set(obj) != set(EXAMPLES["explanation"]):
        errors.add("AI_FIELDS")
    allowed_refs = list(EXAMPLES["refs"].values())
    for name in EXAMPLES["explanation"]:
        items = obj.get(name, [])
        minimum = 1 if name in ["recommendationReasons", "keyEvidence"] else 0
        if not minimum <= len(items) <= 8:
            errors.add("AI_ARRAY_BOUNDS")
        for item in items:
            if set(item) != {"text", "supportRefs"}:
                errors.add("AI_FIELDS")
            if not 1 <= len(item.get("text", "")) <= 500:
                errors.add("AI_TEXT_BOUNDS")
            refs = item.get("supportRefs", [])
            if not 1 <= len(refs) <= 8:
                errors.add("AI_ARRAY_BOUNDS")
            if any(ref not in allowed_refs for ref in refs):
                errors.add("AI_REF_NOT_ALLOWED")
    return errors


EXAMPLES = json.loads((HERE / "examples.json").read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", action="store_true", help="Write only docs/evidence/A-01/review-checks.json")
    args = parser.parse_args()
    checks = []

    def check(name, condition, detail):
        checks.append({"check": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    old = read_tasks(git("show", BASE + ":docs/TASKS.md").stdout.decode("utf-8"))
    current_text = (ROOT / "docs/TASKS.md").read_text(encoding="utf-8")
    current = read_tasks(current_text)
    check("same-task-ids-and-dependencies", len(current) == len(old) == 31 and set(current) == set(old)
          and all(t["dependsOn"] == old[k]["dependsOn"] for k, t in current.items()) and not cycles(list(current.values())),
          {"count": len(current), "cycles": cycles(list(current.values()))})
    stages = lambda text: re.findall(r"^\| [0-5] .*?$", text.replace("\r\n", "\n"), re.M)
    check("six-stage-table-preserved", stages(current_text) == stages(git("show", BASE + ":docs/TASKS.md").stdout.decode("utf-8"))
          and len(stages(current_text)) == 6, "Original stage rows unchanged")
    boundary_ids = ["A-04", "A-05", "B-05", "D-S01-DEV-01", "C-04"]
    text_fields = {"deliverables", "acceptance", "completionEvidence"}
    changed_fields = {k: sorted(f for f in set(current[k]) | set(old[k]) if current[k].get(f) != old[k].get(f)) for k in boundary_ids}
    check("boundary-edits-only-approved-fields", all(set(v) <= text_fields for v in changed_fields.values()), changed_fields)
    untouched = set(current) - set(boundary_ids) - {"A-01"}
    check("other-tasks-and-four-gates-preserved", all(current[k] == old[k] for k in untouched)
          and all(current[k]["enablementGates"] == old[k]["enablementGates"] for k in boundary_ids)
          and current["D-S01-01"]["status"] == "REVIEW" and current["D-S01-01"]["review"] is None,
          {"businessGateIds": [k for k in current if k.startswith("D-S01-") and current[k]["status"] == "BLOCKED"], "designReviewUnchanged": True})
    boundary_text = {k: json.dumps({f: current[k][f] for f in text_fields}, ensure_ascii=False) for k in boundary_ids}
    # Human-reviewed edge interpretation in the approved text; regex/phrases alone cannot prove arbitrary prose is acyclic.
    check("explicit-acceptance-boundary-separation", all([
        "不以真实Worker/数据/证据/报告发布实现作为本任务完成前置" in boundary_text["A-04"],
        "不以B-05报告发布完成作为本任务前置" in boundary_text["A-05"],
        "不以D-S01-DEV-01或C-04完成作为本任务前置" in boundary_text["B-05"],
        "不以C-04通过或D-S01-LIVE-01完成作为本任务工程交付前置" in boundary_text["D-S01-DEV-01"],
        "不要求D-S01-UI-01先完成" in boundary_text["C-04"],
    ]), "Author manually checks G01 ports -> Worker/conditional commit -> report -> Handler engineering -> real model evaluation; formal enablement gates retained")

    controls = EXAMPLES["fixtureControls"]
    check("positive-model-request-example", not model_errors(EXAMPLES["modelRequest"], controls), "Shape invariants only; fixture allowance NOT granted, no send permitted")
    check("positive-ai-output-example", not ai_structure_errors(EXAMPLES["explanation"]), "Only a hypothetical output example; not real model evidence")
    examples_ok = True
    for item in EXAMPLES["quantityExamples"]:
        if item["status"] == "KNOWN":
            examples_ok &= isinstance(item["value"], str) and Decimal(item["value"]).is_finite()
        else:
            examples_ok &= item["value"] is None and bool(item["reason"])
    check("known-zero-versus-unknown-and-not-applicable", examples_ok, "Explicit 0 / null+reason examples; no business calculation")
    timeout = min(int((utc(EXAMPLES["modelRequest"]["deadline"]) - utc(controls["now"])).total_seconds() * 1000), controls["providerTimeoutMs"])
    check("deadline-timeout-example", timeout == controls["expectedTimeoutMs"], {"fixtureTimeoutMs": timeout, "allowanceGranted": controls["allowanceGranted"]})
    case_results = []
    for case in EXAMPLES["negativeCases"]:
        obj = copy.deepcopy(EXAMPLES[case["base"]])
        target = obj
        for part in case["path"][:-1]:
            target = target[part]
        target[case["path"][-1]] = case.get("value", case.get("repeat", "") * case.get("count", 0))
        found = model_errors(obj, controls) if case["base"] == "modelRequest" else ai_structure_errors(obj)
        if case["expected"] == "HUMAN_GOLD_REJECT":
            passed = not found and controls["qualityGate"] == "BLOCKED"
            detail = "Structurally valid contradiction marked REJECT by authored gold example; semantic evaluation remains NOT_RUN"
        else:
            passed = case["expected"] in found
            detail = sorted(found)
        case_results.append({"id": case["id"], "result": "PASS" if passed else "FAIL", "observed": detail})
    check("negative-examples", all(x["result"] == "PASS" for x in case_results), case_results)

    broken = []
    for p in [HERE / "A-01-契约评审稿.md", ROOT / "docs/HANDOFF.md", ROOT / "docs/README.md"]:
        for raw in re.findall(r"\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
            if re.match(r"(?:https?://|#|mailto:)", raw):
                continue
            path = raw.split("#")[0]
            if path and not (p.parent / path).exists():
                broken.append(str(p.relative_to(ROOT)) + ":" + path)
    check("local-review-and-navigation-links", not broken, broken)
    env_ignored = git("check-ignore", "--quiet", ".env").returncode == 0
    env_tracked = git("ls-files", "--error-unmatch", ".env").returncode == 0
    check("local-env-excluded-without-reading-content", (ROOT / ".env").is_file() and env_ignored and not env_tracked,
          {"exists": (ROOT / ".env").is_file(), "ignored": env_ignored, "tracked": env_tracked, "contentsRead": False})
    paths = set(git("diff", "--name-only", BASE).stdout.decode("utf-8").splitlines())
    paths |= {"docs/contracts/s01/" + name for name in ["A-01-契约评审稿.md", "examples.json", "check_review.py"]}
    paths.add("docs/evidence/A-01/review-checks.json")
    paths.add("docs/evidence/A-01/environment-inspection.json")
    allowed_paths = {
        "docs/TASKS.md", "docs/HANDOFF.md", "docs/DECISIONS.md", "docs/README.md",
        "docs/generated/STATUS.md", "docs/generated/DEPENDENCIES.mmd",
        "docs/planning/git-whitelist.json", "docs/planning/validation-report.json",
        "docs/contracts/s01/A-01-契约评审稿.md", "docs/contracts/s01/examples.json",
        "docs/contracts/s01/check_review.py", "docs/evidence/A-01/review-checks.json",
        "docs/evidence/A-01/environment-inspection.json",
    }
    check("authorized-tracked-diff-scope", paths <= allowed_paths,
          {"outOfScope": sorted(paths - allowed_paths), "originalDesignAndPrototypeChanged": False if paths <= allowed_paths else "CHECK_REQUIRED"})
    findings = []
    for rel in sorted(paths):
        p = ROOT / rel
        if not p.is_file():
            continue
        content = p.read_text(encoding="utf-8")
        for name, rule in RULES.items():
            if re.search(rule, content):
                findings.append({"path": rel, "rule": name})
    check("changed-owned-documents-secret-heuristics", not findings, {"findings": findings, "envAndUnknownYamlRead": False})
    result = {
        "scope": "A01_REVIEW_DOCUMENTS_ONLY",
        "baseCommit": BASE,
        "observedHead": git("rev-parse", "HEAD").stdout.decode().strip(),
        "command": "python docs/contracts/s01/check_review.py --output",
        "environment": "Windows / existing documentation Python; no candidate dependencies installed",
        "checks": checks,
        "status": "PASS" if all(x["result"] == "PASS" for x in checks) else "FAIL",
        "realMysqlConnection": "NOT_RUN",
        "serverVersionCompatibility": "NOT_RUN",
        "candidatePackageCompatibility": "NOT_RUN",
        "realErpModelBrowserBusinessAcceptance": "NOT_RUN",
        "contractSignoff": "NOT_RUN",
        "databaseChanges": 0,
        "databaseAuthenticationRequestsThisTurn": 0,
        "reviewDocumentSha256": hashlib.sha256((HERE / "A-01-契约评审稿.md").read_bytes()).hexdigest(),
    }
    if args.output:
        output = ROOT / "docs/evidence/A-01/review-checks.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result["status"] != "PASS"


if __name__ == "__main__":
    raise SystemExit(main())
