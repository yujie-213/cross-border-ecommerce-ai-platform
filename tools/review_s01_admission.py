"""Read-only forensic audit. Explicit --live reads only the two registered SKUs.

No model, activation, migration, application writes or ERP business writes.
Public output is a field whitelist; full responses/checkpoints remain private.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/S01-DATA-REVIEW'
SKUS = ('HL-CBL100-2M', 'HL-MUG350-WH')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sales_summary(rows, sku):
    result = []
    for r in rows:
        lines = [x for x in r.get('item_list', []) if x.get('sku') == sku]
        if lines:
            result.append(dict(id=r['id'], date=r['order_time'], quantity=sum(Decimal(str(x['quantity'])) for x in lines),
                status=[r.get(k) for k in ('payment_status', 'fulfillment_status', 'refund_status')],
                createdAt=r.get('created_at'), updatedAt=r.get('updated_at'), recordDigest=digest(r)))
    return sorted(result, key=lambda r: r['id'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ.update(COMMERCE_MODEL_PROVIDER='mock', COMMERCE_MODEL_NETWORK_ENABLED='false')
    from sqlalchemy import select
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database, assert_migration_target
    from commerce_hub.data.sync.v2_store import acquisitions
    from commerce_hub.scenarios.s01_v2.store import ItemStore
    from commerce_hub.data.sync.online import OnlineMapping
    from commerce_hub.data.projection.owned import normalize_owned
    from commerce_hub.data.contracts import fingerprint
    from commerce_hub.data.quality.v2 import verify_result
    mappings = [OnlineMapping.model_validate(m) for m in read(ROOT / 'data/private/s01-mvp-20261113/mapping-proposed.json')]
    result = dict(nature='READ_ONLY_HISTORICAL_CAPTURE_AND_LOCAL_DB_SELECT', observedAt=datetime.now(timezone.utc).isoformat(),
                  baseline='ece11160ecd0e820153a1c58128657a2f8788884', old=[], v2=[], newModelCalls=0, businessWrites=0)
    folders = ('verification-HL-CBL100-2M-096bec03', 'verification-HL-MUG350-WH-7d5b061e')
    originals = {}
    for m, folder in zip(mappings, folders):
        path = ROOT / 'data/private/s01-mvp-20261113' / folder
        caps, receipt, asset = [read(path / f) for f in ('captures.json', 'receipt.json', 'asset.json')]
        assert all(v['fingerprint']==fingerprint(v['rows']) for v in caps.values())
        original = originals[m.sku] = caps
        n = normalize_owned(caps, m, receipt, True)
        assert n['input'] is not None
        result['old'].append(dict(sku=m.sku, startedAt=receipt['startedAt'], completedAt=receipt['completedAt'],
            snapshotId=asset['snapshotId'], policy=m.monitor.policy.model_dump(),
            window=[n['forecast']['windowStart'], n['forecast']['windowEnd']],
            stock=n['forecast']['stockReconciliation'], sales=sales_summary(original['sales']['rows'], m.sku),
            ledgers=[{k:r.get(k) for k in ('id','resource','record_id','inventory_id','sku','before_quantity','delta_quantity','after_quantity','created_at','operation','reverses_id')}
                for name,cap in caps.items() if name.startswith('ledger-') for r in cap['rows'] if r.get('sku')==m.sku],
            captureFiles={f:hashlib.sha256((path/f).read_bytes()).hexdigest() for f in ('captures.json','receipt.json','asset.json')}))
    settings = load_settings(); assert_migration_target(settings); db = Database(settings)
    try:
        # Exact historical task references; SELECT only on the existing approved local DB.
        for task in ('7463f8f27ccb4915900f4f2a2541a4e1', 'b3eb6b413fd84de7a4cce2b4ac80e4bf', '86af50d1d0814c81a1713e792fa8a267'):
            with db.engine.connect() as c:
                row = c.execute(select(acquisitions).filter_by(tenant_id='s01-v2-teaching-local', task_id=task)).mappings().one()
                items = ItemStore.read(c, 's01-v2-teaching-local', task)
                for item in items.values(): verify_result(item)
            state = row['content']; caps = {}; proofs = []
            for name, resource in state['resources'].items():
                rows = []
                for page in resource['pages']:
                    path = ROOT / 'data/private/s01-v2/s01-v2-teaching-local' / task / page['file']
                    raw = path.read_bytes(); assert hashlib.sha256(raw).hexdigest() == page['sha256']
                    data = json.loads(raw); rows += [data] if resource['binding']['detail'] else data['items']
                    proofs.append(page['sha256'])
                caps[name] = rows
            record = dict(taskId=task, startedAt=state['startedAt'],
                sealedResultsVerified=len(items),
                salesQuery=state['resources']['sales']['binding']['parameters'],
                salesComplete=state['resources']['sales']['complete'], verifiedFiles=sorted(set(proofs)), targets=[])
            for m in mappings:
                sku=m.sku; b=m.monitor
                inv=[r for r in caps['inventory'] if str(r['id']) in b.inventoryIds]
                sales=sales_summary(caps['sales'],sku)
                total=sum((r['quantity'] for r in sales),Decimal(0)); physical=sum(Decimal(str(r['quantity'])) for r in inv)
                prior=originals[sku]
                observed=[r for r in items.values() if r['sku']==sku and r['warehouseId']==m.sourceWarehouse]
                ledger_equal=all(caps.get(k)==v['rows'] for k,v in prior.items() if k.startswith('ledger-') and k in caps)
                record['targets'].append(dict(sku=sku, inventory=[{k:r.get(k) for k in ('id','quantity','available','updated_at')} for r in inv],
                    inventoryIdenticalToOld=inv==prior['inventory']['rows'], sales=sales,
                    salesRowsIdenticalToOld=all(r in prior['sales']['rows'] for r in caps['sales'] if any(x.get('sku')==sku for x in r.get('item_list',[]))),
                    includedLedgerRowsIdenticalToOld=ledger_equal,
                    omittedRegisteredSales=sorted(set(b.salesIds)-{str(r['id']) for r in sales}),
                    opening=b.openingQuantity, selectedSold=str(total), physical=str(physical),
                    expected=str(Decimal(b.openingQuantity)-total), difference=str(Decimal(b.openingQuantity)-total-physical),
                    storedResult=[{k:r.get(k) for k in ('sourceGrade','analysisState','quantity','ruleFailureCodes','snapshotRef','snapshotManifest')} for r in observed],
                    ruleSnapshots=[(r.get('ruleResult') or {}).get('snapshotId') for r in observed]))
            result['v2'].append(record)
    finally:
        db.close()
    save(OUT/'forensics.json',result)
    if args.live:
        from dotenv import dotenv_values
        from commerce_hub.adapters.erp import ERPConfig
        from commerce_hub.data.sync.v2 import V2Reader
        private=ROOT/'data/private/s01-data-review'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        class Checkpoint:
            def load(self): return dict(requestCount=0)
            def save(self,v): save(private/'checkpoint.json',v)
        env=dotenv_values(ROOT/'.env.erp',interpolate=False)
        reader=V2Reader(ERPConfig(username=env.get('ERP_USERNAME') or '', password=env.get('ERP_PASSWORD') or '',
            access_token=env.get('ERP_ACCESS_TOKEN') or '',max_requests=40), private, Checkpoint(), lambda:None,request_limit=40)
        reader.authenticate('1')
        current=[]
        for m in mappings:
            inv=reader.resource('inventory-'+m.sku,'/api/v1/inventory',dict(ids=','.join(m.monitor.inventoryIds)))
            sales=reader.resource('sales-'+m.sku,'/api/v1/sales-orders',dict(ids=','.join(m.monitor.salesIds),view='full'))
            assert inv['complete'] and sales['complete']
            assert {str(r['id']) for r in inv['rows']}==set(m.monitor.inventoryIds)
            assert {str(r['id']) for r in sales['rows']}==set(m.monitor.salesIds)
            assert all(str(r.get('tenant_id'))==m.sourceTenant for r in inv['rows']+sales['rows'])
            current.append(dict(sku=m.sku, inventory=[{k:r.get(k) for k in ('id','quantity','available','updated_at')} for r in inv['rows']],
                inventoryIdenticalToOriginal=inv['rows']==originals[m.sku]['inventory']['rows'],
                registeredSalesIdenticalToOriginal=sorted(sales['rows'],key=lambda r:r['id'])==sorted(originals[m.sku]['sales']['rows'],key=lambda r:r['id']),
                registeredSales=sales_summary(sales['rows'],m.sku)))
        receipt=reader.receipt()
        save(OUT/'current-read.json',dict(nature='REAL_ERP_READ_ONLY_REGISTERED_IDS_NOT_COMPLETE_MOVEMENT_DISCOVERY',
            startedAt=receipt['startedAt'],completedAt=receipt['completedAt'],requestCount=receipt['requestCount'],
            events=[{k:e[k] for k in ('method','path','at','httpStatus','sha256','error') if k in e} for e in receipt['events']],
            targets=current,businessWrites=0,modelCalls=0))
    print(json.dumps(dict(result='PASS_FORENSIC_EXTRACTION',historicalTasks=len(result['v2']),live=args.live),ensure_ascii=False))


if __name__=='__main__':main()
