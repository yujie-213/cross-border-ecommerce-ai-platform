"""Follow selected observed IDs and SKU business keys only; no business mutations."""
import json
from pathlib import Path
from read_only_probe import Probe, ROOT, SKUS, STORE, COMPAT, AUTH_PATH
from dotenv import dotenv_values


def main():
    source = sorted((ROOT/'data/private/s01-replenishment-survey').glob('*/findings.json'))[-1]
    initial=json.loads(source.read_text(encoding='utf-8'))
    p=Probe()
    v=dotenv_values(ROOT/'.env.erp',interpolate=False)
    st,auth=p.request('POST',AUTH_PATH,dict(appId=v.get('ERP_USERNAME'),appSecret=v.get('ERP_PASSWORD')),'authentication')
    assert st==200
    p.token=auth['data']['access_token'];del v,auth
    st,me=p.request('GET','/api/v1/me',label='identity')
    identity=me.get('data',me)
    assert st==200 and identity['tenant_id']==initial['identity']['tenant_id']
    p.compat_verified=initial['postReadonlyContract']['operation_class']=='query'
    sid=initial['store']['id']
    result=dict(sourceRun=source.parent.relative_to(ROOT).as_posix(),businessMutations=0,modelCalls=0)
    ids=[x['replenishment']['rows'][0]['id'] for x in initial['skus']]
    result['batchRest']=p.rows('/api/v1/replenishment',dict(ids=','.join(map(str,ids)),store_name=STORE),'batch-rest',size=2,pages=3)
    assert result['batchRest']['complete'] and {r['id'] for r in result['batchRest']['rows']}==set(ids)
    # Remove potentially wrong MSKU assumptions, still limit to the observed store and two rows.
    result['compatStoreMSKU']=p.rows(COMPAT,dict(sid_list=[sid],data_type=2),'compat-store-msku',method='POST',size=2,pages=1)
    result['compatStoreASIN']=p.rows(COMPAT,dict(sid_list=[sid],data_type=1),'compat-store-asin',method='POST',size=2,pages=1)
    warehouse_ids=sorted({r['wid'] for s in initial['skus'] for r in s['inventory']['rows']})
    result['warehouses']=p.rows('/api/v1/warehouses',dict(ids=','.join(map(str,warehouse_ids))),'warehouse',size=5)
    result['purchases']=[]
    for sku in SKUS:
        # Contains query on the selected SKU, never an unrestricted PO enumeration.
        batch=p.rows('/api/v1/purchase-orders',dict(q=sku),'purchase-'+sku,size=5,pages=2)
        assert all(str(r['tenant_id'])==str(identity['tenant_id']) for r in batch['rows'])
        details=[]
        for row in batch['rows'][:3]:
            if any(l.get('sku')==sku for l in row.get('item_list',[])):
                details.append(p.request('GET',f'/api/v1/purchase-orders/{row["id"]}',label='po-detail-'+sku))
        result['purchases'].append(dict(sku=sku,queryMode='q contains SKU (not proof of exhaustive SKU-line discovery)',batch=batch,details=details))
    row=next(x for x in initial['skus'] if x['sku']=='YF-SO-QD-S')['replenishment']['rows'][0]
    result['qdSourcePlan']=p.rows('/api/v1/purchase-orders',dict(field='source_plan_no',q=row['recommendation_no'],match='exact'),'qd-source-plan',size=5)
    result['repeatedRecommendations']=[]
    for s in initial['skus']:
        row=s['replenishment']['rows'][0]
        st,value=p.request('GET',f'/api/v1/replenishment/{row["id"]}',label='repeat-'+s['sku'])
        result['repeatedRecommendations'].append(dict(sku=s['sku'],status=st,unchanged=value==row,record=value))
    (p.out/'supplement.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p.journal['result']='COMPLETED_SUPPLEMENTAL_READS';p.save()
    print(json.dumps(dict(privateRun=p.out.relative_to(ROOT).as_posix(),attempts=len(p.journal['events']),
        batchRestTotal=result['batchRest']['total'],batchRestPages=result['batchRest'].get('pages'),
        compat=[{k:v.get(k) for k in ['status','total','complete','error']} for v in [result['compatStoreMSKU'],result['compatStoreASIN']]],
        purchases=[dict(sku=x['sku'],total=x['batch'].get('total'),details=len(x['details'])) for x in result['purchases']])))


if __name__=='__main__':main()
