"""第11步文档构建工具；只生成阅读材料，不含应用/业务实现。"""
from pathlib import Path
import csv
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
import markdown

ROOT = Path(__file__).resolve().parents[3]
import sys
sys.path.insert(0,str(ROOT/'docs/governance'))
from paths import root_links_to_relative,current_path
OUT = ROOT / 'docs/agents'
SOURCE = ROOT / 'docs/agents/AI_DETAILED_DESIGN.md'
HTML = SOURCE.with_suffix('.html')
NAMES = ['01-ai-foundation', '02-o01-handler-runtime', '03-prompt-context-harness',
         '04-agent-loop-tool-calling', '05-gateway-cache', '06-conditional-multi-agent',
         '07-llmops-evaluation-loop'] + [f'{n+7:02d}-s{n:02d}-workflow' for n in range(1, 11)] + ['18-pause-resume-protocol','19-s03-a02-voc-contract']
TITLES = ['AI公共底座', 'O01与Runtime边界', 'Prompt/Context/Harness', 'Agent Loop与工具',
          '模型网关与缓存', '条件性多角色协作', '可观测与评测闭环'] + [f'S{n:02d}业务时序' for n in range(1,11)] + ['暂停与恢复交接协议','S03/A02 VOC字段级用例']

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def segment(text, start, end=None):
    a = text.index(start)
    b = text.index(end, a + len(start)) if end else len(text)
    return text[a:b].strip() + '\n'

