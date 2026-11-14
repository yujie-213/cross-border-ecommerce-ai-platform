from copy import deepcopy
import pytest
from tests.support.admission_runtime import AdmissionERP
from tests.support.v2 import MemoryCheckpoint
from commerce_hub.data.sync.v2_catalog import collect_catalog
from commerce_hub.data.projection.v2 import entities
from commerce_hub.scenarios.s01_v2.analysis import analyze,statistics
from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService


def result(tmp_path,monkeypatch,*,fail_ledger=False):
    import commerce_hub.data.sync.v2 as v2
    monkeypatch.setattr(v2,'now',lambda:'2026-11-14T06:00:05+00:00')
    erp=AdmissionERP();reader=erp.reader(tmp_path)
    if fail_ledger:
        original=reader.resource
        def resource(name,*args,**kwargs):
            if name.startswith('stock-scope-'):return dict(rows=[],complete=False,error='ERP_TIMEOUT')
            return original(name,*args,**kwargs)
        reader.resource=resource
    cat=collect_catalog(reader,'1');entity=entities(cat,'1')[0]
    return analyze(cat,entity,reader,opening_binding=erp.mapping),erp


@pytest.mark.parametrize('fail_ledger',[False,True])
def test_reference_is_useful_but_never_a_procurement_quantity(tmp_path,monkeypatch,fail_ledger):
    r,erp=result(tmp_path,monkeypatch,fail_ledger=fail_ledger)
    assert r['analysisState']==r['sourceGrade']=='HISTORICAL_REFERENCE'
    assert r['inventory']['available']==6 and r['demandWindow']['referenceDays']==7
    assert r['demandWindow']['validDays']==(0 if fail_ledger else 6)
    assert r['quantity'] is None and r['ruleResult'] is None and not r['procurementEligibility']['eligible']
    with pytest.raises(Exception,match='REQUISITION_SOURCE_NOT_ELIGIBLE'):
        V2RequisitionService.validate_quantity(dict(dataReport=dict(item=r)),48,'manual')
    assert erp.mutations==0


def test_reference_counts_do_not_rewrite_old_report_summary(tmp_path,monkeypatch):
    r,_=result(tmp_path,monkeypatch);s=statistics([r])
    assert s['historicalReference']==1 and s['coverage']==1 and s['unanalyzable']==0
    old=deepcopy(r);old.update(analysisState='UNANALYZABLE',sourceGrade='UNAVAILABLE')
    assert 'historicalReference' not in statistics([old]) and statistics([old])['coverage']==0


def test_stock_pages_are_small_and_original_request_budget_survives(tmp_path):
    erp=AdmissionERP();cp=MemoryCheckpoint();r=erp.reader(tmp_path,cp)
    r.authenticate('1');r.resource('ledger','/api/v1/stock/ledger',dict(sku=erp.mapping.sku,warehouse_name=erp.mapping.warehouseName))
    assert next(params for _,path,params in erp.calls if path=='/api/v1/stock/ledger')['limit']=='25'
    count=r.state['requestCount'];resumed=erp.reader(tmp_path,cp)
    resumed.resource('ledger','/api/v1/stock/ledger',dict(sku=erp.mapping.sku,warehouse_name=erp.mapping.warehouseName))
    assert resumed.state['requestCount']==count
