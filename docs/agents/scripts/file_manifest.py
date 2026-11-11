"""只列出本次明确拥有的新增文档/图源/验证材料。"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/agents'
pre={x['path']:x for x in json.loads((ROOT/'docs/archive/ai-review-d01-d05/pre-revision-manifest.json').read_text(encoding='utf-8-sig'))}
SOURCE=ROOT/'docs/agents/AI_DETAILED_DESIGN.md'
listing=OUT/'本次新增及修改文件清单.md';manifest=OUT/'file-manifest.json'
for p in [listing,manifest]:
    if not p.exists():p.write_text('' if p==listing else '{}',encoding='utf-8')
files=[SOURCE,SOURCE.with_suffix('.html')]+[p for p in OUT.rglob('*') if p.is_file()]+[p for p in (ROOT/'docs/architecture/interactive/architecture-ai-runtime-20261111-110000').rglob('*') if p.is_file()]
files=sorted(set(p for p in files if '__pycache__' not in p.parts),key=lambda p:str(p.relative_to(ROOT)))
states={}
for p in files:
    rel=p.relative_to(ROOT).as_posix()
    states[rel]='added' if rel not in pre else ('modified' if p in [listing,manifest] or hashlib.sha256(p.read_bytes()).hexdigest()!=pre[rel]['sha256'] else 'unchanged')
body='# 本次新增及修改文件清单（D01—D05）\n\nv0.1→v0.2定点修订；概要开发设计v0.2及另外三份授权基线保持原字节，S01—S10默认选型及场景设计正文不变。脚本仅用于文档/模拟契约材料生成与检查，不是应用业务实现或工程初始化。\n\n'
body+=f"新增 {list(states.values()).count('added')}，修改 {list(states.values()).count('modified')}，原样保留 {list(states.values()).count('unchanged')} 个交付文件。全量SHA-256及分类见[file-manifest.json](file-manifest.json)；自身与清单不计算自引用hash。下表只列本轮新增/修改。\n\n| 变更 | 文件 |\n|---|---|\n"
for p in files:
    rel=p.relative_to(ROOT).as_posix();link=__import__('os').path.relpath(ROOT/rel,OUT).replace('\\','/')
    if states[rel]!='unchanged':body+=f"| {states[rel]} | [{rel}]({link}) |\n"
body+='\n本轮未修改其他历史项目或业务代码。未变的架构/选型与场景图不因重新构建阅读版而重绘，详见修订专项检查。\n'
listing.write_text(body,encoding='utf-8')
items=[]
for p in files:
    item={'path':p.relative_to(ROOT).as_posix(),'change':states[p.relative_to(ROOT).as_posix()],'bytes':p.stat().st_size}
    if p not in [listing,manifest]:item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    else:
        item['hashOmittedReason']='self-referential manifest/listing'
        if p==manifest:item.pop('bytes',None)
    items.append(item)
manifest.write_text(json.dumps({'document':'AIH-AI-LLD-001 v0.2','date':'2026-11-11','revision':'D01—D05','modifiedExistingFiles':[p for p,s in states.items() if s=='modified'],'addedFiles':[p for p,s in states.items() if s=='added'],'files':items},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'newFiles':list(states.values()).count('added'),'modifiedFiles':list(states.values()).count('modified'),'unchangedFiles':list(states.values()).count('unchanged')},ensure_ascii=False))
