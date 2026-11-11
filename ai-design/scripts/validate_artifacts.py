"""文档结构、引用、源同步与基线指纹验证，不执行应用/模型测试。"""
from pathlib import Path
import hashlib,json,re,sys,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'ai-design'
SOURCE=ROOT/'智慧中台AI应用项目_AI模块详细开发设计文档.md'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
text=SOURCE.read_text(encoding='utf-8'); checks=[]
def check(name, passed, details=None): checks.append({'check':name,'status':'pass' if passed else 'fail','details':details})
baseline=read(OUT/'baseline-manifest.json')
compare=[{'path':x['path'],'unchanged':sha(ROOT/x['path'])==x['sha256']} for x in baseline]
check('四份授权基线指纹未变',all(x['unchanged'] for x in compare),compare)
check('直接工程基线版本及统一上下文', 'v0.2' in text and 'AnalysisContext.schemaVersion=0.2' in text)
check('ER01—ER10逐项对应',all(f'| ER{i:02d}' in text for i in range(1,11)))
check('MC01—MC12逐项对应',all(f'| MC{i:02d}' in text for i in range(1,13)))
check('M0—M4分期覆盖',all(f'| M{i} ' in text for i in range(5)))
fields=['目标 / 输入输出','Agent / 多Agent必要性','范式与理由','规则 / SQL / B / A职责','真正LLM步骤','State / Context','只读工具清单','权限 / 预算','失败 / 降级 / 人工 / 终止','O01及跨场景协作','观测 / 验收','未验证及启用门槛']
scenario=[]
for i in range(1,11):
    start=text.index(f'### 14.{i} '); end=text.index(f'### 14.{i+1} ',start) if i<10 else text.index('## 15 ',start)
    part=text[start:end]; missing=[f for f in fields if f'| {f} |' not in part]
    scenario.append({'scenario':f'S{i:02d}','missing':missing,'sequenceDiagrams':part.count('```mermaid')})
check('十场景全部设计项及独立时序',all(not x['missing'] and x['sequenceDiagrams']==1 for x in scenario),scenario)
blocks=re.findall(r'```mermaid\s*\n(.*?)```',text,re.S);manifest=read(OUT/'mermaid-manifest.json')
check('19份独立图源与正文同步',len(blocks)==len(manifest)==19 and all((OUT/x['source']).read_text(encoding='utf-8').strip()==b.strip() for x,b in zip(manifest,blocks)))
xml=[]
for d in manifest:
    p=OUT/d['svg']
    try:
        el=ET.parse(p).getroot();xml.append(el.tag.endswith('svg') and p.stat().st_size>1000)
    except Exception: xml.append(False)
check('19份SVG XML完整',len(xml)==19 and all(xml))
check('真实Mermaid渲染通过',read(OUT/'review/mermaid-render-check.json')['status']=='pass')
body=SOURCE.with_suffix('.html').read_text(encoding='utf-8')
check('HTML内嵌全部19张SVG',len(re.findall(r'<figure id="figure-',body))==19 and len(re.findall(r'<svg[\s>]',body))==19)
check('HTML无远程script或stylesheet运行依赖',not re.search(r'<(?:script|link)\b[^>]*(?:src|href)=["\']https?://',body,re.I))
allowed={str((ROOT/x['path']).resolve()) for x in baseline};allowed.add(str(SOURCE.resolve()));allowed.add(str(SOURCE.with_suffix('.html').resolve()))
refs=[]; violations=[];missing=[]
docs=[SOURCE]+list(OUT.glob('*.md'))
for doc in docs:
    for raw in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
        raw=raw.strip('<>');target=raw.split('#',1)[0]
        if not target:continue
        if re.match(r'[a-zA-Z]+://',target):violations.append({'doc':str(doc.relative_to(ROOT)),'target':target});continue
        p=(doc.parent/target).resolve();refs.append(str(p))
        is_new=p.is_relative_to(OUT.resolve()) or p.is_relative_to((ROOT/'.archify/architecture-ai-runtime-20261111-110000').resolve())
        if str(p) not in allowed and not is_new:violations.append({'doc':str(doc.relative_to(ROOT)),'target':target})
        if not p.exists():missing.append(str(p))
check('引用仅限四份基线与本次产物',not violations,violations)
check('全部文档本地链接可定位',not missing,missing)
json_samples=re.findall(r'```json\s*\n(.*?)```',text,re.S)
valid_json=True
for sample in json_samples:
    try:json.loads(sample)
    except Exception:valid_json=False
check('接口JSON示例可解析',bool(json_samples) and valid_json)
check('16个AI控制验收样例',all(f'| AI-AC{i:02d} ' in text for i in range(1,17)))
browser=read(OUT/'review/browser-check.json')
check('HTML浏览器多视口深浅主题及离线检查',browser['status']=='pass' and browser['sha256']==sha(SOURCE.with_suffix('.html')),browser['interactions'])
arch=read(ROOT/'.archify/architecture-ai-runtime-20261111-110000/ai-runtime.finalize-summary.json')
check('Archify职责图完整交付门禁',arch.get('ok') is True and all(arch['gates'].get(k)=='pass' for k in ['validate','deliver','check','browser-check']))
check('D01—D05专项文档自检',read(OUT/'review-d01-d05/revision-check.json')['status']=='pass' and read(OUT/'review-d01-d05/revision-check.json')['sourceSha256']==sha(SOURCE))
report={'document':'AIH-AI-LLD-001 v0.2','date':'2026-11-11','status':'pass' if all(x['status']=='pass' for x in checks) else 'fail','sourceSha256':sha(SOURCE),'checks':checks,'verificationScope':'文档结构、引用、基线指纹、图示和静态阅读材料；无业务实现/MC验收/模型效果/企业联调/压测/部署','semanticReviewRef':'内部一致性检查记录.md','independentReview':'pending'}
(OUT/'validation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'checks':len(checks),'failures':[x for x in checks if x['status']=='fail']},ensure_ascii=False))
sys.exit(0 if report['status']=='pass' else 1)
