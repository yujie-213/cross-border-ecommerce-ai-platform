"""Reproducible document/visual self-check; never business acceptance."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in channels]
    return sum(x * y for x, y in zip(linear, [0.2126, 0.7152, 0.0722]))


def contrast(a, b):
    low, high = sorted([luminance(a), luminance(b)])
    return (high + 0.05) / (low + 0.05)


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    observation = json.loads((ROOT / 'docs/ui/workspace-observation.json').read_text(encoding='utf-8'))
    protected = [x['path'] for x in observation['protectedUnknownPaths'] if digest(ROOT / x['path']) != x['sha256']]
    baseline = json.loads((ROOT / 'docs/planning/baseline-manifest.json').read_text(encoding='utf-8'))
    changed = [x['path'] for x in baseline if digest(ROOT / x['path']) != x['sha256']]
    pairs = [
        ('ink', '#202d3a', '#ffffff', 4.5), ('muted', '#5c6b79', '#f4f6f8', 4.5),
        ('primary', '#ffffff', '#126b65', 4.5), ('success', '#24664b', '#edf6ef', 4.5),
        ('warning', '#8a510b', '#fff4e2', 4.5), ('danger', '#ad3733', '#fcefee', 4.5),
        ('info', '#315e8f', '#eef4fb', 4.5), ('control', '#8996a3', '#ffffff', 3),
        ('focus', '#276aaf', '#ffffff', 3),
    ]
    ratios = [dict(token=n, foreground=a, background=b, ratio=round(contrast(a, b), 2), minimum=t,
                   result='PASS' if contrast(a, b) >= t else 'FAIL') for n, a, b, t in pairs]
    css = (ROOT / 'prototypes/s01/styles.css').read_text(encoding='utf-8').lower()
    css = re.sub(r'#[0-9a-f]{3}(?![0-9a-f])', lambda m: '#' + ''.join(c * 2 for c in m[0][1:]), css)
    tokens_present = all(a in css and b in css for _, a, b, _ in pairs)
    note = (ROOT / 'docs/ui/DESIGN_NOTE.md').read_text(encoding='utf-8')
    note_length = len(re.sub(r'\s', '', note))
    source_paths = ['DESIGN.md', 'docs/ui/PRODUCT_SPEC.md', 'docs/ui/ALIGNMENT.md',
                    'docs/ui/DESIGN_NOTE.md', 'docs/ui/RESEARCH.md']
    good = not changed and not protected and note_length <= 800 and tokens_present and all(x['result'] == 'PASS' for x in ratios)
    result = dict(kind='DESIGN_ALIGNMENT', reviewType='AUTHOR_SELF_CHECK_NOT_INDEPENDENT_ACCEPTANCE',
                  command='python docs/ui/check_design.py', implementationCommit=head, businessTests='NOT_RUN',
                  baselinesUnchanged=not changed, baselineMismatches=changed,
                  protectedUnknownFiles=len(observation['protectedUnknownPaths']), protectedMismatches=protected,
                  designNoteNonWhitespaceCharacters=note_length, designNoteWithin800=note_length <= 800,
                  paletteTokensPresentInCSS=tokens_present, contrastChecks=ratios,
                  sources=[dict(path=p, sha256=digest(ROOT / p)) for p in source_paths],
                  status='PASS' if good else 'FAIL')
    (ROOT / 'docs/ui/design-review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(status=result['status'], noteCharacters=note_length,
                          protectedFiles=len(observation['protectedUnknownPaths']), contrastPairs=len(ratios))))
    return 0 if good else 1


if __name__ == '__main__':
    raise SystemExit(main())
