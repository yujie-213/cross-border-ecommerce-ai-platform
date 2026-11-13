"""One-off investigation, not a runtime connector. GET only after authentication.

Run from repository root with the project Python environment. Full responses stay
in the ignored private directory. No approvals, orders, receipts or stock posts.
"""
from pathlib import Path
import hashlib
import json
import sys
import time
from urllib.parse import urlencode
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from dotenv import dotenv_values
from commerce_hub.adapters.erp import ERPConfig, BASE_URL, AUTH_PATH, https_transport

OUT = ROOT / 'data/private/p3-erp-capability-20261113-r2'
OUT.mkdir(parents=True, exist_ok=True)
JOURNAL = OUT / 'journal.json'
if JOURNAL.exists():
    raise SystemExit('Existing investigation preserved; review it before a separately named run.')
values = dotenv_values(ROOT / '.env.erp', interpolate=False)
config = ERPConfig(base_url=values.get('ERP_BASE_URL') or BASE_URL, timeout=12)
mapping = json.loads((ROOT / 'data/private/s01-mvp-20261113/mapping-proposed.json').read_text(encoding='utf-8'))
assert len(mapping) == 2 and {x['monitor']['productId'] for x in mapping} == {'218', '219'}
m = mapping[0]
assert m['sourceWarehouse'] == '308' and m['monitor']['purchaseIds'] == ['1398']
tenant = m['sourceTenant']
journal = dict(baseCommit='db13298f7f85efbffa6e034bc3d7d2262de26e39',
               startedAt=datetime.now(timezone.utc).isoformat(), calls=[], checks={},
               mutationCalls=0, modelCalls=0, result='IN_PROGRESS')
token = ''


def save():
    JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def request(path, params=None, *, auth=False):
    global token
    assert len(journal['calls']) < 45
    assert auth and path == AUTH_PATH or not auth and path.startswith('/api/v1/')
    method = 'POST' if auth else 'GET'
    ev = dict(serial=len(journal['calls']) + 1, method=method, path=path,
              at=datetime.now(timezone.utc).isoformat(), state='SENDING')
    journal['calls'].append(ev)
    save()
    headers = {'Accept': 'application/json'}
    body = None
    target = path
    if auth:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(dict(appId=values.get('ERP_USERNAME'), appSecret=values.get('ERP_PASSWORD'))).encode()
    else:
        headers['Authorization'] = 'Bearer ' + token
        ev['query'] = params or {}
        if params:
            target += '?' + urlencode(params)
    time.sleep(.65)
    try:
        status, raw = https_transport(method, target, headers, body, config)
        ev.update(httpStatus=status, state='ACKNOWLEDGED')
        if auth:
            assert status == 200
            token = json.loads(raw)['data']['access_token']
            assert isinstance(token, str) and token
        else:
            ref = OUT / f'response-{ev["serial"]:03}.json'
            ref.write_bytes(raw)
            ev.update(responseRef=ref.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(raw).hexdigest())
        save()
        print(json.dumps({k: ev[k] for k in ['serial', 'method', 'path', 'httpStatus'] if k in ev}), flush=True)
        return status, {} if auth else json.loads(raw)
    except Exception as error:
        ev.update(state='FAILED', error=type(error).__name__)
        save()
        raise


def get(path, params=None):
    status, obj = request(path, params)
    assert status == 200, f'Expected read failed: {status}'
    return obj


def page(path, **params):
    obj = get(path, dict(limit=20, offset=0, **params))
    assert type(obj.get('total')) is int and isinstance(obj.get('items'), list)
    assert len(obj['items']) == obj['total'], 'Incomplete collection: do not infer absence'
    return obj['items']


