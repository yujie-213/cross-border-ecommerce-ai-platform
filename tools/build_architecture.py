"""Extract Mermaid sources and assemble an offline architecture review document."""
from pathlib import Path
import argparse
import ast
import hashlib
import html
import json
import re
import zipfile
import xml.etree.ElementTree as ET

import markdown
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'docs/governance'))
from paths import root_links_to_relative,current_path
SOURCE = ROOT / "docs/architecture/ARCHITECTURE.md"
REQUIREMENTS = ROOT / "docs/requirements/REQUIREMENTS.md"
TARGET = SOURCE.with_suffix(".html")
DIR = ROOT / "docs/architecture/logical"
DIAGRAMS = DIR / "mermaid"
META = DIR / "architecture-manifest.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract():
    text = SOURCE.read_text(encoding="utf-8")
    blocks = re.findall(r"```mermaid\n(.*?)\n```", text, re.S)
    assert len(blocks) == 6, f"Expected 6 diagrams, got {len(blocks)}"
    DIAGRAMS.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": 1,
        "documentDate": "2026-11-11",
        "source": {"path": SOURCE.name, "sha256": digest(SOURCE)},
        "requirements": {"path": REQUIREMENTS.name, "version": "0.2", "sha256": digest(REQUIREMENTS)},
        "diagrams": [],
    }
    for block in blocks:
        slug = re.search(r"^\s*%% diagram: ([a-z0-9-]+)$", block, re.M).group(1)
        path = DIAGRAMS / f"{slug}.mmd"
        path.write_text(block + "\n", encoding="utf-8")
        manifest["diagrams"].append({"id": slug, "source": path.relative_to(ROOT).as_posix(), "sha256": digest(path), "svg": path.with_suffix(".svg").relative_to(ROOT).as_posix()})
    expected = {"W01", "O01", "D01", "D02", "D03", "D04", "B01", "B02", "A01", "A02", "A03", "C01", "C02", "C03", "G01", "G02", "I01"}
    required = REQUIREMENTS.read_text(encoding="utf-8")
    assert all(code in text and code in required for code in expected)
    assert all(f"S{i:02d}" in text for i in range(1, 11))
    coverage = text.split("### 11.1", 1)[1].split("### 11.2", 1)[0]
    assert set(map(int, re.findall(r"^\| (\d+) \|", coverage, re.M))) == set(range(1, 23))
    req_html = BeautifulSoup(REQUIREMENTS.with_suffix(".html").read_text(encoding="utf-8"), "html.parser")
    assert req_html.find("meta", attrs={"name": "source-sha256"})["content"] == digest(REQUIREMENTS), "Requirements HTML does not match Markdown"
    manifest["contentChecks"] = {"commonModules": len(expected), "scenarios": 10, "mappedCandidates": 22, "mermaidDiagrams": 6, "requirementsHtmlMatchesMarkdown": True}
    META.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest["contentChecks"], ensure_ascii=True))


