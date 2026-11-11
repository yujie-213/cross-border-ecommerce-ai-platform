"""轻量规划文档校验；不初始化Git/应用、不运行模型或把任务改为ACCEPTED。"""
import sys
sys.dont_write_bytecode=True
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from datetime import datetime
from collections import Counter
import hashlib,json,re,subprocess
from task_io import ROOT,LEDGER,STATUSES,read_tasks,source_hash,cycles
from render_status import expected

OUT=ROOT/'docs/planning';REPORT=OUT/'validation-report.json';FILES=OUT/'FILES.md';MANIFEST=OUT/'file-manifest.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def git_read(args):
    try:return subprocess.run(['git',*args],cwd=ROOT,capture_output=True)
    except OSError:return None
def valid_time(value):
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).tzinfo is not None
    except Exception:return False

def manifest():
    for p in [FILES,MANIFEST]:
        if not p.exists():p.write_text('',encoding='utf-8')
    files=[ROOT/'AGENTS.md']+[p for p in (ROOT/'docs').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())
    text='# 本轮新增及修改文件清单\n\n本轮仅新增根AGENTS及docs内规划/协议/台账/只读派生视图/文档工具/检查材料。五份授权基线保持原样；未初始化Git或业务工程，未修改旧设计/图源/业务代码。\n\n'
    text+=f'新增文件 {len(files)} 个；修改既有项目文件0个。脚本仅做文档生成/检查，不是业务实现。以下自引用清单和manifest不计算自身hash。\n\n| 新增文件 | 用途 |\n|---|---|\n'
    for p in files:
        rel=p.relative_to(ROOT).as_posix();link='../../'+rel
        kind='开发规范草案' if p.name=='AGENTS.md' else ('只读派生视图' if p.parent.name=='generated' else ('文档工具/检查证据' if 'planning' in p.parts else '计划/台账/管理协议'))
        text+=f'| [{rel}]({link}) | {kind} |\n'
    FILES.write_text(text,encoding='utf-8')
    rows=[]
    for p in files:
        item={'path':p.relative_to(ROOT).as_posix(),'change':'added'}
        if p not in [FILES,MANIFEST]:item.update(bytes=p.stat().st_size,sha256=sha(p))
        else:item['hashOmittedReason']='self-referential listing/manifest'
        rows.append(item)
    write(MANIFEST,{'scope':'planning-documents-only','modifiedExistingFiles':[],'files':rows})
    return len(files)

