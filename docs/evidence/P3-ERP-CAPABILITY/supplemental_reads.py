"""Additional bounded GET observations, with no mutation workflow calls."""
from pathlib import Path
import sys
import json
import time
import hashlib
from urllib.parse import urlencode
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from dotenv import dotenv_values
from commerce_hub.adapters.erp import ERPConfig, BASE_URL, AUTH_PATH, https_transport

OUT = ROOT / 'data/private/p3-erp-capability-20261113-ledger-exact'
OUT.mkdir(exist_ok=True, parents=True)
assert not (OUT / 'journal.json').exists(), 'Preserve previous run'
cfg = dotenv_values(ROOT / '.env.erp', interpolate=False)
config = ERPConfig(base_url=cfg.get('ERP_BASE_URL') or BASE_URL, timeout=12)
mappings = json.loads((ROOT / 'data/private/s01-mvp-20261113/mapping-proposed.json').read_text(encoding='utf-8'))
m = mappings[0]
calls = []


def call(method, path, params=None, auth=False):
    assert auth and path == AUTH_PATH or method == 'GET' and path in {
        '/api/v1/sales-workflow/1153929', '/api/v1/stock/ledger', '/api/v1/purchase-orders/1398'}
    headers = {'Accept': 'application/json'}
    body = None
    target = path
    if auth:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(dict(appId=cfg.get('ERP_USERNAME'), appSecret=cfg.get('ERP_PASSWORD'))).encode()
    else:
        headers['Authorization'] = 'Bearer ' + token
        if params:
            target += '?' + urlencode(params)
    ev = dict(serial=len(calls)+1, at=datetime.now(timezone.utc).isoformat(), method=method, path=path)
    if not auth:
        ev['query'] = params or {}
    calls.append(ev)
    time.sleep(.65)
    try:
        status, raw = https_transport(method, target, headers, body, config)
        ev['httpStatus'] = status
        if not auth:
            p = OUT / f'response-{len(calls):03}.json'
            p.write_bytes(raw)
            ev.update(responseRef=p.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(raw).hexdigest())
        print(json.dumps(dict(serial=ev['serial'], path=path, httpStatus=status)), flush=True)
        return status, json.loads(raw)
    except Exception as error:
        ev.update(state='FAILED', error=type(error).__name__)
        raise
    finally:
        (OUT/'journal.json').write_text(json.dumps(dict(calls=calls, mutationCalls=0, modelCalls=0),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


status, auth = call('POST', AUTH_PATH, auth=True)
assert status == 200
token = auth['data']['access_token']
# Previous wide SKU+warehouse ledger timed out; retain it and query an exact
# owned outbound identified through the registered sale's actual workflow.
assert '1153929' in m['monitor']['salesIds']
status, workflow = call('GET', '/api/v1/sales-workflow/1153929')
assert status == 200 and workflow['data']['order_id'] == 1153929
for shipment in workflow['data']['shipments']:
    assert shipment['order_id'] == 1153929
    outbound = shipment['outbound_id']
    assert type(outbound) is int and outbound > 0
    status, obj = call('GET', '/api/v1/stock/ledger',dict(resource='outbound-orders', record_id=outbound, offset=0, limit=20))
    assert status == 200 and len(obj['items']) == obj['total']
    assert all(r['record_id'] == outbound and str(r['inventory_id']) in {'1137','1138'} for r in obj['items'])
call('GET', '/api/v1/purchase-orders/1398')