def table_csv(text, target):
    rows = []
    for line in text.splitlines():
        if line.startswith('|') and not re.match(r'^\|[\s:|-]+\|$', line):
            rows.append([re.sub(r'\*\*|`', '', x.strip()) for x in line.strip('|').split('|')])
        elif rows and rows[-1] != []:
            rows.append([])
    with target.open('w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(rows)

def prepare(text):
    blocks = re.findall(r'```mermaid\s*\n(.*?)```', text, flags=re.S)
    assert len(blocks) == len(NAMES) == 19, f'Expected 19 diagrams, got {len(blocks)}'
    diagrams = []
    for name, title, body in zip(NAMES, TITLES, blocks):
        path = OUT / 'mermaid' / (name + '.mmd')
        path.write_text(body.strip()+'\n', encoding='utf-8')
        diagrams.append({'id': name, 'title': title, 'source': f'mermaid/{name}.mmd', 'svg': f'mermaid/{name}.svg'})
    dump(OUT/'mermaid-manifest.json', diagrams)
    exports = {
        '技术与范式选型决策表': segment(text, '## 08 ', '## 09 '),
        'AI网关缓存准入与隔离矩阵': segment(text, '### 9.3 ', '## 10 '),
        'S01—S10_Agent与Workflow设计': segment(text, '## 14 ', '## 15 '),
        '待验证假设与实施门槛清单': segment(text, '## 16 ', '## 17 '),
        '核心接口与权限隔离设计表': segment(text, '## 03 ', '## 04 ') + '\n' +
            segment(text, '### 5.4 ', '## 06 ') + '\n' + segment(text, '### 9.1 ', '### 9.2 ') + '\n' + segment(text, '### 10.1 ', '### 10.2 ') + '\n' + segment(text, '### A.1 ', '### A.2 '),
        '暂停与恢复交接协议': segment(text, '### 3.3 ', '### 3.4 ') + '\n' + segment(text,'## 附录 B ','## 附录 C '),
        'S03_A02_VOC字段级契约示例': segment(text,'## 附录 C ')
    }
    for name, body in exports.items():
        (OUT/(name+'.md')).write_text(f'# {name}\n\n> 从[AI模块详细开发设计文档]({SOURCE.name}) v0.2自动摘编，唯一维护源为正文；状态和未验证项与正文一致。\n\n'+body, encoding='utf-8')
        table_csv(body, OUT/(name+'.csv'))
    rows = []
    for n in range(1,11):
        start = f'### 14.{n} '
        end = f'### 14.{n+1} ' if n < 10 else '## 15 '
        part = segment(text, start, end)
        data = {}
        for line in part.splitlines():
            cells = [x.strip() for x in line.strip('|').split('|')]
            if line.startswith('|') and len(cells)==2:
                data[cells[0]] = cells[1]
        rows.append({'场景': f'S{n:02d}', '阶段': 'P0' if n<=4 else ('P1' if n<=7 else 'P2'),
                     '必要性':data['Agent / 多Agent必要性'], '范式':data['范式与理由'],
                     '工具':data['只读工具清单'], '门槛':data['未验证及启用门槛']})
    with (OUT/'S01—S10_选型总览.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    (OUT/'assets/render.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>本次文档图示渲染</title><body></body></html>',encoding='utf-8')
    export_voc_fixtures(text)
    print(json.dumps({'phase':'prepare','diagrams':len(blocks),'exports':len(exports)},ensure_ascii=False))

def export_voc_fixtures(text):
    """仅展开文档内模拟数据，生成可审查JSON，不是业务ModelProvider实现。"""
    import copy
    target=OUT/'examples/s03-voc';target.mkdir(parents=True,exist_ok=True)
    samples={name:json.loads(body) for name,body in re.findall(r'样例标识：`([^`]+)`\s*```json\s*\n(.*?)```',text,re.S)}
    for name,value in samples.items():dump(target/(name+'.json'),value)
    a=segment(text,'### A.1 ','### A.2 ')
    request=json.loads(re.search(r'```json\s*\n(.*?)```',a,re.S)[1])
    def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for case in samples['voc-three-cases']['cases']:
        item=next(x for x in samples['voc-input-fixture']['items'] if x['caseId']==case['caseId'])
        suffix={'success':'success','technical-failure':'failure','semantic-unknown':'unknown'}[case['caseId']]
        req=copy.deepcopy(request)
        req.update(logicalCallId=case['logicalCallId'],attemptId=case['attemptId'],traceId=case['traceId'],parentSpanId='span-a02-'+suffix)
        req['taskRef']['taskId']=case['taskId'];req['contextBundleRef']['id']='context-voc-'+suffix;req['allowanceRef']['id']='allowance-voc-'+suffix+'-1'
        ctx={'tenantId':'tenant-fixture','id':req['contextBundleRef']['id'],'version':'1','purpose':'A02_VOC_CLASSIFICATION','snapshotId':req['snapshotId'],'taxonomyRef':samples['voc-input-fixture']['taxonomyRef'],'segments':[{'kind':'USER_FEEDBACK','controlTrust':'DATA','sensitivity':'PRIVATE_FEEDBACK','contentId':item['contentId'],'sourceRef':item['contentRef'],'sourceEvidenceId':item['sourceEvidenceId'],'language':item['language'],'text':item['text']}],'omissionReasons':[],'history':[],'memory':[]}
        messages=copy.deepcopy(samples['voc-resolved-messages']);messages[-1]['content']=json.dumps({'contentId':item['contentId'],'language':item['language'],'feedbackText':item['text']},ensure_ascii=False,separators=(',',':'))
        payload={'modelRevision':'model-fixture-rev-1','messages':messages,'parameters':{'temperature':0,'maxOutputTokens':128},'outputSchema':samples['voc-output-schema'],'toolSpecs':[]}
        control={k:copy.deepcopy(req[k]) for k in ['attemptId','logicalCallId','allowanceRef','deadline','taskRef','queryRef','planVersion','participantId','snapshotId','traceId','parentSpanId']}
        control.update(timeoutMs=20000,digests={'resolvedPromptDigest':digest(messages[:2]),'contextDigest':digest(ctx),'parametersDigest':digest(payload['parameters']),'outputSchemaDigest':digest(payload['outputSchema']),'toolSpecsDigest':digest([])})
        dump(target/(suffix+'-model-request.json'),req);dump(target/(suffix+'-context-bundle.json'),ctx);dump(target/(suffix+'-provider-request.json'),{'simulated':True,'payload':payload,'control':control})

CSS = '''
:root{color-scheme:light;--bg:#f3f5f8;--paper:#fff;--fg:#17283c;--muted:#53677e;--line:#dce3eb;--accent:#126b63;--soft:#edf6f4}
html[data-theme=dark]{color-scheme:dark;--bg:#111923;--paper:#182432;--fg:#e4edf6;--muted:#a1b4c9;--line:#33485f;--accent:#7cd8c8;--soft:#203b3c}
*{box-sizing:border-box}[hidden]{display:none!important}html{scroll-behavior:smooth;scroll-padding-top:80px}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.85 "Microsoft YaHei","Noto Sans CJK SC",sans-serif}a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{padding:26px 36px;background:#122b3a;color:#effaf7;border-bottom:4px solid #4aa794}header .meta{color:#b6cbd5;font-size:13px;letter-spacing:.04em}header h1{font-size:28px;line-height:1.5;max-width:1150px;margin:12px 0}header p{max-width:1100px;margin:12px 0;color:#d2e6e7}.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}.actions a,.actions button{background:#24475a;color:#effaf7;border:1px solid #4c7186;border-radius:6px;padding:7px 12px;font:14px inherit;cursor:pointer}
.layout{display:grid;grid-template-columns:252px minmax(0,1fr);max-width:1660px;margin:auto;gap:26px;padding:28px 30px}aside{position:sticky;top:16px;align-self:start;max-height:calc(100vh - 32px);overflow:auto;font-size:13px;padding-right:10px}aside label{font-weight:bold}aside input{width:100%;margin:8px 0 14px;padding:9px;border:1px solid var(--line);border-radius:5px;background:var(--paper);color:var(--fg)}aside a{display:block;padding:5px 7px;line-height:1.55;color:var(--muted)}aside a.sub{font-size:12px;padding-left:18px}main{min-width:0;background:var(--paper);padding:28px 34px 50px;border:1px solid var(--line);border-radius:10px;box-shadow:0 5px 24px #122b3a08}article h1{font-size:25px}h2{font-size:24px;padding-top:20px;margin-top:42px;border-top:1px solid var(--line);line-height:1.55}h3{font-size:19px;line-height:1.65;margin-top:28px}p,li,td{overflow-wrap:anywhere}blockquote{margin:16px 0;padding:12px 18px;background:var(--soft);border-left:4px solid var(--accent);color:var(--muted)}blockquote p{margin:6px 0}code{font:13px/1.6 Consolas,monospace;background:var(--soft);padding:2px 4px;border-radius:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--soft);padding:14px;border-radius:7px;font-size:13px}pre code{background:transparent;padding:0}
.table-scroll{overflow-x:auto;margin:18px 0;border:1px solid var(--line);border-radius:7px}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.75;min-width:650px}th{background:var(--soft);text-align:left;position:relative}th,td{padding:11px 12px;vertical-align:top;border-bottom:1px solid var(--line);border-right:1px solid var(--line)}tr:last-child td{border-bottom:0}td:first-child{font-weight:600;min-width:130px}figure{margin:24px 0;padding:16px;background:#fff;border:1px solid #d7e2ea;border-radius:8px;color:#17283c}.svg-viewport{overflow-x:auto}figure svg{display:block;width:100%;height:auto;max-width:none}figcaption{font-size:14px;font-weight:600;margin-top:12px;color:#1b554f}figcaption a{color:#126b63}details{font-size:13px;color:var(--muted);margin-top:12px}summary{cursor:pointer}footer{max-width:1500px;margin:12px auto 35px;padding:20px 32px;color:var(--muted);font-size:13px}.callout{border:1px solid var(--line);border-radius:6px;padding:14px;margin-bottom:20px;background:var(--soft)}
@media(max-width:1000px){.layout{grid-template-columns:1fr;padding:18px}aside{position:relative;max-height:300px;background:var(--paper);padding:14px;border-radius:6px}main{padding:22px}header{padding:24px}header h1{font-size:24px}}@media print{body{background:#fff;color:#000;font-size:10pt}header,.actions,aside,footer{display:none}.layout{display:block;padding:0}main{padding:0;border:0;box-shadow:none}h2,h3{break-after:avoid}figure{break-inside:avoid}.table-scroll{overflow:visible}table{min-width:0;font-size:9pt}details{display:none}}
'''

def publish(text):
    num = 0
    svg_checks=[]
    def replace(match):
        nonlocal num
        name,title=NAMES[num],TITLES[num];num+=1
        path=OUT/'mermaid'/(name+'.svg')
        svg=path.read_text(encoding='utf-8')
        el=ET.fromstring(svg)
        assert el.tag.endswith('svg')
        assert len(''.join(el.itertext()).strip())>10
        svg_checks.append({'id':name,'xml':'pass','bytes':path.stat().st_size})
        svg=re.sub(r'^<\?xml.*?\?>\s*','',svg,flags=re.S)
        code=html.escape(match.group(1).strip())
        readable = max(0, round(float(el.attrib.get('viewBox','0 0 0 0').split()[2]) * .85)) if num == 4 else 0
        inner=f'<div style="min-width:{readable}px">{svg}</div>' if readable else svg
        note='<p>本图按可读尺寸显示，可左右滚动；也可打开独立SVG缩放。</p>' if readable else ''
        return f'\n<figure id="figure-{num:02d}">{note}<div class="svg-viewport">{inner}</div><figcaption>图{num:02d} · {title}　<a href="docs/agents/mermaid/{name}.svg" target="_blank">打开SVG</a> · <a href="docs/agents/mermaid/{name}.mmd">Mermaid图源</a></figcaption><details><summary>查看图源</summary><pre><code>{code}</code></pre></details></figure>\n'
    body=re.sub(r'```mermaid\s*\n(.*?)```',replace,text,flags=re.S)
    body=markdown.markdown(body,extensions=['tables','fenced_code','sane_lists'])
    toc=[]; count=0
    def heading(m):
        nonlocal count
        count+=1
        level,content=m.group(1),m.group(2)
        anchor=f'section-{count}'
        label=re.sub('<[^>]+>','',content)
        toc.append(f'<a class="{"sub" if level=="3" else "top"}" href="#{anchor}">{label}</a>')
        return f'<h{level} id="{anchor}">{content}</h{level}>'
    body=re.sub(r'<h([23])>(.*?)</h\1>',heading,body,flags=re.S)
    body=re.sub(r'(<table>.*?</table>)',r'<div class="table-scroll">\1</div>',body,flags=re.S)
    page=f'''<!doctype html><html lang="zh-CN" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI模块详细开发设计 · 第11步</title><style>{CSS}</style></head><body>
<header><div class="meta">AIH-AI-LLD-001 · v0.2 · 2026-11-11 · 待独立审查</div><h1>跨境电商智慧中台<br>AI 模块详细开发设计</h1><p>以确定性 Workflow 为主，按需启用受限 Agent。复用 O01 / A01—A03 / B01—B02 / D01—D04 / G01—G02 / C01—C03，保留完整 S01—S10 规划与既有分期。</p><div class="actions"><a href="{SOURCE.name}">Markdown正文</a><a href="docs/agents/index.md">交付索引</a><a href="docs/architecture/interactive/architecture-ai-runtime-20261111-110000/ai-runtime.html">交互职责图</a><a href="docs/agents/本次新增及修改文件清单.md">文件清单</a><button id="theme">切换深浅主题</button><button onclick="window.print()">打印 / 保存PDF</button></div></header>
<div class="layout"><aside aria-label="文档目录"><label for="toc-search">章节目录 · 17章 / 19图</label><input id="toc-search" placeholder="筛选章节，例如：缓存、S03"><nav>{''.join(toc)}</nav></aside><main><div class="callout">仅完成第11步设计。首批 S02 最小代码基座保持无模型；本文没有执行模型效果、MC工程验收、企业联调或部署。</div><article>{body}</article></main></div>
<footer>正文是唯一维护源；HTML、摘编表与图源由本轮文档工具生成。图示为设计方案，非已实现系统；预算、模型、质量阈值与企业事实按正文门槛待冻结。</footer><script>document.getElementById('theme').onclick=()=>{{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark'}};document.getElementById('toc-search').oninput=e=>{{const q=e.target.value.toLowerCase();document.querySelectorAll('nav a').forEach(a=>a.hidden=!a.textContent.toLowerCase().includes(q))}};</script></body></html>'''
    page=root_links_to_relative(page,HTML)
    HTML.write_text(page,encoding='utf-8')
    dump(OUT/'review/svg-check.json',svg_checks)
    (OUT/'index.md').write_text(f'''# 第11步交付索引

状态：设计 v0.2（D01—D05修订），待独立审查；未进入应用代码开发。

- [HTML阅读版]({HTML.name})
- [Markdown正文]({SOURCE.name})
- [交互职责图](../architecture/interactive/architecture-ai-runtime-20261111-110000/ai-runtime.html)
- [技术与范式选型决策表](技术与范式选型决策表.md) / [CSV](技术与范式选型决策表.csv)
- [AI网关缓存准入与隔离矩阵](AI网关缓存准入与隔离矩阵.md) / [CSV](AI网关缓存准入与隔离矩阵.csv)
- [核心接口与权限隔离设计表](核心接口与权限隔离设计表.md)
- [S01—S10场景设计与时序](S01—S10_Agent与Workflow设计.md) / [选型总览CSV](S01—S10_选型总览.csv)
- [待验证假设与实施门槛](待验证假设与实施门槛清单.md)
- [D01—D05修订说明与剩余事项](D01—D05定点修订说明.md)
- [暂停与恢复协议](暂停与恢复交接协议.md)
- [S03/A02字段级示例](S03_A02_VOC字段级契约示例.md)
- [正文逐行差异](../archive/ai-review-d01-d05/AI模块详细设计_v0.1_to_v0.2.diff)
- [内部一致性复核](内部一致性检查记录.md)
- [实际文档验证结果](validation-report.json)
- [本次新增及修改文件清单](本次新增及修改文件清单.md)

## 独立图源与SVG

'''+ '\n'.join(f'- {title}：[Mermaid](mermaid/{name}.mmd) / [SVG](mermaid/{name}.svg)' for name,title in zip(NAMES,TITLES))+'\n',encoding='utf-8')
    print(json.dumps({'phase':'publish','html':str(HTML),'svg':num,'tables':body.count('<table>')},ensure_ascii=False))

if __name__ == '__main__':
    source=SOURCE.read_text(encoding='utf-8')
    if sys.argv[1]=='prepare': prepare(source)
    elif sys.argv[1]=='publish': publish(source)
    else: raise SystemExit('prepare | publish')
