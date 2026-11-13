"""Fixture tests for the online port. These are never evidence of real ERP access."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from commerce_hub.adapters.erp import ERPConfig, TeachingERPReader
from commerce_hub.data.sync.online import OnlineMapping,collect,MODE
from commerce_hub.data.projection.online import observed
from commerce_hub.data.quality.online import capture_online,verify_asset
from commerce_hub.scenarios.s01_backend.online import OnlineS01Handler

def mapping():
    return OnlineMapping(scope=dict(tenantId='online-fixture',storeIds=['store-fixture'],warehouseIds=['warehouse-fixture'],
        canonicalSkuIds=['sku-fixture'],fields=['quantity']),sku='SKU-TEST',sourceTenant='1',sourceStore='2',sourceWarehouse='3',
        storeName='store',warehouseName='warehouse')

def pages():
    common=dict(id=1,tenant_id=1,sku='SKU-TEST',updated_at='2026-11-13T00:00:00Z')
    return dict(inventory=[dict(common,wid=3,store_id=2,quantity=60,available=50)],products=[common],
        **{'store-authorizations':[dict(common,id=2)],'warehouses':[dict(common,id=3)],
        'listings':[dict(common,store_name='store')],'sales-orders':[],'purchase-orders':[],'supplier-quotes':[]})

def acquire(*,data=None,status=200):
    data=data or pages()
    def transport(method,path,headers,body,config):
        key=path.split('?')[0].split('/')[-1]
        rows=data.get(key,[])
        response=dict(items=rows,total=len(rows)) if method=='GET' else dict(code=0,data=[],total=0)
        return status,json.dumps(response).encode()
    reader=TeachingERPReader(ERPConfig(access_token='fixture-only',max_requests=48),transport=transport,sleeper=lambda _:None)
    context=SimpleNamespace(check=lambda:None)
    captures,receipt=collect(reader,mapping(),context,'a'*32)
    projection,verified=observed(captures,mapping(),receipt)
    return capture_online(projection,receipt,verified),captures

def test_online_observations_are_freshly_collected_and_never_admitted_by_names():
    asset,captures=acquire()
    assert asset['manifest']['mappingVerified'] is True
    assert captures['sales']['complete'] is True
    result=OnlineS01Handler.rules_result(asset)
    assert result.completeness=='BLOCKED'
    assert result.dataReport['supplyDemand']['baseline'] is None
    assert result.dataReport['supplyDemand']['candidates']==[]
    assert result.analysisReport['ai']['status']=='NOT_ATTEMPTED'
    assert 'NET_AVAILABLE_UNCONFIRMED' in {i['code'] for i in result.dataReport['quality']}

@pytest.mark.parametrize('status',[503,401,302])
def test_online_http_failure_preserves_error_never_zero_or_fixed_fallback(status):
    asset,captures=acquire(status=status)
    assert asset['manifest']['mappingVerified'] is False
    assert not asset['observationProjection']['domains'][1]['measurements']
    assert captures['inventory']['error']
    assert asset['manifest']['acquisition']['interfaces']['inventory']['complete'] is False

def test_foreign_source_identity_hides_quantities_and_blocks():
    data=pages();data['inventory'][0]['store_id']=999
    asset,_=acquire(data=data)
    assert not asset['manifest']['mappingVerified']
    assert asset['observationProjection']['domains'][1]['measurements']==[]

def test_manifest_binds_acquisition_and_projection():
    asset,_=acquire();altered=deepcopy(asset);altered['manifest']['acquisition']['acquisitionId']='b'*32
    with pytest.raises(ValueError):verify_asset(altered)
    other=deepcopy(asset);other['observationProjection']['domains'][1]['measurements'][0]['value']='99'
    with pytest.raises(ValueError):verify_asset(other)

def test_online_parameters_reject_fixed_facts_and_cross_scope_before_network():
    handler=OnlineS01Handler([mapping()],lambda *_:pytest.fail('No network during validation/options'))
    handler.validate_scope(dict(inputMode=MODE),mapping().scope)
    assert handler.options('other')==[]
    assert 'packageRef' not in handler.options('online-fixture')[0]
    for parameters in [dict(packageRef='x'),dict(inputMode=MODE,packageRef='x'),dict(inputMode=MODE,inventory=[])]:
        with pytest.raises(ValueError):handler.validate(parameters)
    with pytest.raises(ValueError):handler.validate_scope(dict(inputMode=MODE),dict(mapping().scope,storeIds=['other']))
