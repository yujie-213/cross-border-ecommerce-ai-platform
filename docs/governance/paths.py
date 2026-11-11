"""Resolve historical evidence paths after document-only migration."""
from pathlib import Path
import json
import posixpath
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
MAP = json.loads((ROOT / 'docs/governance/migration.json').read_text(encoding='utf-8'))


def current_path(old):
    old = old.replace('\\', '/')
    if old in MAP['exact']:
        return MAP['exact'][old]
    for before, after in MAP['prefixes']:
        if old.startswith(before):
            return after + old[len(before):]
    return old


def historical_path(old):
    """Original frozen source remains byte-for-byte in an explicitly historic archive."""
    snapshot = ROOT / MAP['baselineArchive'] / old
    return snapshot if snapshot.is_file() else ROOT / current_path(old)


def relative_link(raw, old_doc, new_doc):
    if re.match(r'^(?:[a-zA-Z][\w+.-]*:|#|/)', raw) or '{' in raw:
        return raw
    target, sep, fragment = raw.partition('#')
    path, query_sep, query = target.partition('?')
    if not path:
        return raw
    old_target = posixpath.normpath(posixpath.join(posixpath.dirname(old_doc), unquote(path)))
    new_target = current_path(old_target)
    if not (ROOT / new_target).exists():
        return raw
    result = posixpath.relpath(new_target, posixpath.dirname(new_doc) or '.')
    return result + (query_sep + query if query_sep else '') + (sep + fragment if sep else '')


def migrated_text(text, old_doc, new_doc):
    """Only relocate Markdown/HTML destinations and literal project path references."""
    def md(m):
        return m[1] + relative_link(m[2], old_doc, new_doc) + m[3]
    text = re.sub(r'(\[[^\]\n]*\]\()([^\s)]+)(\))', md, text)
    text = re.sub(r'((?:href|src)=["\'])([^"\']+)(["\'])', md, text)
    # Backtick paths are project-root references, not new authoritative documents.
    def literal(m):
        raw = m[1]
        return '`' + current_path(raw) + '`'
    return re.sub(r'`([^`\n]+)`', literal, text)


def frozen_content_matches():
    errors = []
    baseline = json.loads((ROOT / MAP['baselineArchive'] / 'docs/planning/baseline-manifest.json').read_text(encoding='utf-8'))
    for item in baseline:
        old = item['path']; new = current_path(old)
        original = historical_path(old).read_text(encoding='utf-8')
        expected = migrated_text(original, old, new)
        if (ROOT / new).read_text(encoding='utf-8') != expected:
            errors.append(new)
    return errors


def root_links_to_relative(text, document):
    """Document builders may emit project-root paths; browsers need document-relative ones."""
    doc = Path(document)
    if doc.is_absolute():
        doc = doc.relative_to(ROOT)
    def rewrite(match):
        raw = match[2]
        if re.match(r'^(?:[a-zA-Z][\w+.-]*:|#)', raw) or '{' in raw:
            return match[0]
        target, sep, fragment = raw.partition('#')
        path = current_path(unquote(target))
        if (ROOT / path).exists() and not (ROOT / doc.parent / target).exists():
            raw = posixpath.relpath(path, doc.parent.as_posix()) + (sep + fragment if sep else '')
        return match[1] + raw + match[3]
    text = re.sub(r'((?:href|src)=["\'])([^"\']+)(["\'])', rewrite, text)
    return re.sub(r'(\[[^\]\n]*\]\()([^\s)]+)(\))', rewrite, text)
