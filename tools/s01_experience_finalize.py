"""Complete the existing owned teaching batch: master data and end-to-end reconciliation.

Explicit --execute-live only. No new purchases, approvals, receipts, monetary
changes to posted sales, database writes to ERP, or external notifications.
"""
from pathlib import Path
from decimal import Decimal
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from tools.s01_experience_dataset import Importer, Client, PRIVATE, BATCH, NATURE, canonical_bytes, DatasetError, scenarios


# Fictional brand, ordinary merchandise names. Test conclusions belong in audit
# notes, not in names or categories. Dimensions are cm and weights kg unless noted.
PROFILES = {
 'HLX-USB-STABLE': dict(name='USB-C 编织充电线 1m 深灰', model='HC60-1M-GY', category='数码配件', material='尼龙编织 / 铝合金接头', price=9.99, cost=2.40, size=('100','0.4','0.4'), weight='0.035', carton=(24,18,8,.35), spec='USB-C to USB-C；60W；1m；深灰色'),
 'HLX-TOTE-SAFE': dict(name='帆布拉链收纳袋 米白色', model='CT28-IV', category='家居收纳', material='12安帆布 / 金属拉链', price=14.90, cost=3.10, size=('28','20','8'), weight='0.180', carton=(32,24,12,.95), spec='28×20×8cm；米白色；单主仓拉链'),
 'HLX-LAMP-SURGE': dict(name='USB 调光阅读灯 暖白色', model='DL5-WH', category='家居照明', material='ABS / 铝合金', price=19.90, cost=5.20, size=('12','10','32'), weight='0.310', carton=(36,28,18,1.80), spec='USB 5V供电；5W；三档调光；暖白色；无电池'),
 'HLX-CUP-SLOW': dict(name='304不锈钢随行杯 420ml 森林绿', model='TC420-GN', category='家居生活', material='304不锈钢 / PP杯盖 / 硅胶密封圈', price=16.90, cost=4.50, size=('7','7','18'), weight='0.240', carton=(20,20,22,1.30), spec='420ml；森林绿；旋盖；手洗'),
 'HLX-MAT-SPARSE': dict(name='软木双面桌垫 60×30cm 原木色', model='DM6030-NT', category='办公用品', material='天然软木 / PU', price=13.90, cost=3.30, size=('60','30','0.2'), weight='0.280', carton=(34,18,18,1.50), spec='60×30cm；原木色；软木与PU双面'),
 'HLX-STAND-NEW': dict(name='铝合金折叠手机支架 银色', model='PS90-SL', category='数码配件', material='铝合金 / 硅胶防滑垫', price=12.90, cost=3.60, size=('9','7','12'), weight='0.150', carton=(24,18,12,.90), spec='4–7英寸手机；双轴折叠；银色'),
 'HLX-CASE-NOQUOTE': dict(name='双层数码收纳包 藏蓝色', model='EC22-NV', category='箱包配件', material='涤纶 / EVA夹层', price=15.90, cost=4.00, size=('22','15','6'), weight='0.190', carton=(32,24,18,1.10), spec='22×15×6cm；双层网袋；藏蓝色'),
 'HLX-HUB-PENDING': dict(name='USB-C 四口扩展坞 太空灰', model='UH4-GY', category='电脑配件', material='铝合金外壳 / TPE线材', price=24.90, cost=6.80, size=('10','3','1.2'), weight='0.065', carton=(24,18,8,.50), spec='USB-C输入；4个USB-A数据口；不含充电功能；太空灰'),
}


def reconcile_inventory(member, rows):
    """Verify unique posted movements, continuity and independently read balances."""
    ids = [r['id'] for r in rows]
    if len(set(ids)) != len(ids): raise DatasetError('DUPLICATE_LEDGER_EVENT')
    quantity = available = member['initial']
    actual_by_sale = {}
    for r in sorted(rows, key=lambda r: r['id']):
        if (str(r['inventory_id']) != str(member['inventory']['id']) or
            r['sku'] != member['product']['sku'] or r['warehouse_name'] != member['warehouse']['name'] or
            r['resource'] != 'outbound-orders' or r.get('operation') != 'post' or r.get('reverses_id') is not None or
            r['before_quantity'] != quantity or r['before_available'] != available or
            r['after_quantity'] != quantity + r['delta_quantity'] or r['after_available'] != available + r['delta_available'] or
            r['delta_quantity'] >= 0 or r['delta_quantity'] != r['delta_available']):
            raise DatasetError('LEDGER_RELATION_OR_CONTINUITY_FAILED')
        quantity = r['after_quantity']; available = r['after_available']
        actual_by_sale[str(r['record_id'])] = actual_by_sale.get(str(r['record_id']), 0) - r['delta_quantity']
    if actual_by_sale != member['expectedOutboundQuantities']:
        raise DatasetError('SALE_OUTBOUND_QUANTITY_MISMATCH')
    inv = member['finalInventory']
    if quantity != member['expectedAvailable'] or available != quantity or inv['quantity'] != quantity or inv['available'] != available:
        raise DatasetError('FINAL_BALANCE_MISMATCH')
    return dict(opening=member['initial'], sales=sum(actual_by_sale.values()), closing=quantity,
                movementCount=len(rows), eventIds=ids, relationVerified=True)


