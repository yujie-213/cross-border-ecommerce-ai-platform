import pytest

from tests.support.b_returns import ReturnERP,SimpleNamespace,SourceReader

def test_monitor_uses_received_returns_and_order_cohort_denominator():
    erp=ReturnERP()
    member=SimpleNamespace(storeName='Owned Store',sku='SKU-KNIT',sourceTenant='1',sourceStore='2',sourceWarehouse='20',warehouseName='WH-A',
        monitor=SimpleNamespace(productId='10',salesIds=tuple(str(o['id']) for o in erp.orders)))
    reader=SourceReader(lambda:erp,{'Owned Store':dict(sourceTenant='1',storeId='2')},'.tmp/source',owned_provider=lambda:[member])

    result=reader.return_analysis('Owned Store',lambda:None,end_date='2026-11-17',window_days=7)

    row=result['monitor'][0]
    assert result['complete'] is True
    assert row['previous']==25 and row['current']==25
    assert row['previousReturnRate']==4.0 and row['currentReturnRate']==24.0
    assert row['previousLowReviews']==2 and row['currentLowReviews']==6
    assert row['previousLowReviewRate']==100.0 and row['currentLowReviewRate']==100.0
    assert row['evaluated'] is True
    assert len(result['items'])==7 and all(item['state']=='received' for item in result['items'])
    assert any('缝线松脱' in item['text'] for item in row['evidenceItems'])


def test_return_draft_authorization_and_refund_without_receipt_do_not_enter_return_rate():
    erp=ReturnERP()
    for row in erp.returns:
        row.update(state='draft',received_at=None)
    erp.returns[0].update(state='authorized',authorized_at='2026-11-17T09:00:00+08:00')
    erp.returns[1].update(state='refunded',refunded_at='2026-11-17T11:00:00+08:00')
    member=SimpleNamespace(storeName='Owned Store',sku='SKU-KNIT',sourceTenant='1',sourceStore='2',sourceWarehouse='20',warehouseName='WH-A',
        monitor=SimpleNamespace(productId='10',salesIds=tuple(str(o['id']) for o in erp.orders)))
    reader=SourceReader(lambda:erp,{'Owned Store':dict(sourceTenant='1',storeId='2')},'.tmp/source',owned_provider=lambda:[member])

    result=reader.return_analysis('Owned Store',lambda:None,end_date='2026-11-17',window_days=7)

    assert len(result['items'])==7
    assert sum(row['currentReturns']+row['previousReturns'] for row in result['monitor'])==0


def test_monitor_uses_order_warehouse_when_same_sku_is_registered_in_multiple_warehouses():
    erp=ReturnERP()
    ids=tuple(str(o['id']) for o in erp.orders)
    members=[SimpleNamespace(storeName='Owned Store',sku='SKU-KNIT',sourceTenant='1',sourceStore='2',
        sourceWarehouse=warehouse,warehouseName=name,monitor=SimpleNamespace(productId='10',salesIds=ids))
        for warehouse,name in [('20','WH-A'),('21','WH-B')]]
    reader=SourceReader(lambda:erp,{'Owned Store':dict(sourceTenant='1',storeId='2')},'.tmp/source',owned_provider=lambda:members)

    result=reader.return_analysis('Owned Store',lambda:None,end_date='2026-11-17',window_days=7)

    assert result['complete'] is True
    assert result['monitor'][0]['previous']==25 and result['monitor'][0]['current']==25
    assert all(item['identity']['warehouseId']=='20' for item in result['items'])


def test_monitor_blocks_evaluation_when_cross_warehouse_order_cannot_be_resolved():
    erp=ReturnERP();erp.orders[0].pop('shipping_warehouse')
    ids=tuple(str(o['id']) for o in erp.orders)
    members=[SimpleNamespace(storeName='Owned Store',sku='SKU-KNIT',sourceTenant='1',sourceStore='2',
        sourceWarehouse=warehouse,warehouseName=name,monitor=SimpleNamespace(productId='10',salesIds=ids))
        for warehouse,name in [('20','WH-A'),('21','WH-B')]]
    reader=SourceReader(lambda:erp,{'Owned Store':dict(sourceTenant='1',storeId='2')},'.tmp/source',owned_provider=lambda:members)

    result=reader.return_analysis('Owned Store',lambda:None,end_date='2026-11-17',window_days=7)

    assert result['complete'] is False
    assert result['monitor'][0]['evaluated'] is False


