"""Read-only publication checks; output contains locations, never secret values.

The publication gate remains closed on uncertain provenance or missing authentication.
This is documentation tooling, not platform implementation or business acceptance.
"""
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from paths import ROOT, MAP, current_path, frozen_content_matches

OUT = ROOT / 'docs/governance/audit.json'
EXCLUDED = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.cache'}
SECRET_RULES = {
    'PRIVATE_KEY': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'API_KEY': r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}',
    'GITHUB_TOKEN': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
    'AWS_KEY': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'SLACK_TOKEN': r'\bxox[baprs]-[A-Za-z0-9-]{20,}',
    'CREDENTIAL_URL': r'(?:mysql|postgres(?:ql)?|https?)://[^\s/:<>]+:[^\s/@<>]{6,}@',
    'LITERAL_SECRET': r'''(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*["']?\s*[:=]\s*["'][A-Za-z0-9+/=_-]{20,}["']''',
}
PII_RULES = {
    'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'CN_MOBILE': r'(?<![0-9])1[3-9][0-9]{9}(?![0-9])',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def public_files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file()
                  and not any(x in EXCLUDED for x in p.relative_to(ROOT).parts)
                  and 'local' not in p.relative_to(ROOT).parts)


def scan_bytes(data, label, pii=True):
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return []
    found = []
    for name, regex in {**SECRET_RULES, **(PII_RULES if pii else {})}.items():
        matches = list(re.finditer(regex, text))
        if matches:
            found.append(dict(path=label, rule=name, count=len(matches),
                              lines=sorted({text.count('\n', 0, m.start()) + 1 for m in matches})[:12]))
    return found


def scan_zip(data, label):
    found = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.file_size > 20 * 1024 * 1024:
                found.append(dict(path=label, rule='ZIP_MEMBER_TOO_LARGE_FOR_REVIEW'))
                continue
            found.extend(scan_bytes(archive.read(info), label + '!' + info.filename))
    return found


def history_check():
    objects = git('rev-list', '--objects', '--all').decode().splitlines()
    reachable = {line.split(' ', 1)[0] for line in objects}
    all_objects = git('cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)').decode().splitlines()
    unreachable = [line.split()[0] for line in all_objects if line.split()[0] not in reachable]
    objects += unreachable
    process = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    found = []; blobs = 0; commits = 0; largest = 0
    for line in objects:
        oid, _, name = line.partition(' ')
        process.stdin.write((oid + '\n').encode()); process.stdin.flush()
        header = process.stdout.readline().decode().split()
        typ, size = header[1], int(header[2])
        data = process.stdout.read(size); process.stdout.read(1)
        # Git tree binary object names/hashes are not text; do not scan them as phone numbers.
        if typ == 'blob':
            blobs += 1; largest = max(largest, size)
            found.extend(scan_bytes(data, 'history:' + oid + ':' + name))
            if name.endswith('.zip') or data.startswith(b'PK\x03\x04'):
                found.extend(scan_zip(data, 'history:' + oid + ':' + name))
        elif typ in {'commit', 'tag'}:
            commits += typ == 'commit'
            # Author/committer emails are separately disclosed and explicitly consented.
            message = data.split(b'\n\n', 1)[-1]
            found.extend(scan_bytes(message, 'history-message:' + oid))
            found.extend(scan_bytes(data, 'history-metadata:' + oid, pii=False))
    process.stdin.close(); process.wait()
    return dict(reachableObjects=len(reachable), unreachableObjectsScanned=len(unreachable), uniqueBlobs=blobs, commits=commits,
                largestBlobBytes=largest, findings=found,
                scope='All reachable refs plus every locally stored unreachable Git object; blob ZIP contents and commit/tag messages included; no history rewritten',
                historicalEmailConsent=MAP['emailPublicationConsent'])


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set(); self.svg = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'svg':
            self.svg += 1
        if not self.svg:
            for key in ('href', 'src'):
                if attrs.get(key):
                    self.links.append(attrs[key])

    def handle_endtag(self, tag):
        if tag == 'svg':
            self.svg = max(0, self.svg - 1)


def document_links(p):
    text = p.read_text(encoding='utf-8-sig')
    if p.suffix == '.html':
        parser = Links(); parser.feed(text)
        return parser.links
    # Ignore fenced examples and inline code; parse prose links, images and HTML attributes.
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`\n]*`', '', text)
    links = re.findall(r'\[[^\]\n]*\]\(([^\s)]+)\)', text)
    links += re.findall(r'(?:href|src)=["\']([^"\']+)["\']', text)
    return links


def link_check(files):
    broken = []; historical = []; checked = 0; external = 0
    for p in files:
        if p.suffix not in {'.md', '.html'}:
            continue
        archived = p.is_relative_to(ROOT / 'docs/archive')
        for raw in document_links(p):
            if re.match(r'^[a-zA-Z][\w+.-]*:', raw) or raw.startswith('//'):
                external += 1; continue
            target = unquote(raw.split('#', 1)[0].split('?', 1)[0]).strip('<>')
            fragment = unquote(raw.partition('#')[2])
            if not target:
                if fragment and p.suffix == '.html' and not p.is_relative_to(ROOT / 'prototypes'):
                    parser = Links(); parser.feed(p.read_text(encoding='utf-8-sig'))
                    if fragment not in parser.ids:
                        item = dict(doc=p.relative_to(ROOT).as_posix(), target=raw, reason='missing-fragment')
                        (historical if archived else broken).append(item)
                continue
            checked += 1
            resolved = (p.parent / target).resolve()
            if not resolved.is_relative_to(ROOT):
                broken.append(dict(doc=p.relative_to(ROOT).as_posix(), target=raw, reason='escapes-repository'))
            elif not resolved.exists():
                item = dict(doc=p.relative_to(ROOT).as_posix(), target=raw)
                (historical if archived else broken).append(item)
    return dict(checkedLocalTargets=checked, externalReferencesNotFetched=external,
                brokenActive=broken, historicalMissing=historical)


