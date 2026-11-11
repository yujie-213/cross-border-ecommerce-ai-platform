"""只检查文档/入库完整性，不代表任何业务或企业接口验收。"""
import sys
sys.dont_write_bytecode=True
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
import re,json,hashlib,subprocess,xml.etree.ElementTree as ET
from collections import Counter
from task_io import ROOT,STATUSES,read_tasks,cycles
from render_status import expected
checks=[]
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def j(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def check(name,ok,detail):checks.append({'check':name,'result':'PASS' if ok else 'FAIL','detail':detail})
def main():
    required=['AGENTS.md','docs/PLAN.md','docs/PLAN.html','docs/TASKS.md','docs/HANDOFF.md','docs/DECISIONS.md','docs/COLLABORATION.md','docs/CI_RULES.md','docs/planning/git-whitelist.json','docs/planning/security-scan.json','docs/planning/repository-receipt.json']
    check('required-files',all((ROOT/p).is_file() for p in required),required)
    bs=j('docs/planning/baseline-manifest.json')
    check('immutable-design-baselines',all(h(ROOT/x['path'])==x['sha256'] for x in bs),[x['path'] for x in bs])
    ts=read_tasks();ix={t['id']:t for t in ts}
    check('unique-task-ids',len(ix)==len(ts),{'tasks':len(ts),'stages':dict(Counter(t['stage'] for t in ts))})
    bad=[(t['id'],d) for t in ts for d in t['dependsOn'] if d not in ix or d==t['id']]
    check('valid-acyclic-dependencies',not bad and not cycles(ts),{'invalid':bad,'cycles':cycles(ts)})
    fields=['id','stage','title','kind','dependsOn','entryCondition','ownerRole','assignee','allowedPaths','parallelCondition','deliverables','acceptance','plannedTests','risks','requiredEvidenceKinds','status','implementationCommits','testedCommit','evidence','review','branch','observedHead','dirtyPaths','latestHandoffRef','blocker','history']
    check('task-shape',all(all(f in t for f in fields) and t['status'] in STATUSES and t['acceptance'] and t['plannedTests'] and t['allowedPaths'] for t in ts),'字段/状态/验收/测试/文件范围')
    check('s01-design-no-code-or-s02-gate','D-S01-01' in ix and ix['D-S01-01']['dependsOn']==[],'S01设计不依赖A/B/C/S02')
    errors=[]
    for t in ts:
        if t['status']=='BLOCKED' and not t['blocker']:errors.append(t['id']+': missing blocker')
        if t['status']!='ACCEPTED':continue
        rv=t['review'] or {};ev=t['evidence'];commits=t['implementationCommits']
        if not commits or not all(re.fullmatch('[0-9a-f]{40}',c) for c in commits):errors.append(t['id']+': real commits required')
        if not t['testedCommit'] or not all(rv.get(k) for k in ['reviewer','reviewedCommit','evidenceRef']):errors.append(t['id']+': tested commit/review required')
        covered={a for e in ev if e.get('result')=='PASS' for a in e.get('acceptanceIds',[])}
        if not {a['id'] for a in t['acceptance']}<=covered:errors.append(t['id']+': acceptance coverage missing')
        if not set(t['requiredEvidenceKinds'])<={e.get('kind') for e in ev if e.get('result')=='PASS'}:errors.append(t['id']+': evidence kind missing')
        if any(not all(k in e for k in ['command','environment','sample','exitCode','result','artifactRef']) or e.get('result')!='PASS' or e.get('exitCode')!=0 for e in ev):errors.append(t['id']+': incomplete/failing evidence')
        for c in commits+([t['testedCommit']] if t['testedCommit'] else []):
            r=subprocess.run(['git','cat-file','-e',c+'^{commit}'],cwd=ROOT,capture_output=True)
            if r.returncode:errors.append(t['id']+': commit not found')
    check('acceptance-evidence-rules',not errors,errors or '无伪造验收；语义/环境/评审身份还须人工核验')
    check('generated-status-and-dependencies',all(p.read_text(encoding='utf-8')==text for p,text in expected(ts).items()),'从TASKS生成')
    ar=j('docs/archive/plan96-v0.1/archive-manifest.json')['files']
    check('exact-historical-archive',len(ar)==17 and all(h(ROOT/x['archivePath'])==x['sha256'] for x in ar),'17份旧管理文件字节不变')
    oldtext=(ROOT/'docs/archive/plan96-v0.1/docs/TASKS.md').read_text(encoding='utf-8')
    old=[json.loads(x) for x in re.findall(r'```json\s*\n(.*?)```',oldtext,re.S)];mapping=j('docs/planning/task-mapping.json')['rows'];m={x['oldId']:x for x in mapping}
    plan=(ROOT/'docs/PLAN.md').read_text(encoding='utf-8');regs=set(re.findall(r'REG-(?:S\d\d|ACTIONS|ADHOC)',plan))
    check('all-96-ids-history-mapped',len(old)==len(mapping)==len(m)==96 and all(t['id'] in m and t['status']==m[t['id']]['oldStatus'] and t['title']==m[t['id']]['oldTitle'] for t in old) and all(x in ix or x in regs for row in mapping for x in row['targets']),{'oldStates':dict(Counter(t['status'] for t in old)),'mappingIsNotAcceptance':True})
    page=(ROOT/'docs/PLAN.html').read_text(encoding='utf-8');build=j('docs/planning/plan-build.json');diag=ROOT/'docs/planning/diagrams';mmd=re.findall(r'```mermaid\s*\n(.*?)```',plan,re.S)
    check('plan-html-diagram-sync',h(ROOT/'docs/PLAN.md')==build['sourceSha256'] and h(ROOT/'docs/PLAN.html')==build['htmlSha256'] and build['sourceSha256'] in page and len(mmd)==1 and mmd[0].strip()+'\n'==(diag/'plan-flow.mmd').read_text(encoding='utf-8') and h(diag/'plan-flow.mmd')==build['diagramSourceSha256'] and h(diag/'plan-flow.svg')==build['diagramSvgSha256'] and (diag/'plan-flow.svg').read_text(encoding='utf-8') in page,build)
    ET.parse(diag/'plan-flow.svg');browser=j('docs/planning/browser-check.json')
    check('offline-browser-layout',browser['status']=='pass' and browser['htmlSha256']==h(ROOT/'docs/PLAN.html') and len(browser['checks'])==6 and not browser['remoteRequests'],'3宽度×深浅主题，无远程请求；SVG有效')
    check('preserved-milestone-mc-scope',all(f'| MC{i:02d} |' in plan for i in range(1,13)) and all(f'| M{i} |' in plan for i in range(5)) and 'S01调用链绝不填为此项PASS' in plan and '全部**未执行**' in plan,'原M0—M4/MC01—MC12保留；S01另立验收')
    agents=(ROOT/'AGENTS.md').read_text(encoding='utf-8')
    check('active-collaboration-consistency','工具与模型不绑定' in agents and 'TASKS是唯一任务状态' in agents and '缓存OFF' in agents and 'ADR-SEQ-001' in (ROOT/'docs/DECISIONS.md').read_text(encoding='utf-8'),'静态约束检查；语义仍须人工复核')
    forbidden=['src','pyproject.toml','alembic.ini','migrations','docker-compose.yml']
    management_only=all(t['status']=='TODO' for t in ts if t['kind']=='development')
    check('no-business-initialization',not management_only or not any((ROOT/p).exists() for p in forbidden),{'managementOnly':management_only,'paths':forbidden})
    security=j('docs/planning/security-scan.json');check('whitelist-secret-scan',security['status']=='PASS' and not security['findings'],'启发式秘密扫描，不保证识别所有敏感信息')
    wl=j('docs/planning/git-whitelist.json')['paths'];git=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True)
    if git.returncode==0:
        tracked=set(git.stdout.decode('utf-8').split('\0'))-{''};check('tracked-whitelist',tracked<=set(wl),{'tracked':len(tracked),'over':sorted(tracked-set(wl))})
    report={'scope':'DOCUMENTATION_AND_LOCAL_REPOSITORY_ONLY','businessTests':'NOT_RUN','checks':checks,'status':'PASS' if all(c['result']=='PASS' for c in checks) else 'FAIL'}
    (ROOT/'docs/planning/validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'checks':len(checks),'failed':[c['check'] for c in checks if c['result']=='FAIL']},ensure_ascii=False));return report['status']!='PASS'
if __name__=='__main__':raise SystemExit(main())