def test_monitor_does_not_use_receipts_after_the_selected_cutoff():
    erp=ReturnERP()
    for row in erp.returns:row['received_at']='2026-11-18T10:00:00+08:00'
    member=SimpleNamespace(storeName='Owned Store',sku='SKU-KNIT',sourceTenant='1',sourceStore='2',sourceWarehouse='20',warehouseName='WH-A',
        monitor=SimpleNamespace(productId='10',salesIds=tuple(str(o['id']) for o in erp.orders)))
    reader=SourceReader(lambda:erp,{'Owned Store':dict(sourceTenant='1',storeId='2')},'.tmp/source',owned_provider=lambda:[member])
    result=reader.return_analysis('Owned Store',lambda:None,end_date='2026-11-17')
    assert result['monitor'][0]['currentReturns']==0
    assert result['monitor'][0]['previousReturns']==0


def detail_reader(erp):
    member=SimpleNamespace(storeName='Owned Store',sku='SKU-KNIT',sourceTenant='1',sourceStore='2',sourceWarehouse='20',warehouseName='WH-A',
        monitor=SimpleNamespace(productId='10',salesIds=tuple(str(o['id']) for o in erp.orders)))
    return SourceReader(lambda:erp,{'Owned Store':dict(sourceTenant='1',storeId='2')},'.tmp/source',owned_provider=lambda:[member])


def test_analysis_only_reads_detail_for_incomplete_return_projection():
    erp=ReturnERP()
    read,detail=erp.read,erp.detail
    detail_ids=[]

    def read_with_one_summary(path,params,**kwargs):
        if path=='/api/v1/sales-returns' and params['order_id']==26:
            row=erp.returns[1]
            return erp.batch([dict(id=row['id'],order_id=row['order_id'])])
        return read(path,params,**kwargs)

    def record_detail(resource,record_id):
        detail_ids.append(record_id)
        return detail(resource,record_id)

    erp.read=read_with_one_summary
    erp.detail=record_detail
    reader=detail_reader(erp)
    factories=[]
    reader.analysis_factory=lambda:factories.append('analysis') or erp
    reader.factory=lambda:pytest.fail('Analysis should share its reader with review collection')

    result=reader.return_analysis('Owned Store',lambda:None,end_date='2026-11-17')

    assert factories==['analysis']
    assert detail_ids==[902]
    assert result['complete'] and len(result['items'])==7
    assert result['monitor'][0]['currentReturnRate']==24.0


@pytest.mark.parametrize('wrong_identity',[dict(tenant_id=9),dict(order_id=999)])
def test_analysis_excludes_an_out_of_scope_return_summary(wrong_identity):
    erp=ReturnERP()
    read=erp.read

    def read_with_wrong_identity(path,params,**kwargs):
        if path=='/api/v1/sales-returns' and params['order_id']==26:
            return erp.batch([dict(id=902,order_id=26)|wrong_identity])
        return read(path,params,**kwargs)

    erp.read=read_with_wrong_identity
    erp.detail=lambda *_:pytest.fail('Out-of-scope summary should never trigger a detail read')

    result=detail_reader(erp).return_analysis('Owned Store',lambda:None,end_date='2026-11-17')

    assert not result['complete'] and not result['monitor'][0]['evaluated']
    assert all(item['id']!='902' for item in result['items'])


def test_one_return_reads_only_its_detail_order_and_product():
    erp=ReturnERP();calls=[];read=erp.read;detail=erp.detail
    def observed_read(path,params,**kwargs):
        calls.append((path,params));return read(path,params,**kwargs)
    def observed_detail(resource,rid):
        calls.append((resource,rid));return detail(resource,rid)
    erp.read=observed_read;erp.detail=observed_detail
    result=detail_reader(erp).return_detail('Owned Store','902','SKU-KNIT',lambda:None)
    assert result['complete'] and len(result['items'])==1
    assert result['items'][0]['identity']['orderId']=='26'
    assert calls==[('sales-returns','902'),('/api/v1/sales-orders',dict(ids='26')),('/api/v1/products',dict(ids='10'))]


def test_one_return_cannot_admit_an_unregistered_order_or_wrong_identity():
    import pytest
    from commerce_hub.orchestration.service import TaskError
    for field,value,code in [('order_id',999,'SOURCE_NOT_OWNED'),('tenant_id',9,'SOURCE_IDENTITY_MISMATCH')]:
        erp=ReturnERP();erp.returns[1][field]=value
        with pytest.raises(TaskError,match=code):detail_reader(erp).return_detail('Owned Store','902','SKU-KNIT',lambda:None)
    erp=ReturnERP();erp.orders[25]['store_name']='Other Store'
    with pytest.raises(TaskError,match='SOURCE_IDENTITY_MISMATCH'):detail_reader(erp).return_detail('Owned Store','902','SKU-KNIT',lambda:None)


def test_one_return_rechecks_authorization_around_source_io():
    import pytest
    erp=ReturnERP();checks=[]
    def revoked():
        checks.append(True)
        if len(checks)==2:raise PermissionError('revoked')
    with pytest.raises(PermissionError):detail_reader(erp).return_detail('Owned Store','902','SKU-KNIT',revoked)
    assert len(checks)==2