def state_check():
    before = git('show', MAP['startHead'] + ':docs/TASKS.md').decode()
    after = (ROOT / 'docs/TASKS.md').read_text(encoding='utf-8')
    def tasks(s):
        return {t['id']: t for t in map(json.loads, re.findall(r'```json\s*\n(.*?)```', s, re.S))}
    old, new = tasks(before), tasks(after)
    fields = ['status', 'dependsOn', 'acceptance', 'implementationCommits', 'testedCommit', 'review', 'history']
    changed = [key for key in old if key not in new or any(old[key][field] != new[key][field] for field in fields)]
    fixture_errors = []
    for name in ['app.js', 'demo-data.js', 'styles.css', 'index.html', 'check.cjs']:
        rel = 'prototypes/s01/' + name
        if (ROOT / rel).read_bytes() != git('show', MAP['startHead'] + ':' + rel):
            fixture_errors.append(rel)
    archive_errors = [x['path'] for x in MAP.get('archiveFiles', []) if digest(ROOT / x['path']) != x['sha256']]
    return dict(taskCount=len(new), sameTaskIds=old.keys() == new.keys(), taskSemanticChanges=changed,
                archiveByteMismatches=archive_errors,
                prototypeChanged=fixture_errors, frozenBusinessRuleChanges=frozen_content_matches())


def main():
    files = public_files(); findings = []
    for p in files:
        # Never scan our own location-only report as user data (Git history still scans it).
        if p == OUT:
            continue
        findings.extend(scan_bytes(p.read_bytes(), p.relative_to(ROOT).as_posix()))
        if p.suffix == '.zip':
            findings.extend(scan_zip(p.read_bytes(), p.relative_to(ROOT).as_posix()))
    history = history_check(); links = link_check(files); states = state_check()
    excluded = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
                and '.git' not in p.parts and ('local' in p.relative_to(ROOT).parts or any(x in EXCLUDED - {'.git'} for x in p.parts))]
    sensitive = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts
                 and re.match(r'(?i)(\.env(?:\..*)?|credentials.*|id_rsa.*|.*\.(?:pem|key|p12|pfx|db|sqlite|gguf|safetensors))$', p.name)
                 and p.name != '.env.example']
    gh = shutil.which('gh')
    tests = json.loads((ROOT / 'docs/governance/local/tests.json').read_text(encoding='utf-8')) if (ROOT / 'docs/governance/local/tests.json').exists() else []
    blockers = ['第三方Mermaid及内嵌图示运行时代码的完整再分发许可/依赖声明尚未核验；未增加项目LICENSE']
    if not gh:
        blockers.append('GitHub CLI (gh) 未安装或不在PATH，未验证登录账号/创建权限/同名仓库；未创建远端或推送')
    if findings or history['findings'] or sensitive:
        blockers.append('秘密/个人信息/敏感文件候选尚待逐项判定')
    state_failure = (not states['sameTaskIds'] or states['taskSemanticChanges'] or states['archiveByteMismatches']
                     or states['prototypeChanged'] or states['frozenBusinessRuleChanges'])
    if links['brokenActive'] or state_failure:
        blockers.append('文档/状态一致性检查失败')
    report = dict(scope='DOCUMENT_GOVERNANCE_AND_PUBLICATION_PREPARATION_ONLY',
                  observedHead=git('rev-parse', 'HEAD').decode().strip(),
                  inventory=dict(files=len(files), totalBytes=sum(p.stat().st_size for p in files),
                                 byExtension=dict(Counter(p.suffix or '<none>' for p in files)),
                                 markdownAndHtml=sum(p.suffix in {'.md', '.html'} for p in files),
                                 largestFiles=[dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size) for p in sorted(files, key=lambda p: p.stat().st_size, reverse=True)[:5]]),
                  worktreeFindings=findings, sensitiveFiles=sensitive, excludedLocalFiles=excluded,
                  history=history, links=links, invariants=states, tests=tests,
                  screenshotReview=MAP.get('screenshotsReviewed'),
                  publication=dict(status='BLOCKED' if blockers else 'READY_FOR_AUTHENTICATED_RELEASE', blockers=blockers,
                                   ghAvailable=bool(gh), repositoryUrl=None, publicVerified=False, remoteHead=None),
                  limitations='Pattern scans cannot prove absence of every secret or private business fact. Historical archive links are separately reported; screenshots require visual review. No business service, model, ERP or production acceptance was run.')
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=len(files), commits=history['commits'], blobs=history['uniqueBlobs'],
                          currentFindings=len(findings), historyFindings=len(history['findings']),
                          brokenActiveLinks=len(links['brokenActive']), historicalMissing=len(links['historicalMissing']),
                          invariants=states, publication=report['publication']['status']), ensure_ascii=False))
    return 1 if findings or history['findings'] or sensitive or links['brokenActive'] or state_failure else 0


if __name__ == '__main__':
    raise SystemExit(main())
