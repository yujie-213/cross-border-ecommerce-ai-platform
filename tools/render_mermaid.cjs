/* Render the authored Mermaid sources locally. No product runtime dependencies. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('module').createRequire(process.env.PLAYWRIGHT_MODULE||require.resolve('playwright/package.json'))('playwright');
const root = path.resolve(__dirname, '..');
const directory = path.join(root, 'docs/architecture/logical');
const hash = data => crypto.createHash('sha256').update(data).digest('hex');

(async () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(directory, 'architecture-manifest.json'), 'utf8'));
  const vendor = JSON.parse(fs.readFileSync(path.join(directory, 'assets/mermaid-source.json'), 'utf8'));
  const library = path.join(directory, `assets/mermaid-${vendor.version}.min.js`);
  if (hash(fs.readFileSync(library)) !== vendor.sha256) throw new Error('Mermaid library hash mismatch');
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const page = await browser.newPage({ viewport: {width: 1920, height: 1080} });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const output = { status: 'running', mermaidVersion: vendor.version, librarySha256: vendor.sha256, diagrams: [], errors: [] };
  try {
    await page.setContent('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"></head><body><div id="render"></div></body></html>');
    await page.addScriptTag({ path: library });
    await page.evaluate(() => mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      htmlLabels: false,
      theme: 'base',
      fontFamily: 'Microsoft YaHei, Arial, sans-serif',
      themeVariables: { fontFamily: 'Microsoft YaHei, Arial, sans-serif', fontSize: '16px', primaryColor: '#e8f3ee', primaryTextColor: '#173342', primaryBorderColor: '#47887c', lineColor: '#526c76', secondaryColor: '#f0f3f5', tertiaryColor: '#fcfaf4', actorBkg: '#e8f3ee', actorBorder: '#47887c', actorTextColor: '#173342', noteBkgColor: '#fff4de', noteTextColor: '#543e20', noteBorderColor: '#c89b54', activationBkgColor: '#deeee6', signalColor: '#24495a', signalTextColor: '#173342' },
      flowchart: { htmlLabels: false, useMaxWidth: false, curve: 'linear', nodeSpacing: 28, rankSpacing: 58, padding: 16 },
      sequence: { useMaxWidth: false, wrap: true, width: 140, actorMargin: 25, messageMargin: 32, noteMargin: 14, wrapPadding: 10, diagramMarginX: 25, diagramMarginY: 20 }
    }));
    for (let index = 0; index < manifest.diagrams.length; index++) {
      const item = manifest.diagrams[index];
      const source = fs.readFileSync(path.join(root, item.source), 'utf8');
      if (hash(Buffer.from(source)) !== item.sha256) throw new Error(`Source hash mismatch: ${item.id}`);
      const rendered = await page.evaluate(async ({ source, id }) => {
        await mermaid.parse(source);
        const result = await mermaid.render(id, source);
        document.getElementById('render').innerHTML = result.svg;
        const svg = document.getElementById('render').querySelector('svg');
        const viewBox = svg.getAttribute('viewBox').split(/\s+/).map(Number);
        if (viewBox.length !== 4 || !viewBox.every(Number.isFinite) || viewBox[2] <= 0 || viewBox[3] <= 0) throw new Error('Invalid rendered viewBox');
        return { svg: new XMLSerializer().serializeToString(svg), viewBox, labels: svg.querySelectorAll('text').length, errorNodes: svg.querySelectorAll('.error-icon,.error-text').length };
      }, { source, id: `architecture_diagram_${index + 1}` });
      if (rendered.errorNodes) throw new Error(`Error nodes in diagram: ${item.id}`);
      const svgPath = path.join(root, item.svg);
      fs.writeFileSync(svgPath, rendered.svg, 'utf8');
      output.diagrams.push({ id: item.id, sourceSha256: item.sha256, svgSha256: hash(Buffer.from(rendered.svg)), viewBox: rendered.viewBox, textElements: rendered.labels, status: 'pass' });
    }
    if (errors.length) throw new Error(errors.join('\n'));
    output.status = 'pass';
  } catch (error) {
    output.status = 'fail';
    output.errors.push(error.stack || error.message);
    process.exitCode = 1;
  } finally {
    await browser.close();
    fs.writeFileSync(path.join(directory, 'mermaid-render-check.json'), JSON.stringify(output, null, 2));
    console.log(JSON.stringify(output));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