class Finalizer(Importer):
    def __init__(self):
        super().__init__()
        owner=self
        class EnrichmentClient(Client):
            def _allow(self,method,path,*,auth):
                parts=path.split('/')
                if method=='GET' and len(parts)==5 and parts[3] in {'outbound-orders','finance'}:return
                if method=='PUT' and path in owner.allowed_updates:return
                return super()._allow(method,path,auth=auth)
        self.allowed_updates=set()
        self.client=EnrichmentClient()

    def original(self,resource,key):
        v=self.journal['operations'][resource+':'+key]
        if v['state']!='VERIFIED':raise DatasetError('ORIGINAL_BATCH_NOT_VERIFIED')
        return v['record']

    def update(self,resource,record,values):
        path='/api/v1/'+resource+'/'+str(record['id']);self.allowed_updates.add(path)
        # A durable exact ID and original creation receipt confer ownership.
        current=self.client.request('GET',path);current=current.get('data',current)
        if current.get('tenant_id')!=1 or current.get('id')!=record['id']:raise DatasetError('UPDATE_OWNERSHIP_MISMATCH')
        updates=self.journal.setdefault('enrichment',{})
        fp=hashlib.sha256(canonical_bytes(values)).hexdigest()
        op=resource+':'+str(record['id'])+':'+fp[:12];prior=updates.get(op)
        if prior and prior['fingerprint']!=fp:raise DatasetError('ENRICHMENT_PAYLOAD_CHANGED')
        if not all(current.get(k)==v for k,v in values.items()):
            if prior:raise DatasetError('UNKNOWN_UPDATE_REQUIRES_READBACK_NO_REPLAY')
            updates[op]=dict(state='SENDING',fingerprint=fp,before=current,desired=values);self.save()
            try:self.client.request('PUT',path,values)
            except Exception as error:
                updates[op]['state']='REJECTED' if isinstance(error,DatasetError) and error.status and 400<=error.status<500 else 'UNKNOWN'
                updates[op]['httpStatus']=getattr(error,'status',None);self.save();raise
            current=self.client.request('GET',path);current=current.get('data',current)
            if not all(current.get(k)==v for k,v in values.items()):raise DatasetError('ENRICHMENT_READBACK_MISMATCH')
        updates[op]=dict(prior or updates.get(op) or {},state='VERIFIED',fingerprint=fp,record=current)
        self.save();print(json.dumps(dict(enriched=resource,id=record['id'])),flush=True)
        return current

    def quote(self,record,profile):
        op='quote:'+str(record['id']);updates=self.journal.setdefault('enrichment',{});prior=updates.get(op)
        rows=self.client.lookup('supplier-quotes','quote_no',record['quote_no'])
        if len(rows)!=1:raise DatasetError('QUOTE_OWNERSHIP_MISMATCH')
        current=rows[0]
        if any(current[k]!=record[k] for k in ['quote_no','sku','product_id','supplier_id','supplier_code']):raise DatasetError('QUOTE_PARENT_RELATION_MISMATCH')
        # Quote upsert appends an immutable version with a NEW row ID. Bind the
        # independently read version, not the superseded creation row.
        if current['id']!=record['id'] and not (prior and (current['id']==prior.get('record',{}).get('id') or
                prior['state'] in {'SENDING','UNKNOWN'} and current['version']==prior['before']['version']+1)):
            raise DatasetError('QUOTE_VERSION_NOT_OWNED')
        desired=dict(quote_no=record['quote_no'],supplier_code=record['supplier_code'],sku=record['sku'],currency='USD',
            unit_price=f"{profile['cost']:.2f}",minimum_quantity=8,lead_days=2,valid_from='2026-11-14',valid_to='2027-11-14',
            enabled='NOQUOTE' not in record['sku'],request_key=BATCH+'-ENRICH-Q-'+str(record['id']))
        fp=hashlib.sha256(canonical_bytes(desired)).hexdigest()
        if prior and prior['fingerprint']!=fp:raise DatasetError('QUOTE_ENRICHMENT_PAYLOAD_CHANGED')
        if not all(current.get(k)==v for k,v in desired.items() if k!='request_key'):
            if prior:raise DatasetError('QUOTE_UNKNOWN_REQUIRES_ORIGINAL_KEY_READBACK')
            updates[op]=dict(state='SENDING',fingerprint=fp,before=current);self.save()
            try:self.client.request('POST','/api/v1/supplier-quotes',dict(desired,expected_version=current['version']))
            except Exception:
                updates[op]['state']='UNKNOWN';self.save();raise
            current=self.client.lookup('supplier-quotes','quote_no',record['quote_no'])[0]
        if not all(current.get(k)==v for k,v in desired.items() if k!='request_key') or current['product_name']!=profile['name']:
            raise DatasetError('QUOTE_ENRICHMENT_READBACK_MISMATCH')
        updates[op]=dict(prior or updates.get(op) or {},state='VERIFIED',fingerprint=fp,record=current);self.save()
        return current

    def execute(self):
        self.preflight()
        captured=self.journal.get('verificationCaptures')
        if captured:
            return self.complete(captured['members'],captured['ledger'],captured['links'])
        supplier=self.original('suppliers',BATCH+'-SUP')
        # Referenced supplier names are business keys in this ERP. Preserve the
        # original identity and enrich only permitted descriptive fields.
        supplier=self.update('suppliers',supplier,dict(level='合格',contact='教学供应服务组',phone='',purchase_user='海岚采购组',status_text='正常'))
        stores=[self.original('store-authorizations',BATCH+'-'+c) for c in ['EAST','WEST']]
        warehouses=[self.original('warehouses',BATCH+'-'+c) for c in ['EAST','WEST']]
        for w in warehouses:self.update('warehouses',w,dict(manager='海岚仓储组'))
        members=[]
        for i,s in enumerate(scenarios()):
            sku=s['sku'];p=PROFILES[sku];base=self.original('products',sku)
            official=dict(currency='USD',cg_product_length=p['size'][0],cg_product_width=p['size'][1],cg_product_height=p['size'][2],
                cg_product_net_weight=str(Decimal(p['weight'])*1000),cg_opt_username='海岚采购组',purchase_remark='教学仿真；'+s['scene'],
                )
            # Do not invent official platform IDs, certificates or customs codes.
            length,width,height,weight=p['carton']
            product=self.update('products',base,dict(name=p['name'],model=p['model'],category=p['category'],status='在售',
                price=p['price'],cost=p['cost'],product_type='普通商品',unit='piece',material=p['material'],brand='海岚优选',
                tag=BATCH,developer='海岚产品组',owner='海岚运营组',supplier_name=supplier['name'],moq=8,procurement_lead_days=2,
                default_carton_qty=4,carton_length=length,carton_width=width,carton_height=height,carton_weight=weight,
                origin_country='CN',customs_name=p['name'],customs_price=p['cost'],qc_method='外观与功能抽检',
                qc_standard='教学检验规范：外观无破损、规格一致、功能正常；不表示真实认证',
                description=p['spec']+'。'+NATURE+'；'+BATCH+'；历史教学促销成交价10 USD/件，当前挂牌价另列；海关编码未核定。',official_attributes=official))
            quote=self.quote(self.original('supplier-quotes',BATCH+'-Q-'+str(i+1)),p)
            for si in ([0,1] if i==0 else [0]):
                inv=self.original('inventory',BATCH+'-I-'+str(i+1)+'-'+str(si))
                listing=self.original('listings',BATCH+'-L-'+str(i+1)+'-'+str(si))
                balance=self.client.request('GET','/api/v1/inventory/'+str(inv['id']));balance=balance.get('data',balance)
                expected=120 if si else s['available']
                if balance['quantity']!=expected or balance['available']!=expected:raise DatasetError('CURRENT_BALANCE_MISMATCH')
                # Sync the listing's sellable snapshot only after the independent
                # balance read; never alter the authoritative inventory balance.
                listing=self.update('listings',listing,dict(title=p['name'],price=p['price'],stock=balance['available']))
                members.append(dict(scenario=s,scopeIndex=si,store=stores[si],warehouse=warehouses[si],product=product,quote=quote,
                    inventory=inv,listing=listing,initial=self.journal['operations']['inventory:'+inv['batch_no']]['payload']['quantity'],
                    expectedAvailable=120 if si else s['available'],salesIds=[],expectedOutboundQuantities={}))
        # Read the exact original sales, payment voucher, outbound and movement
        # IDs. This avoids the ERP's slow broad SKU ledger query entirely.
        ledger=[];links=[]
        sales=[v['record'] for k,v in self.journal['operations'].items() if k.startswith('sales-orders:') and v['state']=='VERIFIED']
        for sale in sales:
            sid=str(sale['id']);actual=self.client.request('GET','/api/v1/sales-orders/'+sid);actual=actual.get('data',actual)
            matching=[m for m in members if m['store']['store_name']==sale['store_name'] and m['warehouse']['name']==sale['shipping_warehouse']]
            if not matching or any(actual.get(k)!=sale.get(k) for k in ['order_sn','store_name','shipping_warehouse','currency','amount','item_list','order_time']):raise DatasetError('ORIGINAL_SALES_DRIFT')
            if '-UNPAID' in sale['order_sn']:
                wf=self.client.request('GET','/api/v1/sales-workflow/'+sid)['data']
                if (not wf['local_only'] or wf['state']!='unpaid' or wf.get('finance_id') or wf.get('outbound_id') or wf.get('shipments')
                    or actual['payment_status']!='待支付' or actual['fulfillment_status']!='待审核'):
                    raise DatasetError('UNPAID_SCENARIO_DRIFT')
                next(m for m in matching if m['product']['sku']=='HLX-HUB-PENDING')['salesIds'].append(sid)
                continue
            wf=self.client.request('GET','/api/v1/sales-workflow/'+sid);wf=wf['data']
            if not wf['local_only'] or wf['state']!='shipped' or actual['payment_status']!='已支付' or actual['fulfillment_status']!='已发货':raise DatasetError('SALE_WORKFLOW_INCOMPLETE')
            total=sum(Decimal(str(x['unit_price']))*x['quantity'] for x in actual['item_list'])
            if total!=Decimal(str(actual['amount'])) or total!=Decimal(wf['paid_amount']) or wf['currency']!=actual['currency']:raise DatasetError('SALE_PAYMENT_AMOUNT_MISMATCH')
            finance=self.client.request('GET','/api/v1/finance/'+str(wf['finance_id']));finance=finance.get('data',finance)
            # ERP vouchers reference the sales order; the idempotency payment
            # reference belongs to the workflow, linked by its finance_id.
            if finance['reference_no']!=sale['order_sn'] or Decimal(str(finance['amount']))!=total or finance['currency']!=wf['currency']:raise DatasetError('PAYMENT_VOUCHER_MISMATCH')
            if len(wf['shipments'])!=1:raise DatasetError('UNEXPECTED_SHIPMENT_COUNT')
            ship=wf['shipments'][0];oid=str(ship['outbound_id'])
            out=self.client.request('GET','/api/v1/outbound-orders/'+oid);out=out.get('data',out)
            expected={x['sku']:x['quantity'] for x in sale['item_list']}
            if ({x['sku']:x['quantity'] for x in out['item_list']}!=expected or out['warehouse_name']!=sale['shipping_warehouse'] or out['quantity']!=sum(expected.values())):raise DatasetError('OUTBOUND_SALES_RELATION_MISMATCH')
            cap=self.client.request('GET','/api/v1/stock/ledger',dict(resource='outbound-orders',record_id=int(oid),limit=20,offset=0))
            if cap['total']!=len(cap['items']) or len(cap['items'])!=len(expected):raise DatasetError('EXACT_OUTBOUND_LEDGER_INCOMPLETE')
            ledger+=cap['items'];links.append(dict(saleId=sid,financeId=str(wf['finance_id']),outboundId=oid,total=str(total)))
            for m in matching:
                sku=m['product']['sku']
                if sku in expected:
                    m['salesIds'].append(sid);m['expectedOutboundQuantities'][oid]=expected[sku]
        self.journal['verificationCaptures']=dict(members=members,ledger=ledger,links=links);self.save()
        return self.complete(members,ledger,links)

    def complete(self,members,ledger,links):
        for m in members:
            inv=self.client.request('GET','/api/v1/inventory/'+str(m['inventory']['id']));m['finalInventory']=inv.get('data',inv)
            rows=[r for r in ledger if str(r['inventory_id'])==str(m['inventory']['id'])]
            m['reconciliation']=reconcile_inventory(m,rows);m['ledger']=rows
        self.journal.update(members=members,workflowLinks=links,state='INDEPENDENTLY_VERIFIED');self.save()
        self.register(members)
        print(json.dumps(dict(masterDataComplete=True,verifiedSales=len(links),verifiedMovements=len(ledger),newScopes=len(members))),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-live',action='store_true');args=parser.parse_args()
    if not args.execute_live:
        print(json.dumps(dict(mode='PLAN_ONLY_NO_NETWORK',products=list(PROFILES),purchaseWrites=False)));raise SystemExit(0)
    try:Finalizer().execute()
    except Exception as e:
        print(json.dumps(dict(status='STOPPED',error=e.code if isinstance(e,DatasetError) else type(e).__name__,httpStatus=getattr(e,'status',None))),flush=True);raise SystemExit(1) from None
