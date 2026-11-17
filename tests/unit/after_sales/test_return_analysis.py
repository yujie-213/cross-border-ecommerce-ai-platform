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