def build():
    manifest = json.loads(META.read_text(encoding="utf-8"))
    assert digest(SOURCE) == manifest["source"]["sha256"], "Architecture changed since extraction"
    assert digest(REQUIREMENTS) == manifest["requirements"]["sha256"], "Requirements changed during build"
    receipt_path = DIR / "mermaid-render-check.json"
    render = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert render["status"] == "pass" and len(render["diagrams"]) == 6
    soup = BeautifulSoup(markdown.markdown(SOURCE.read_text(encoding="utf-8"), extensions=["tables", "fenced_code", "sane_lists"]), "html.parser")
    toc = []
    for index, heading in enumerate(soup.find_all("h2"), 1):
        heading["id"] = f"section-{index:02d}"
        toc.append(f'<a href="#section-{index:02d}">{html.escape(heading.get_text())}</a>')
    for table in list(soup.find_all("table")):
        table.wrap(soup.new_tag("div", attrs={"class": "table-scroll", "tabindex": "0", "role": "region", "aria-label": "架构设计表格，可横向滚动"}))
    replacements = {}
    for index, code in enumerate(list(soup.select("pre > code.language-mermaid"))):
        item = manifest["diagrams"][index]
        svg_path = ROOT / item["svg"]
        assert digest(ROOT / item["source"]) == item["sha256"]
        checked = next(d for d in render["diagrams"] if d["id"] == item["id"])
        assert digest(svg_path) == checked["svgSha256"]
        svg_text = svg_path.read_text(encoding="utf-8")
        assert ET.fromstring(svg_text).tag == "{http://www.w3.org/2000/svg}svg", "Standalone SVG must be valid XML"
        svg_text = re.sub(r"<\?xml[^>]*>\s*", "", svg_text)
        pre = code.parent
        figure = soup.new_tag("figure", attrs={"class": "diagram-figure", "data-diagram": item["id"]})
        tools = soup.new_tag("div", attrs={"class": "diagram-toolbar"})
        for label, command in [("适配宽度", "fit"), ("原始尺寸", "original"), ("放大", "in"), ("缩小", "out")]:
            button = soup.new_tag("button", attrs={"type": "button", "class": "button", "data-command": command})
            button.string = label
            tools.append(button)
        for label, target in [("打开 SVG", item["svg"]), ("Mermaid 图源", item["source"])]:
            link = soup.new_tag("a", attrs={"class": "button", "href": target, "target": "_blank", "rel": "noopener"})
            link.string = label
            tools.append(link)
        figure.append(tools)
        natural_width = checked["viewBox"][2]
        stage = soup.new_tag("div", attrs={"class": "diagram-stage", "tabindex": "0", "role": "region", "aria-label": f"{item['id']}，可滚动和缩放", "data-natural-width": str(natural_width)})
        token = f"__ARCHITECTURE_SVG_{index}__"
        stage.string = token
        replacements[token] = svg_text
        figure.append(stage)
        details = soup.new_tag("details", attrs={"class": "mermaid-source"})
        summary = soup.new_tag("summary")
        summary.string = "查看 / 复制 Mermaid 源码"
        details.append(summary)
        pre.replace_with(figure)
        details.append(pre)
        figure.append(details)
        item["svgSha256"] = digest(svg_path)
    # Reuse the established review document typography without executing its builder.
    css = (ROOT / "docs/requirements/assets/reader.css").read_text(encoding="utf-8")
    css += r"""
.reading-shell{max-width:1540px}.diagram-figure{margin:24px 0;border:1px solid var(--line);border-radius:5px;background:#fff;min-width:0;max-width:100%}.diagram-toolbar{display:flex;gap:6px;flex-wrap:wrap;padding:10px;background:#edf3ef;border-bottom:1px solid var(--line)}.diagram-stage{overflow:auto;max-height:900px;min-height:260px;padding:20px;background:#fff;max-width:100%}.diagram-stage svg{display:block;max-width:none;height:auto}.mermaid-source{padding:10px 16px;border-top:1px solid var(--line)}.mermaid-source summary{cursor:pointer;font-size:12px;color:var(--teal)}.mermaid-source pre{max-height:600px;overflow:auto;font-size:12px;white-space:pre}.source-stamp{font-size:11px;color:var(--muted);overflow-wrap:anywhere}main img{max-width:100%}@media print{.diagram-toolbar,.mermaid-source{display:none}.diagram-stage{overflow:visible;max-height:none;padding:5px;min-height:0}.diagram-stage svg{width:100%!important;height:auto!important;max-width:100%}.diagram-figure{break-inside:avoid}.topbar{display:none}}@media(max-width:760px){.toolbar{flex-wrap:wrap}.diagram-stage{padding:10px;max-height:75vh}.document h1{font-size:27px}.diagram-toolbar .button{font-size:10px;padding:5px 8px}}
"""
    options = ''.join(f'<option value="#section-{i:02d}">{html.escape(h.get_text())}</option>' for i,h in enumerate(soup.find_all("h2"), 1))
    script = r"""
document.getElementById('print').onclick=()=>window.print();
document.getElementById('jump').onchange=e=>document.querySelector(e.target.value)?.scrollIntoView();
document.querySelectorAll('.diagram-figure').forEach(figure=>{const stage=figure.querySelector('.diagram-stage');const svg=stage.querySelector('svg');const natural=Number(stage.dataset.naturalWidth);svg.style.width=natural+'px';stage.dataset.scale='1';figure.querySelectorAll('button[data-command]').forEach(button=>button.onclick=()=>{let scale=Number(stage.dataset.scale);const cmd=button.dataset.command;if(cmd==='fit')scale=Math.min(1,(stage.clientWidth-40)/natural);if(cmd==='original')scale=1;if(cmd==='in')scale=Math.min(3,scale*1.25);if(cmd==='out')scale=Math.max(.1,scale/1.25);stage.dataset.scale=scale;svg.style.width=(natural*scale)+'px';svg.style.height='auto';});});
const navs=[...document.querySelectorAll('.toc a')];const observer=new IntersectionObserver(entries=>{const first=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];if(first)navs.forEach(a=>a.classList.toggle('active',a.hash==='#'+first.target.id));},{rootMargin:'-85px 0px -65% 0px'});document.querySelectorAll('main h2').forEach(h=>observer.observe(h));
"""
    overview = '<div class="summary"><div><b>6</b><span>Mermaid 架构与流程图</span></div><div><b>10</b><span>完整产品场景</span></div><div><b>17</b><span>公共模块保持原编号</span></div><div><b>22</b><span>候选需求逐项覆盖</span></div></div>'
    content = str(soup)
    for token, svg in replacements.items():
        content = content.replace(token, svg)
    document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="requirements-sha256" content="{manifest['requirements']['sha256']}"><meta name="source-sha256" content="{digest(SOURCE)}"><title>总体逻辑架构与流程设计 · 跨境电商智慧中台</title><style>{css}</style></head><body>
