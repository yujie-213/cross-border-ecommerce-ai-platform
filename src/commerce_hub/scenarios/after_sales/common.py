from datetime import datetime, timezone
import hashlib
import json
import re

from commerce_hub.orchestration.service import TaskError

SOURCE = 'MIDDLEWARE_TEACHING_DATA'
WORKSPACE = 'after-sales-v1'
SOURCE_TENANT = 'b-teaching-local'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        raise TaskError('TIMEZONE_UNKNOWN', 422) from None


def require(condition, code, status=422):
    if not condition:
        raise TaskError(code, status)


def redacted(text):
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[邮箱]', str(text))
    text = re.sub(r'(?<!\w)\+?\d[\d -]{6,}\d', '[号码]', text)
    return text[:6000]


def safety(text):
    return any(term in text.lower() for term in ('冒烟', '起火', '漏电', '触电', '烫伤', 'smoke', 'fire', 'burn', '发热'))


def scope(tenant, kind, rid=None, *, source=SOURCE, source_tenant=SOURCE_TENANT, version=None):
    return dict(schemaVersion='1.0.0', tenantId=tenant, workspaceId=WORKSPACE, resourceKind=kind,
        resourceId=rid, createParent=rid is None, datasetVersion=version if kind == 'DATASET' and rid else None,
        sourceNature=source, sourceTenant=source_tenant)
