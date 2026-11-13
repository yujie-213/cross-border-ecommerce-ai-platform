"""文档构建：MD是唯一正文，HTML内嵌同源SVG；不是业务工程。"""
import sys
sys.dont_write_bytecode=True
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
import re,hashlib,html,json,argparse
import markdown
from task_io import ROOT,read_tasks
from render_status import expected

SOURCE=ROOT/'docs/PLAN.md';OUT=SOURCE.with_suffix('.html');DIAG=ROOT/'docs/planning/diagrams'
def sha(b):return hashlib.sha256(b).hexdigest()
CSS='''
:root{--bg:#f3f5f7;--paper:#fff;--fg:#172a3b;--muted:#566c7e;--line:#d9e2e9;--accent:#126d63;--soft:#edf6f3}
html[data-theme=dark]{--bg:#111b26;--paper:#1a2938;--fg:#e7f0f7;--muted:#b2c6d7;--line:#374f63;--accent:#7cd7c7;--soft:#24403f}
*{box-sizing:border-box}[hidden]{display:none!important}html{scroll-padding-top:28px}body{margin:0;font:16px/1.85 "Microsoft YaHei",sans-serif;color:var(--fg);background:var(--bg)}a{color:var(--accent)}header{background:#122e3c;color:#effaf8;padding:30px 38px;border-bottom:4px solid #469f92}header h1{font-size:29px;margin:8px 0}header p{margin:8px 0;color:#c8dde2}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.actions a,.actions button{font:14px sans-serif;padding:9px 13px;border:1px solid #58778b;background:#26475b;color:#effaf8;border-radius:6px;text-decoration:none;cursor:pointer}.layout{display:grid;grid-template-columns:245px minmax(0,1fr);gap:25px;max-width:1660px;margin:auto;padding:28px}aside{position:sticky;top:16px;align-self:start;max-height:calc(100vh - 32px);overflow:auto;font-size:14px}aside a{display:block;padding:7px 8px;text-decoration:none;color:var(--muted)}main{min-width:0;background:var(--paper);padding:30px 36px;border:1px solid var(--line);border-radius:10px}h2{font-size:23px;margin-top:40px;border-top:1px solid var(--line);padding-top:25px}p,td,li{overflow-wrap:anywhere}blockquote{margin:20px 0;padding:10px 20px;background:var(--soft);border-left:4px solid var(--accent)}.table-scroll{overflow-x:auto;border:1px solid var(--line);border-radius:6px;margin:20px 0}table{border-collapse:collapse;width:100%;min-width:680px;font-size:14px;line-height:1.8}td,th{padding:11px 12px;vertical-align:top;text-align:left;border-right:1px solid var(--line);border-bottom:1px solid var(--line)}th{background:var(--soft)}code{font:13px/1.7 Consolas,monospace;background:var(--soft);padding:2px 4px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--soft);padding:15px;border-radius:6px}figure{margin:22px 0;background:#fff;color:#172a3b;padding:16px;border:1px solid #d9e2e9;border-radius:7px}figure svg{display:block;width:100%;height:auto}figcaption{font-size:14px;color:#185950;margin-top:12px}summary{cursor:pointer}.callout{padding:15px;background:var(--soft);border:1px solid var(--line);border-radius:6px}footer{margin:24px auto;max-width:1500px;padding:18px;color:var(--muted);font-size:13px}
@media(max-width:1000px){.layout{grid-template-columns:1fr;padding:16px}aside{position:relative;max-height:280px;background:var(--paper);padding:12px}main{padding:20px}header{padding:24px}header h1{font-size:24px}}@media print{header,aside,footer,.actions{display:none}.layout{display:block;padding:0}main{border:0;padding:0}body{background:white;color:black;font-size:10pt}h2{break-after:avoid}.table-scroll{overflow:visible}table{min-width:0;font-size:9pt}details{display:none}}
'''
def prepare():
    text=SOURCE.read_text(encoding='utf-8');blocks=re.findall(r'```mermaid\s*\n(.*?)```',text,re.S)
    assert len(blocks)==1
    DIAG.mkdir(parents=True,exist_ok=True);(DIAG/'plan-flow.mmd').write_text(blocks[0].strip()+'\n',encoding='utf-8')
    for p,t in expected(read_tasks()).items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
def publish():
    text=SOURCE.read_text(encoding='utf-8');mmd=(DIAG/'plan-flow.mmd').read_bytes();svg=(DIAG/'plan-flow.svg').read_text(encoding='utf-8');receipt=json.loads((DIAG/'render-receipt.json').read_text(encoding='utf-8'))
    assert receipt['sourceSha256']==sha(mmd) and receipt['svgSha256']==sha(svg.encode()),'Diagram stale; rerender source with approved Mermaid runtime'
    body=re.sub(r'```mermaid\s*\n(.*?)```',lambda m:'\n<figure>'+svg+'<figcaption>阶段流程（来自本MD图源） · <a href="planning/diagrams/plan-flow.svg">打开SVG</a></figcaption><details><summary>Mermaid图源</summary><pre>'+html.escape(m.group(1))+'</pre></details></figure>\n',text,flags=re.S)
    body=markdown.markdown(body,extensions=['tables','fenced_code','sane_lists']);toc=[];n=0
    def heading(m):
        nonlocal n
        n+=1;label=re.sub('<[^>]+>','',m[2]);anchor='section-'+str(n);toc.append(f'<a href="#{anchor}">{label}</a>');return f'<h{m[1]} id="{anchor}">{m[2]}</h{m[1]}>'
    body=re.sub(r'<h([23])>(.*?)</h\1>',heading,body,flags=re.S);body=re.sub(r'(<table>.*?</table>)',r'<div class="table-scroll">\1</div>',body,flags=re.S)
    source_hash=sha(SOURCE.read_bytes())
    page=f'''<!doctype html><html lang="zh-CN" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="plan-source-sha256" content="{source_hash}"><title>S01先行 · 代码底座与通用AI计划</title><style>{CSS}</style></head><body><header><p>A—D增量计划 · S01纵向切片 · 最新状态见TASKS</p><h1>先完成所需底座，再按使用方补齐能力</h1><p>A 最小工程 · B 必要公共能力 · C 按需AI · D 逐场景专项</p><div class="actions"><a href="PLAN.md">Markdown正文</a><a href="TASKS.md">唯一任务台账</a><a href="HANDOFF.md">交接入口</a><a href="TASK_MAPPING.md">旧96项映射</a><button id="theme">切换深浅主题</button><button onclick="print()">打印</button></div></header><div class="layout"><aside aria-label="章节目录">{''.join(toc)}</aside><main><div class="callout">当前本地教学运行入口与首次配置见README；任务状态和验收范围以TASKS为准。原M0—M4/MC验收独立保留，不以S01测试替代。</div><article>{body}</article></main></div><footer>唯一正文为PLAN.md；HTML与SVG是派生阅读材料。原M0—M4、MC01—MC12保留，S01另立验收。</footer><script>document.getElementById('theme').onclick=()=>{{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark'}};</script></body></html>'''
    OUT.write_text(page,encoding='utf-8')
    (ROOT/'docs/planning/plan-build.json').write_text(json.dumps({'source':'docs/PLAN.md','sourceSha256':source_hash,'html':'docs/PLAN.html','htmlSha256':sha(OUT.read_bytes()),'diagramSourceSha256':sha(mmd),'diagramSvgSha256':sha(svg.encode()),'tables':body.count('<table>'),'sections':len(toc)},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');a=p.parse_args();prepare()
    if not a.prepare:publish()
    print(json.dumps({'prepared':True,'published':not a.prepare},ensure_ascii=False))
