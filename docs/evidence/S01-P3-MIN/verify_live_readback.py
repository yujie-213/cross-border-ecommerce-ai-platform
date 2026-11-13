"""Independent GET verification of the browser-created owned requisition.

No procurement mutation method is invoked. Full responses remain private.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from dotenv import dotenv_values
from commerce_hub.adapters.erp import ERPConfig, AUTH_PATH, https_transport
from commerce_hub.adapters.erp_requisition import TeachingRequisitionClient
from commerce_hub.data.sync.online import OnlineMapping
from commerce_hub.data.projection.purchases import FORMAL_STATES


def main():
    source = ROOT/'data/private/s01-p3-min'
    operation = json.loads((source/'browser-operation.json').read_text(encoding='utf-8'))
    report = json.loads((source/'browser-report.json').read_text(encoding='utf-8'))
    result = operation['result']
    mapping = [OnlineMapping.model_validate(v) for v in json.loads((ROOT/'data/private/s01-mvp-20261113/mapping-proposed.json').read_text(encoding='utf-8'))]
    m = next(v for v in mapping if v.scope == report['scope'])
    assert m.sku == 'HL-CBL100-2M' and m.monitor.productId == '218' and m.sourceWarehouse == '308'
    assert result['state'] == 'SUBMITTED' and result['finalQuantity'] == 48 and result['erpId'] != '1398'
    out = source/('independent-'+datetime.now(timezone.utc).strftime('%H%M%S'))
    out.mkdir(exist_ok=False)
    calls = []
    values = dotenv_values(ROOT/'.env.erp', interpolate=False)
    def transport(method, target, headers, body, config):
        assert method == 'GET' or method == 'POST' and target == AUTH_PATH
        status, raw = https_transport(method, target, headers, body, config)
        ev = dict(method=method, path=target.split('?')[0], httpStatus=status, at=datetime.now(timezone.utc).isoformat())
        if target != AUTH_PATH:
            path = out/f'response-{len(calls)+1:03d}.json'
            path.write_bytes(raw)
            ev.update(sha256=hashlib.sha256(raw).hexdigest(),privateResponse=path.relative_to(ROOT).as_posix())
        calls.append(ev)
        (out/'journal.json').write_text(json.dumps(calls,ensure_ascii=False,indent=2),encoding='utf-8')
        return status, raw
    client = TeachingRequisitionClient(ERPConfig(username=values.get('ERP_USERNAME') or '', password=values.get('ERP_PASSWORD') or '',
        access_token=values.get('ERP_ACCESS_TOKEN') or '',max_requests=12),transport=transport)
    batch = client.find_requisition(result['erpNumber'])
    assert batch.complete and batch.total == 1
    po = client.read_requisition(result['erpId'])
    assert po == batch.records[0] and str(po['id']) == result['erpId'] and str(po['tenant_id']) == m.sourceTenant
    assert po['status_text'] == '待审核' and po['warehouse_name'] == m.warehouseName
    assert len(po['item_list']) == 1 and po['item_list'][0]['sku'] == m.sku and po['item_list'][0]['quantity'] == 48
    assert po['received_qty'] == 0 and po['pending_qty'] == 48 and po['amount'] == 115.2
    inv = client.reader.read('/api/v1/inventory',dict(ids=','.join(m.monitor.inventoryIds)),page_size=5,max_pages=1)
    assert inv.complete and inv.total == 1 and inv.records[0]['quantity'] == inv.records[0]['available'] == 6
    formal = []
    for state in FORMAL_STATES:
        rows = client.reader.read('/api/v1/purchase-orders',dict(warehouse_name=m.warehouseName,field='status_text',q=state,match='exact'),page_size=50,max_pages=2)
        assert rows.complete and all(r['status_text'] == state for r in rows.records)
        formal.extend(rows.records)
    assert not formal, 'New formal data requires scope review, never infer it is absent'
    private_requests = []
    for journal in (ROOT/'data/private/s01-requisitions'/result['operationId']).glob('attempt-*/requests.jsonl'):
        private_requests.extend(json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines())
    mutations = [e for e in private_requests if e['method'] == 'POST']
    assert len(mutations) == 2 and {e['path'] for e in mutations} == {'/api/v1/purchase-orders',f"/api/v1/workflows/purchase-orders/{result['erpId']}/submit"}
    assert sorted(e['httpStatus'] for e in mutations) == [200,201]
    summary = dict(sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',observedHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        observedAt=datetime.now(timezone.utc).isoformat(),liveOperation=result,independentCalls=calls,
        mutations=mutations,independentListTotal=batch.total,createSubmitReadback='VERIFIED',sameOperationReplay=operation['replay']==result,
        inventoryAfter=dict(physical=6,available=6),formalApprovedQueries='VERIFIED_EMPTY',positiveApprovedSample='BLOCKED_NO_AUTHORIZED_SAMPLE',
        sellableSupply='UNKNOWN_NOT_DEDUCTED',approvalDecisions=0,placeOrders=0,receipts=0,inboundConfirmations=0,modelCalls=0,
        browserPageErrors=operation['pageErrors'])
    (ROOT/'docs/evidence/S01-P3-MIN/live-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(erpId=result['erpId'],status=po['status_text'],quantity=48,requestCount=len(calls),mutations=2,result='PASS'),ensure_ascii=False))


if __name__ == '__main__':
    main()
