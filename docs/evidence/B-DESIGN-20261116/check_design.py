"""B design-only consistency checks; never connects to ERP, models or a database."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'docs/planning'))
from task_io import read_tasks, cycles

paths = ['docs/architecture/B_AFTER_SALES_REUSE.md',
         'docs/agents/B_AFTER_SALES_DESIGN.md',
         'docs/ui/B_AFTER_SALES_PRODUCT.md',
         'docs/planning/B_AFTER_SALES_PLAN.md']
texts = {p: (ROOT / p).read_text(encoding='utf-8') for p in paths}
reqpath = 'docs/requirements/B_AFTER_SALES_V1.md'
req = (ROOT / reqpath).read_bytes()
baseline = subprocess.check_output(['git', 'show', '2547d1e:' + reqpath], cwd=ROOT)
plan = texts[paths[3]]
checks = []

def check(name, ok, detail):
    checks.append(dict(check=name, result='PASS' if ok else 'FAIL', detail=detail))

check('frozen-requirements-unchanged', req == baseline, hashlib.sha256(req).hexdigest())
ids = sorted(set(re.findall(r'B-(?:SCP|DATA|CASE|STAT|POL|RISK|ISO|EXP|FAIL|SEC|CHG)-\d+', req.decode())))
missing = [i for i in ids if '| ' + i + ' |' not in plan]
check('all-frozen-requirement-ids-mapped', not missing, dict(count=len(ids), missing=missing))
acs = ['AC-%02d-%s' % (n, suffix) for n in (1, 2, 3) for suffix in ['P', 'N1', 'N2', 'N3', 'N4', 'N5']]
check('18-acceptance-cases-mapped', all('| ' + i + ' |' in plan for i in acs), acs)
missing_links = []
for path, text in texts.items():
    for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', text):
        if not link.startswith(('http:', 'https:')) and not (ROOT / path).parent.joinpath(link).exists():
            missing_links.append([path, link])
check('local-document-links', not missing_links, missing_links)
reuse = texts[paths[0]]
codepaths = re.findall(r'`([^`]+)`', reuse)
missing_code = []
for p in codepaths:
    if '/' not in p or not p.endswith(('.py', '.vue', '.ts', '.cmd', '.md')):
        continue
    if not (ROOT / p).exists() and not (ROOT / 'src/commerce_hub' / p).exists():
        missing_code.append(p)
check('reuse-cited-file-paths-exist', not missing_code, missing_code)
tasks = read_tasks()
new = [t for t in tasks if t['id'].startswith('D-B-')]
allids = {t['id'] for t in tasks}
required = ['stage','kind','dependsOn','entryCondition','ownerRole','assignee','allowedPaths','parallelCondition','deliverables','acceptance','plannedTests','risks','requiredEvidenceKinds','status','implementationCommits','testedCommit','evidence','review','branch','observedHead','dirtyPaths','latestHandoffRef','blocker','history']
check('nine-tasks-and-shape', len(new) == 9 and all(all(k in t for k in required) for t in new), [t['id'] for t in new])
check('dag-valid', not cycles(tasks) and all(d in allids for t in tasks for d in t['dependsOn']), cycles(tasks))
check('design-review-development-not-started', all(t['status'] == ('REVIEW' if t['id'] == 'D-B-DESIGN-01' else 'TODO') and t['review'] is None and not t['implementationCommits'] for t in new), 'No implementation or business acceptance claimed')
by_id = {t['id']: t for t in new}
check('case-does-not-wait-for-complete-dataset', by_id['D-B-CASE-01']['dependsOn'] == ['D-B-FOUNDATION-01', 'D-B-PROTOTYPE-01'] and by_id['D-B-EXPERIENCE-01']['dependsOn'] == ['D-B-DATASET-01', 'D-B-PROTOTYPE-01'] and by_id['D-B-DATASET-01']['dependsOn'] == ['D-B-FOUNDATION-01'], 'CASE and DATASET branch after minimal foundation; complete dataset remains mandatory')
design = texts[paths[1]]
check('g01-admin-revision-design', all(x in design for x in ['g01_b_resource_grants','authorize_b_resource','taskAuthorization','grant-after-sales','不写password_hash','重跑旧配置复活','engineering:execute','每项1—100条非空']), 'Reviewed service.py, local.py, tables.py and O01 hard-coded authorization calls; implementation NOT_RUN')
check('prototype-before-vue-and-four-paths', 'D-B-PROTOTYPE-01' in plan and all(x in texts[paths[2]] for x in ['prototypes/b-after-sales/index.html','正式Vue','售后工作台','案件处理','体验分析','补货风险展示']), 'Prototype planned TODO; no prototype or Vue implementation this round')
check('tables-and-contracts-by-first-consumer', all('| '+x+' |' in design for x in ['PROTOTYPE','FOUNDATION','CASE','DATASET','EXPERIENCE','RISK','S01']), 'Section 7.1 postpones unused capabilities without dropping final constraints')
check('mermaid-fences-balanced', all(t.count('```') % 2 == 0 for t in texts.values()), 'Source syntax only; visual rendering NOT_RUN')
combined = '\n'.join(texts.values())
check('essential-design-boundaries-present', all(x in combined for x in ['QualityRiskReadPort', 'UNKNOWN', '1024', '30×24', '20', '10个百分点', '独立回读', '不进入', 'Idempotency-Key', '教师答案']), 'Static markers plus manual semantic review; not business verification')
changed = subprocess.check_output(['git','diff','--name-only','2547d1e'], cwd=ROOT, text=True).splitlines()
check('tracked-change-documentation-only', all(p.startswith('docs/') for p in changed), changed)
report = dict(date='2026-11-16', baseline='2547d1e23ef8cbc991a6e238df9961c35a551696',
              scope='DESIGN_DOCUMENTATION_ONLY', businessTests='NOT_RUN', erpCalls=0, modelCalls=0,
              migrationExecution='NOT_RUN', mermaidRendering='NOT_RUN',
              checks=checks, status='PASS' if all(c['result']=='PASS' for c in checks) else 'FAIL')
(Path(__file__).parent / 'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(status=report['status'], checks=len(checks), failed=[c['check'] for c in checks if c['result']=='FAIL']),ensure_ascii=False))
raise SystemExit(report['status'] != 'PASS')