<a class="skip" href="#document">跳至正文</a><aside class="sidebar"><div class="brand"><span class="kicker">COMMERCE AI HUB / ARCHITECTURE</span><h2>总体逻辑架构<br>与业务流程设计</h2><p>完整覆盖 · 分期实施 · 契约复用</p></div><nav class="toc" aria-label="文档目录">{''.join(toc)}</nav><div class="side-foot">V0.2 · 2026-11-11 · 架构评审草案</div></aside>
<div class="workspace"><div class="topbar"><span class="edition">AIH-ARCH-DRAFT-001 / MERMAID</span><select id="jump" class="mobile-toc" aria-label="跳转章节"><option value="#document">选择章节</option>{options}</select><div class="toolbar"><a class="button" href="{SOURCE.name}">Markdown 源文档</a><a class="button" href="docs/architecture/logical/mermaid-sources.zip">全部 Mermaid 图源</a><a class="button" href="../requirements/REQUIREMENTS.html">需求草案</a><button class="button" id="print" type="button">打印 / 保存 PDF</button></div></div>
<div class="reading-shell"><div class="eyebrow">完整逻辑范围，不等于首期部署清单</div>{overview}<p class="intro">六张图依次覆盖总体架构、跨领域只读分析、业务建议与人工审批、受控执行、完整数据流和首期部署。图按原始尺寸展示，可滚动、缩放或打开独立 SVG；下方保留可复制的 Mermaid 源码。</p><main class="document" id="document">{content}</main><footer><span>依据需求草案 v0.2 · 需求源指纹 {manifest['requirements']['sha256'][:12]}</span><span>离线 SVG 已嵌入；构建校验使用 Mermaid {render['mermaidVersion']}</span></footer></div></div><script>{script}</script></body></html>'''
    document = root_links_to_relative(document, TARGET)
    TARGET.write_text(document, encoding="utf-8")
    with zipfile.ZipFile(DIR / "mermaid-sources.zip", "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in manifest["diagrams"]:
            bundle.write(ROOT / item["source"], arcname=Path(item["source"]).name)
    # Check local navigation and final counts without treating SVG fragment IDs as document links.
    checked_doc = BeautifulSoup(document, "html.parser")
    assert len(checked_doc.select(".diagram-stage > svg")) == 6
    assert len(checked_doc.select("code.language-mermaid")) == 6
    assert len(checked_doc.select("main h2")) == 12
    for anchor in checked_doc.find_all("a", href=True):
        target = anchor["href"]
        if anchor.find_parent("svg") or target.startswith("#") or re.match(r"^[a-zA-Z][\w+.-]*:", target):
            continue
        assert (TARGET.parent / target.split("#")[0]).exists(), target
    manifest["artifact"] = {"path": TARGET.name, "sha256": digest(TARGET)}
    manifest["renderReceipt"] = receipt_path.relative_to(ROOT).as_posix()
    META.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "pass", "sections": 12, "diagrams": 6, "offlineHtmlBytes": TARGET.stat().st_size, "requirementsSha256": manifest["requirements"]["sha256"]}, ensure_ascii=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["extract", "build"])
    args = parser.parse_args()
    extract() if args.stage == "extract" else build()