try:
    request(AUTH_PATH, auth=True)
    me = get('/api/v1/me')
    me = me.get('data', me)
    assert str(me['tenant_id']) == tenant
    get('/api/v1/data-contract')
    get('/api/v1/access/catalog')
    get('/api/v1/access/roles')
    wh = get('/api/v1/warehouses/' + m['sourceWarehouse'])
    store = get('/api/v1/store-authorizations/' + m['sourceStore'])
    assert wh['name'] == m['warehouseName'] and str(wh['tenant_id']) == tenant
    assert str(store['tenant_id']) == tenant
    # Search by the independently verified warehouse, without registered IDs.
    params = dict(field='warehouse_name', q=m['warehouseName'], match='exact', limit=1, offset=0)
    first = get('/api/v1/purchase-orders', params)
    assert type(first['total']) is int and first['total'] <= 6
    rows = list(first['items'])
    for offset in range(1, first['total']):
        more = get('/api/v1/purchase-orders', dict(params, offset=offset))
        assert more['total'] == first['total'] and len(more['items']) == 1
        rows.extend(more['items'])
    assert len(rows) == first['total'] and len({r['id'] for r in rows}) == len(rows)
    assert all(str(r['tenant_id']) == tenant and r['warehouse_name'] == m['warehouseName'] for r in rows)
    assert any(str(r['id']) == '1398' for r in rows)
    # End page and alternate declared filter, both still bounded to the owned warehouse.
    end = get('/api/v1/purchase-orders', dict(params, offset=first['total']))
    assert end['total'] == first['total'] and not end['items']
    direct = page('/api/v1/purchase-orders', warehouse_name=m['warehouseName'])
    assert {r['id'] for r in direct} == {r['id'] for r in rows}
    journal['checks']['warehouseDiscovery'] = dict(total=len(rows), exactFieldAndDirectFilterAgree=True,
        endPageEmpty=True, uniqueIds=True, pages=first['total'], registeredIdsNotUsed=True)
    po = get('/api/v1/purchase-orders/1398')
    assert po == next(r for r in rows if r['id'] == 1398)
    context = get('/api/v1/record-context/purchase-orders/1398')
    assert context['record']['id'] == po['id']
    approvals = page('/api/v1/approvals', field='business_no', q=po['order_sn'], match='exact')
    for approval in approvals:
        assert str(approval['tenant_id']) == tenant and approval['business_no'] == po['order_sn']
        detail = get('/api/v1/approvals/' + str(approval['id']))
        assert detail == approval
    for resource in ['supplier-deliveries', 'inbound-orders']:
        linked = page('/api/v1/' + resource, field='purchase_order_sn', q=po['order_sn'], match='exact')
        assert all(r['purchase_order_sn'] == po['order_sn'] and str(r['tenant_id']) == tenant for r in linked)
    page('/api/v1/purchase-amendments', purchase_id=po['id'])
    # Read-only SKU search negative control; no assumption that unknown field is implemented.
    status, sku_result = request('/api/v1/purchase-orders', dict(params, field='sku', q=m['sku']))
    journal['checks']['skuSearch'] = dict(httpStatus=status, keys=list(sku_result))
    # Current balances and real posted ledger, restricted by owned inventory IDs.
    stock = get('/api/v1/inventory', dict(ids=','.join(x['monitor']['inventoryIds'][0] for x in mapping), view='full', limit=5, offset=0))
    assert stock['total'] == 2 and {str(r['id']) for r in stock['items']} == {'1137', '1138'}
    # Final independent re-read detects status drift during this non-atomic acquisition.
    final = get('/api/v1/purchase-orders/1398')
    assert final == po
    journal['checks']['purchaseStableAcrossIndependentReads'] = True
    journal['checks']['ownPurchaseLines'] = len(po.get('item_list', []))
    journal['checks']['approvalCount'] = len(approvals)
    journal['result'] = 'PASS_READ_ONLY_INVESTIGATION'
except Exception as error:
    journal['result'] = 'FAIL_PRESERVED'
    journal['error'] = type(error).__name__ + ': ' + str(error)[:180]
    raise
finally:
    journal['closedAt'] = datetime.now(timezone.utc).isoformat()
    save()