def validate():
    if not REPORT.exists():write(REPORT,{'status':'RUNNING','scope':'planning documents only'})
    manifest();checks=[]
    def check(name,ok,detail=None):checks.append({'check':name,'status':'pass' if ok else 'fail','details':detail})
    required=['AGENTS.md','docs/PLAN.md','docs/TASKS.md','docs/HANDOFF.md','docs/DECISIONS.md','docs/COLLABORATION.md','docs/CI_RULES.md']
    check('所需管理文件存在',all((ROOT/p).is_file() for p in required))
    baseline=read(OUT/'baseline-manifest.json')
    comparisons=[{'path':x['path'],'unchanged':sha(ROOT/x['path'])==x['sha256']} for x in baseline]
    check('五份授权基线指纹未变',len(baseline)==5 and all(x['unchanged'] for x in comparisons),comparisons)
    ts=read_tasks();idx={t['id']:t for t in ts};ids=[t['id'] for t in ts]
    check('任务ID唯一且阶段一致',len(ids)==len(set(ids)) and all(re.fullmatch(r'M[0-4]-\d{3}',t['id']) and t['stage']==t['id'][:2] for t in ts))
    fields=['goal','priority','ownerRole','allowedPaths','entryConditions','parallelPolicy','deliverables','acceptance','plannedTests','requiredEvidenceKinds','risks','baselineRefs']
    check('每任务定义/范围/验收/测试/风险/依据完整',all(all(t.get(k) for k in fields) for t in ts))
    check('验收criterionId稳定唯一',len({a['id'] for t in ts for a in t['acceptance']})==sum(len(t['acceptance']) for t in ts) and all(a['id'].startswith(t['id']+'/AC') for t in ts for a in t['acceptance']))
    missing=[(t['id'],d) for t in ts for d in t['dependsOn'] if d not in idx]
    check('依赖存在且无环',not missing and not cycles(ts),{'missing':missing,'cycles':cycles(ts)})
    check('任务状态和优先级只用协议枚举',all(t['status'] in STATUSES and t['priority'] in ['HIGH','STANDARD','LOW'] for t in ts))
    bad=[]
    for t in ts:
        if t['status']=='IN_PROGRESS' and (not t['assignee'] or not re.fullmatch(r'[0-9a-f]{40}',t.get('baseCommit') or '')):bad.append((t['id'],'IN_PROGRESS missing assignee/baseCommit'))
        if t['status']=='BLOCKED' and (not isinstance(t['blocker'],dict) or not all(t['blocker'].get(k) for k in ['reason','ownerRole','resolutionCondition'])):bad.append((t['id'],'BLOCKED missing actual blocker'))
        if t['status']!='ACCEPTED':continue
        commit=t.get('testedCommit') or '';rv=t.get('review') or {};ev=t.get('evidence',[])
        if not re.fullmatch(r'[0-9a-f]{40}',commit) or not t['implementationCommits'] or commit not in t['implementationCommits']:bad.append((t['id'],'no real-shaped tested implementation commit'))
        if rv.get('decision')!='ACCEPT' or not all(rv.get(k) for k in ['reviewer','role','reviewedImplementationCommit','evidenceCommit','observedAt']) or rv.get('reviewedImplementationCommit')!=commit or rv.get('reviewer')==t.get('assignee'):bad.append((t['id'],'missing independent acceptance review'))
        if not valid_time(rv.get('observedAt','')):bad.append((t['id'],'invalid review time'))
        evidence_commit=rv.get('evidenceCommit','')
        for c in set(t['implementationCommits']+[commit,evidence_commit]):
            r=git_read(['cat-file','-e',c+'^{commit}']) if re.fullmatch(r'[0-9a-f]{40}',c or '') else None
            if r is None or r.returncode!=0:bad.append((t['id'],'commit does not exist: '+str(c)))
        ancestry=git_read(['merge-base','--is-ancestor',commit,evidence_commit]) if re.fullmatch(r'[0-9a-f]{40}',commit) and re.fullmatch(r'[0-9a-f]{40}',evidence_commit or '') else None
        if ancestry is None or ancestry.returncode!=0:bad.append((t['id'],'tested commit not ancestor of evidence commit'))
        if any(idx[d]['status']!='ACCEPTED' for d in t['dependsOn']):bad.append((t['id'],'dependency not ACCEPTED'))
        passed=[]
        for e in ev:
            required_e=['id','criterionIds','kind','testedCommit','environmentRef','sampleRef','artifactPath','sha256','observedAt']
            ok=all(e.get(k) for k in required_e) and e.get('result')=='PASS' and e.get('testedCommit')==commit
            ok=ok and ((bool(e.get('command')) and e.get('exitCode')==0) or (e.get('command') is None and bool(e.get('reviewerRef'))))
            if ok:
                try:ok=datetime.fromisoformat(e['observedAt'].replace('Z','+00:00')).tzinfo is not None
                except Exception:ok=False
            rel=e.get('artifactPath','');path=(ROOT/rel).resolve()
            if ok:
                ok=not Path(rel).is_absolute() and path.is_relative_to(ROOT.resolve())
                blob=git_read(['show',evidence_commit+':'+Path(rel).as_posix()]) if ok and re.fullmatch(r'[0-9a-f]{40}',evidence_commit or '') else None
                ok=bool(blob is not None and blob.returncode==0 and hashlib.sha256(blob.stdout).hexdigest()==e['sha256'])
            if ok:passed.append(e)
        covered={c for e in passed for c in e['criterionIds']};kinds={e['kind'] for e in passed}
        if not {a['id'] for a in t['acceptance']}<=covered or not set(t['requiredEvidenceKinds'])<=kinds:bad.append((t['id'],'criteria/evidence kinds not covered by valid PASS evidence'))
    check('状态事实与ACCEPTED基本证据约束',not bad,bad)
    check('基线引用仅使用五份授权别名',all(re.match(r'^(PRD|ARCH|FSR|HLD|AI)(?:§|\s|候选|附录)',b) for t in ts for b in t['baselineRefs']))
    stale=[p.relative_to(ROOT).as_posix() for p,text in expected(ts).items() if not p.exists() or p.read_text(encoding='utf-8')!=text]
    check('状态/依赖视图由唯一TASKS生成且无漂移',not stale,stale)
    check('A/B任务分组及最终MC验收责任存在',all(idx[f'M1-{n:03d}']['track']=='A' for n in range(1,11)) and all(idx[f'M1-{n:03d}']['track']=='B' for n in range(11,21)) and idx['M1-020']['dependsOn']==['M1-019'])
    plan=(ROOT/'docs/PLAN.md').read_text(encoding='utf-8')
    check('M0—M4及MC01—MC12逐项映射',all(f'| MC{n:02d} ' in plan for n in range(1,13)) and all(any(t['stage']==f'M{n}' for t in ts) for n in range(5)))
    alltext='\n'.join((ROOT/p).read_text(encoding='utf-8') for p in required)
    check('S01—S10和22候选需求覆盖',all(f'S{n:02d}' in plan for n in range(1,11)) and all(x in plan for x in ['1、6、7、8','2、9','10、11','12、13','18、19、20','21','22']))
    check('Git启动无ACCEPTED前置死锁',not idx['M0-002']['dependsOn'] and '独立审查' in ''.join(idx['M0-002']['entryConditions']) and 'M0-001' in idx['M0-010']['dependsOn'])
    check('S01设计准备与MVP实际门槛分开', 'M1-020' in idx['M2-001']['dependsOn'] and 'M1-036' in idx['M2-002']['dependsOn'])
    def ancestors(k):
        result=set()
        def walk(x):
            for d in idx[x]['dependsOn']:
                if d not in result:result.add(d);walk(d)
        walk(k);return result
    check('ERP与CRM逐动作门槛独立，不互相挂靠', 'M3-006' not in ancestors('M3-010') and 'M3-005' not in ancestors('M3-011') and {'M3-010','M3-011'}<=set(idx['M3-012']['dependsOn']))
    allowed={str((ROOT/x['path']).resolve()) for x in baseline};broken=[];outside=[]
    docs=[ROOT/p for p in required]+list((ROOT/'docs/generated').glob('*.md'))+[FILES]
    for doc in docs:
        for link in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            target=link.strip('<>').split('#',1)[0]
            if not target:continue
            if re.match(r'[a-zA-Z]+://',target):outside.append(target);continue
            p=(doc.parent/target).resolve()
            if not p.exists():broken.append({'doc':doc.relative_to(ROOT).as_posix(),'target':target})
            if not p.is_relative_to((ROOT/'docs').resolve()) and p!=ROOT/'AGENTS.md' and str(p) not in allowed:outside.append(str(p))
    check('本轮文档链接可定位且不关联未授权项目文件',not broken and not outside,{'broken':broken,'unauthorized':outside})
    try:r=subprocess.run(['git','rev-parse','--show-toplevel'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace');git_present=r.returncode==0
    except OSError:git_present=False
    if any(t['status']=='ACCEPTED' for t in ts):check('ACCEPTED必须有真实Git仓库',git_present)
    report={'document':'分阶段实施计划与AI协作协议 v0.1','date':'2026-11-11','status':'pass' if all(c['status']=='pass' for c in checks) else 'fail','tasks':len(ts),'byStage':dict(Counter(t['stage'] for t in ts)),'byStatus':dict(Counter(t['status'] for t in ts)),'taskLedgerSha256':source_hash(),'checks':checks,'gitRepositoryPresent':git_present,'notices':[] if git_present else ['当前不是Git仓库；工作区草案未提交，无开发验收SHA，本轮不建仓'],'scope':'规划文档/任务字段/DAG/源指纹/生成漂移与基本证据约束；未运行业务、MC、真实接口、模型、压测或部署','independentReview':'pending'}
    write(REPORT,report);count=manifest()
    print(json.dumps({'status':report['status'],'checks':len(checks),'tasks':len(ts),'newFiles':count,'failures':[c for c in checks if c['status']=='fail'],'gitRepositoryPresent':git_present},ensure_ascii=False))
    return report['status']=='pass'

if __name__=='__main__':raise SystemExit(0 if validate() else 1)
