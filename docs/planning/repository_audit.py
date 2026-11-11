"""只读Git审计、显式文档白名单和脱敏扫描；不init/add/commit/push。"""
import sys
sys.dont_write_bytecode=True
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'docs/planning'
def put(name,obj):(HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def load(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):
    r=subprocess.run(['git',*args],cwd=ROOT,capture_output=True)
    return r.returncode,r.stdout.decode('utf-8',errors='replace').strip()
def managed():
    files=[ROOT/'AGENTS.md',ROOT/'.gitignore']+list((ROOT/'docs').rglob('*'))
    return sorted(p for p in files if p.is_file() and 'local' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts and p.suffix!='.pyc')
def whitelist():
    baseline=[ROOT/x['path'] for x in load('baseline-manifest.json')]
    extra=[ROOT/'智慧中台AI应用项目_概要开发设计文档.html',ROOT/'智慧中台AI应用项目_AI模块详细开发设计文档.html',ROOT/'智慧中台AI应用项目_概要设计审查修订说明_H01-H07.md',ROOT/'智慧中台AI应用项目_最小代码基座交付与验收清单.md']
    attachments=[p for folder in ['design','ai-design'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    paths=sorted({p.relative_to(ROOT).as_posix() for p in baseline+extra+attachments+managed()})
    put('git-whitelist.json',{'authorization':'当前用户：仅本地Git；五份设计基线、两份直接工程设计附件/修订史、计划/管理/归档；无业务工程或其他历史项目','policy':'Exact paths; no git add .; non-whitelisted files remain untouched/untracked','paths':paths})
    return paths
def inventory():
    archive=json.loads((ROOT/'docs/archive/plan96-v0.1/archive-manifest.json').read_text(encoding='utf-8'))['files'];before={x['originalPath']:x['sha256'] for x in archive};rows=[]
    for p in managed():
        rel=p.relative_to(ROOT).as_posix();category='ARCHIVED' if rel.startswith('docs/archive/') else ('MODIFIED' if rel in before and digest(p)!=before[rel] else 'UNCHANGED' if rel in before else 'ADDED')
        rows.append({'path':rel,'change':category,'sha256':None if p.name in ['file-manifest.json','FILES.md'] else digest(p)})
    put('file-manifest.json',{'scope':'本轮管理文件变化；基线/既有设计附件只入库不改','selfHashExcluded':['docs/planning/file-manifest.json','docs/planning/FILES.md'],'files':rows})
    counts={k:sum(x['change']==k for x in rows) for k in ['ADDED','MODIFIED','ARCHIVED','UNCHANGED']}
    text='# 本轮交付与文件变化\n\n由repository_audit.py生成。只改管理/计划文档及文档工具；五份基线未改，未建业务工程。旧17份文件字节保全，96项任务/评审状态逐ID可追。实际提交及剩余未跟踪见[仓库回执](repository-receipt.json)。\n\n'
    text+='管理范围数量：'+json.dumps(counts,ensure_ascii=False)+'。ARCHIVED包括17份原稿、说明与指纹清单。白名单内既有设计/图表/修订史只读入库，不计本轮新增设计。\n\n| 路径 | 变化 |\n|---|---|\n'
    for x in rows:text+=f"| [{x['path']}](../../{x['path']}) | {x['change']} |\n"
    text+='\n文件hash见file-manifest.json，自引用文件不计算自身hash。旧基线可选链接指向architecture/feasibility/.archify的材料可能未入库；原工作区文件保留。PLAN.html图示自包含。文档脚本不是业务实现。\n'
    (HERE/'FILES.md').write_text(text,encoding='utf-8');return counts
RULES={
 'PRIVATE_KEY':r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
 'OPENAI_STYLE_KEY':r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}',
 'GITHUB_TOKEN':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
 'AWS_ACCESS_KEY':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
 'SLACK_TOKEN':r'\bxox[baprs]-[A-Za-z0-9-]{20,}',
 'CREDENTIAL_URL':r'(?:mysql|postgres(?:ql)?|https?)://[^\s/:<>]+:[^\s/@<>]{6,}@',
 'LITERAL_SECRET':r'''(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*["']?\s*[:=]\s*["'][A-Za-z0-9+/=_-]{20,}["']'''
}
def scan(staged=False):
    paths=load('git-whitelist.json')['paths'];findings=[];count=0
    for rel in paths:
        p=ROOT/rel
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(ROOT.resolve()):findings.append({'path':rel,'rule':'MISSING_OR_UNSAFE_PATH'});continue
        if staged:
            r=subprocess.run(['git','show',':'+rel],cwd=ROOT,capture_output=True)
            if r.returncode:findings.append({'path':rel,'rule':'NOT_STAGED'});continue
            data=r.stdout
        else:data=p.read_bytes()
        count+=1
        if b'\0' in data[:8192]:continue
        try:text=data.decode('utf-8-sig')
        except UnicodeDecodeError:continue
        for name,pattern in RULES.items():
            for match in re.finditer(pattern,text):findings.append({'path':rel,'line':text.count('\n',0,match.start())+1,'rule':name,'value':'REDACTED'})
    sensitive=[]
    for p in ROOT.rglob('*'):
        if '.git' in p.parts or not p.is_file():continue
        if re.match(r'(?i)(\.env(?:\..*)?|credentials.*|id_rsa.*|.*\.(?:pem|key|p12|pfx))$',p.name) and p.name not in ['.env.example','.env.template']:sensitive.append(p.relative_to(ROOT).as_posix())
    report={'status':'PASS' if not findings and not sensitive else 'FAIL','mode':'STAGED_BLOBS' if staged else 'WHITELIST_WORKTREE','scannedFiles':count,'findings':findings,'sensitiveNamesAcrossWorkspace':sensitive,'limitations':'启发式模式/文件名检查，不保证全部秘密/个人信息均可识别；白名单均获准设计/管理材料，无真实ERP数据。'}
    if not staged:put('security-scan.json',report)
    print(json.dumps(report,ensure_ascii=False));return bool(findings or sensitive)
def audit():
    code,head=git('rev-parse','HEAD');_,branch=git('branch','--show-current');_,tracked=git('ls-files','-z');paths=set(tracked.split('\0'))-{''};allowed=set(load('git-whitelist.json')['paths']);_,remote=git('remote');_,dirty=git('diff','--name-only');_,staged=git('diff','--cached','--name-only');_,untracked=git('ls-files','--others','--exclude-standard','-z');bloberrors=[]
    for x in load('baseline-manifest.json'):
        r=subprocess.run(['git','show','HEAD:'+x['path']],cwd=ROOT,capture_output=True)
        if r.returncode or hashlib.sha256(r.stdout).hexdigest()!=x['sha256']:bloberrors.append(x['path'])
    result={'status':'PASS' if not code and not(paths-allowed) and not remote and not dirty and not staged and not bloberrors else 'FAIL','head':head,'branch':branch,'trackedCount':len(paths),'overWhitelist':sorted(paths-allowed),'remotes':remote.splitlines(),'trackedDirty':dirty.splitlines(),'stagedChanges':staged.splitlines(),'baselineBlobErrors':bloberrors,'untracked':sorted(set(untracked.split('\0'))-{''})}
    print(json.dumps(result,ensure_ascii=False,indent=2));return result['status']!='PASS'
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','scan','staged','final']);x=a.parse_args()
    if x.action=='prepare':whitelist();print(json.dumps(inventory()));whitelist()
    elif x.action=='scan':raise SystemExit(scan())
    elif x.action=='staged':raise SystemExit(scan(True))
    else:raise SystemExit(audit())
