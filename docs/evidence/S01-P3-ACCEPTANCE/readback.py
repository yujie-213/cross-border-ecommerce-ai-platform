"""Independent bounded GET verification; never calls a business mutation."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from dotenv import dotenv_values
from commerce_hub.adapters.erp import ERPConfig, AUTH_PATH, https_transport
from commerce_hub.adapters.erp_requisition import TeachingRequisitionClient
from commerce_hub.data.projection.purchases import FORMAL_STATES


def main():
    original = json.loads((ROOT/'data/private/s01-p3-min/browser-operation.json').read_text(encoding='utf-8'))['result']
    private = ROOT/'data/private/s01-p3-acceptance'/datetime.now(timezone.utc).strftime('readback-%H%M%S')
    private.mkdir(parents=True, exist_ok=False)
    events = []
    def transport(method, target, headers, body, config):
        assert method == 'GET' or method == 'POST' and target == AUTH_PATH
        event = dict(method=method, path=target.split('?')[0], at=datetime.now(timezone.utc).isoformat())
        events.append(event)
        try:
            status, raw = https_transport(method, target, headers, body, config)
            event['httpStatus'] = status
            if target != AUTH_PATH:
                p = private/f'response-{len(events):03d}.json'
                p.write_bytes(raw)
                event.update(sha256=hashlib.sha256(raw).hexdigest(), privateResponse=p.relative_to(ROOT).as_posix())
            return status, raw
        except Exception as exc:
            event['errorType'] = type(exc).__name__
            raise
        finally:
            (private/'journal.json').write_text(json.dumps(events, indent=2)+'\n', encoding='utf-8')
    v = dotenv_values(ROOT/'.env.erp', interpolate=False)
    client = TeachingRequisitionClient(ERPConfig(username=v.get('ERP_USERNAME') or '', password=v.get('ERP_PASSWORD') or '',
        access_token=v.get('ERP_ACCESS_TOKEN') or '', max_requests=12), transport=transport)
    batch = client.find_requisition(original['erpNumber'])
    po = client.read_requisition(original['erpId'])
    assert batch.complete and batch.total == 1 and po == batch.records[0]
    assert str(po['id']) == '1406' and str(po['tenant_id']) == '1' and po['status_text'] == '待审核'
    assert po['order_sn'] == original['erpNumber'] and len(po['item_list']) == 1
    line = po['item_list'][0]
    assert line['sku'] == 'HL-CBL100-2M' and line['quantity'] == 48
    assert po['received_qty'] == 0 and po['pending_qty'] == 48 and po['amount'] == 115.2
    mappings = json.loads((ROOT/'data/private/s01-mvp-20261113/mapping-proposed.json').read_text(encoding='utf-8'))
    m = next(x for x in mappings if x['sku'] == line['sku'])
    assert po['warehouse_name'] == m['warehouseName']
    stock = client.reader.read('/api/v1/inventory', dict(ids=','.join(m['monitor']['inventoryIds'])), page_size=5, max_pages=1)
    assert stock.complete and stock.total == 1 and stock.records[0]['available'] == stock.records[0]['quantity'] == 6
    formal = []
    for state in FORMAL_STATES:
        rows = client.reader.read('/api/v1/purchase-orders', dict(warehouse_name=m['warehouseName'], field='status_text', q=state, match='exact'), page_size=50, max_pages=2)
        assert rows.complete and all(x['status_text'] == state for x in rows.records)
        formal.extend(rows.records)
    summary = dict(result='PASS', observedAt=datetime.now(timezone.utc).isoformat(),
        observedHead=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP', erpId='1406', quantity=48, status=po['status_text'],
        independentListTotal=batch.total, inventoryAvailable=6, formalRecordCount=len(formal),
        positiveApprovedSample='NOT_VERIFIED', effectiveTransitDeduction='UNKNOWN_NOT_DEDUCTED',
        events=events, businessMutations=0, modelCalls=0)
    (ROOT/'docs/evidence/S01-P3-ACCEPTANCE/live-readback.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n', encoding='utf-8',newline='\n')
    print(json.dumps({k:summary[k] for k in ['result','erpId','quantity','status','formalRecordCount','businessMutations']},ensure_ascii=False))


if __name__ == '__main__':
    main()
