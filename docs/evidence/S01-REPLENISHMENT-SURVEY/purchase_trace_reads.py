"""Trace approvals/receipts only via contexts of the two independently observed POs."""
import json
from read_only_probe import Probe,ROOT,AUTH_PATH
from dotenv import dotenv_values


def main():
    supplement=sorted((ROOT/'data/private/s01-replenishment-survey').glob('*/supplement.json'))[-1]
    source=json.loads(supplement.read_text(encoding='utf-8'))
    prior=sum(len(json.loads(p.read_text(encoding='utf-8'))['events']) for p in (ROOT/'data/private/s01-replenishment-survey').glob('*/journal.json'))
    p=Probe();p.journal['requestLimit']=80-prior
    v=dotenv_values(ROOT/'.env.erp',interpolate=False)
    st,auth=p.request('POST',AUTH_PATH,dict(appId=v.get('ERP_USERNAME'),appSecret=v.get('ERP_PASSWORD')),'authentication')
    assert st==200
    p.token=auth['data']['access_token'];del v,auth
    st,me=p.request('GET','/api/v1/me',label='identity')
    assert st==200 and me.get('data',me)['tenant_id']==1
    traces=[]
    for record in source['purchases']:
        for st,po in record['details']:
            assert st==200 and record['sku'] in {'YF-SO-QD-S','YF-SO-PZ-M'}
            status,context=p.request('GET',f'/api/v1/record-context/purchase-orders/{po["id"]}',label='po-context-'+record['sku'])
            approvals=[]
            if status==200:
                for link in context.get('related',[]):
                    if link.get('resource')=='approvals':
                        approvals.append(p.request('GET',f'/api/v1/approvals/{link["id"]}',label='approval-'+record['sku']))
            traces.append(dict(sku=record['sku'],purchaseId=po['id'],contextStatus=status,context=context,approvals=approvals))
    (p.out/'purchase-traces.json').write_text(json.dumps(traces,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p.journal['result']='COMPLETED_PURCHASE_TRACE_READS';p.save()
    print(json.dumps(dict(attempts=len(p.journal['events']),cumulativeAttempts=prior+len(p.journal['events']),
        traces=[dict(sku=t['sku'],purchaseId=t['purchaseId'],contextStatus=t['contextStatus'],approvalDetails=len(t['approvals']),
            relatedResources=[dict(resource=r.get('resource'),id=r.get('id')) for r in (t['context'] or {}).get('related',[])]) for t in traces])))


if __name__=='__main__':main()
