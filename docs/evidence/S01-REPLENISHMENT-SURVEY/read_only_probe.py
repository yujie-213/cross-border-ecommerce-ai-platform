"""Explicit survey only: selected teaching SKUs; no runtime integration or business writes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import sys
import time
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from dotenv import dotenv_values
from commerce_hub.adapters.erp import ERPConfig, AUTH_PATH, https_transport

COMPAT = '/erp/sc/routing/restocking/analysis/getSummaryList'
SKUS = ['YF-SO-NG-OS','YF-SO-PZ-L','YF-SO-QD-S','YF-SO-QD-L','YF-SO-PZ-M']
STORE = 'MIMI Apparel US'
GETS = {'/api/v1/me','/api/v1/data-contract','/static/compat-field-catalog.json',
    '/api/v1/store-authorizations','/api/v1/products','/api/v1/listings','/api/v1/inventory',
    '/api/v1/warehouses','/api/v1/replenishment','/api/v1/purchase-orders'}


class Probe:
    def __init__(self):
        self.out = ROOT/'data/private/s01-replenishment-survey'/datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        self.out.mkdir(parents=True, exist_ok=False)
        self.token = ''
        self.config = ERPConfig(timeout=12, interval=.65)
        self.journal = dict(startedAt=datetime.now(timezone.utc).isoformat(), events=[], businessMutations=0, modelCalls=0,
            allowedSkus=SKUS, store=STORE, requestLimit=80, observedHead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
        self.compat_verified = False

    def save(self):
        (self.out/'journal.json').write_text(json.dumps(self.journal, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')

    def request(self, method, path, values=None, label='response'):
        auth = path == AUTH_PATH
        assert method == 'GET' and (path in GETS or re.fullmatch(r'/api/v1/(?:replenishment|record-context/replenishment|record-context/purchase-orders|purchase-orders|approvals)/[1-9][0-9]{0,19}',path)) or method == 'POST' and (auth or path == COMPAT and self.compat_verified)
        values = values or {}
        for attempt in range(2 if not auth else 1):
            assert len(self.journal['events']) < self.journal['requestLimit'], 'BOUNDED_REQUEST_LIMIT'
            e = dict(method=method,path=path,parameters=None if auth else values, label=label,attempt=attempt+1,at=datetime.now(timezone.utc).isoformat())
            self.journal['events'].append(e); self.save()
            target = path+('?' + urlencode(values,doseq=True) if method == 'GET' and values else '')
            body = json.dumps(values,ensure_ascii=False).encode() if method == 'POST' else None
            headers = {'Accept':'application/json'}
            if method == 'POST': headers['Content-Type']='application/json'
            if not auth: headers['Authorization']='Bearer '+self.token
            time.sleep(.65 if not attempt else 2)
            start = time.monotonic()
            try:
                status,raw = https_transport(method,target,headers,body,self.config)
                e['httpStatus']=status
                if not auth:
                    p=self.out/f'{len(self.journal["events"]):03d}-{label}.json'
                    p.write_bytes(raw)
                    e.update(privateResponse=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest())
                try: data=json.loads(raw)
                except ValueError: data=None
            except Exception as exc:
                e.update(errorType=type(exc).__name__)
                status,data=None,None
            e['elapsedMs']=round((time.monotonic()-start)*1000); self.save()
            if not attempt and not auth and (status in {503,504} or status is None): continue
            return status,data

    def rows(self,path,params,label,*,method='GET',size=10,pages=2):
        rows=[]; total=None; seen=set()
        for page in range(pages):
            q=dict(params,offset=len(rows),**({'limit':size} if method=='GET' else {'length':size}))
            st,data=self.request(method,path,q,label+f'-p{page}')
            if st != 200 or not isinstance(data,dict):return dict(status=st,complete=False,total=total,rows=rows,error='HTTP_OR_ENVELOPE')
            if method=='GET':items,count=data.get('items'),data.get('total')
            else:
                if data.get('code') not in {0,200,'0','200'}:return dict(status=st,complete=False,rows=rows,error='BUSINESS_ENVELOPE')
                items,count=data.get('data'),data.get('total')
                if isinstance(items,dict):count,items=items.get('total',count),items.get('list')
            if not isinstance(items,list) or type(count) is not int or count<0 or len(items)>size:
                return dict(status=st,complete=False,rows=rows,error='INVALID_PAGE')
            if total is not None and count != total:return dict(status=st,complete=False,rows=rows,error='TOTAL_DRIFT')
            total=count
            for item in items:
                sig=json.dumps(item,sort_keys=True)
                if sig in seen:return dict(status=st,complete=False,rows=rows,error='REPEATED_ROW')
                seen.add(sig)
            rows.extend(items)
            if len(rows)==total:return dict(status=st,complete=True,total=total,rows=rows,pages=page+1)
            if not items or len(rows)>total:return dict(status=st,complete=False,total=total,rows=rows,error='INCOMPLETE_PAGE')
        return dict(status=st,complete=False,total=total,rows=rows,error='BOUNDED_PAGE_LIMIT')

    def main(self):
        v=dotenv_values(ROOT/'.env.erp',interpolate=False)
        st,auth=self.request('POST',AUTH_PATH,dict(appId=v.get('ERP_USERNAME'),appSecret=v.get('ERP_PASSWORD')),'authentication')
        assert st==200 and isinstance(auth.get('data',{}).get('access_token'),str),'AUTH_FAILED'
        self.token=auth['data']['access_token']; del v,auth
        st,me=self.request('GET','/api/v1/me',label='identity')
        assert st==200 and isinstance(me,dict),'IDENTITY_UNVERIFIED'
        identity=me.get('data',me)
        tenant=identity.get('tenant_id'); assert tenant is not None,'TENANT_UNKNOWN'
        st,contract=self.request('GET','/api/v1/data-contract',label='data-contract')
        st,catalog=self.request('GET','/static/compat-field-catalog.json',label='field-catalog')
        entry=catalog.get('endpoints',{}).get(COMPAT,{}) if isinstance(catalog,dict) else {}
        assert st==200 and entry.get('operation_class')=='query','POST_READONLY_UNVERIFIED'
        self.compat_verified=True
        stores=self.rows('/api/v1/store-authorizations',dict(field='store_name',q=STORE,match='exact'),'store',size=5)
        assert stores['complete'] and len(stores['rows'])==1,'STORE_RELATION_UNVERIFIED'
        store=stores['rows'][0]
        assert store['store_name']==STORE and str(store['tenant_id'])==str(tenant),'STORE_TENANT_MISMATCH'
        sid=store['id']
        findings=dict(identity=identity,store=store,postReadonlyContract=entry,skus=[],businessMutations=0,modelCalls=0)
        for sku in SKUS:
            exact=dict(field='sku',q=sku,match='exact')
            r=self.rows('/api/v1/replenishment',dict(exact,store_name=STORE),'recommendation-'+sku,size=5)
            assert all(x.get('sku')==sku and x.get('store_name')==STORE and str(x.get('tenant_id'))==str(tenant) for x in r['rows']),'SUGGESTION_SCOPE_MISMATCH'
            product=self.rows('/api/v1/products',exact,'product-'+sku,size=5)
            listing=self.rows('/api/v1/listings',dict(exact,store_name=STORE),'listing-'+sku,size=5)
            stock=self.rows('/api/v1/inventory',dict(exact,store_id=sid,view='full'),'stock-'+sku,size=10)
            assert all(x.get('sku')==sku and str(x.get('tenant_id'))==str(tenant) for x in product['rows']),'PRODUCT_SCOPE_MISMATCH'
            assert all(x.get('sku')==sku and x.get('store_name')==STORE and str(x.get('tenant_id'))==str(tenant) for x in listing['rows']),'LISTING_SCOPE_MISMATCH'
            assert all(x.get('sku')==sku and str(x.get('store_id'))==str(sid) and str(x.get('tenant_id'))==str(tenant) for x in stock['rows']),'STOCK_SCOPE_MISMATCH'
            detail=[];contexts=[]
            for row in r['rows'][:2]:
                detail.append(self.request('GET',f'/api/v1/replenishment/{row["id"]}',label='detail-'+sku))
                contexts.append(self.request('GET',f'/api/v1/record-context/replenishment/{row["id"]}',label='context-'+sku))
            findings['skus'].append(dict(sku=sku,replenishment=r,product=product,listing=listing,inventory=stock,details=detail,contexts=contexts))
            (self.out/'findings.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        # Explicitly scoped batch, small pages; never enumerate an unrestricted store/global list.
        findings['compatBatch']=self.rows(COMPAT,dict(sid_list=[sid],data_type=2,msku_list=SKUS),'compat-selected',method='POST',size=2,pages=3)
        findings['completedAt']=datetime.now(timezone.utc).isoformat()
        (self.out/'findings.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        self.journal['result']='COMPLETED_READS';self.save()
        print(json.dumps(dict(privateRun=self.out.relative_to(ROOT).as_posix(),result='COMPLETED_READS',
            requestAttempts=len(self.journal['events']),samples=[dict(sku=x['sku'],total=x['replenishment'].get('total'),complete=x['replenishment']['complete']) for x in findings['skus']],
            compatTotal=findings['compatBatch'].get('total'),compatComplete=findings['compatBatch']['complete']),ensure_ascii=True))


if __name__=='__main__':
    probe=Probe()
    try:probe.main()
    except Exception as exc:
        probe.journal.update(result='STOPPED',errorType=type(exc).__name__);probe.save()
        print(json.dumps(dict(result='STOPPED',errorType=type(exc).__name__,privateRun=probe.out.relative_to(ROOT).as_posix())))
        raise SystemExit(1)
