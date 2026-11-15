"""Real isolated MySQL; synthetic ERP, including uncertain cross-report operations."""
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select,update
import pytest
from commerce_hub.adapters.erp import ERPConfig
from commerce_hub.adapters.erp_requisition import TeachingRequisitionClient
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.s01_backend.requisition_store import requisitions
from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService
from tests.integration.orchestration.test_s01_reports import make_s01
from tests.integration.s01.test_registered_product_workflow import owned_environment
from tests.integration.s01.test_v2_workflow import run,single
from commerce_hub.orchestration.worker import Worker
from uuid import uuid4
from tests.integration.s01.test_v2_workflow import environment

pytestmark=pytest.mark.mysql


def test_eleven_scope_report_survives_mysql_fraction_roundtrip(make_s01,tmp_path,monkeypatch):
    import commerce_hub.scenarios.s01_v2.handler as h
    e=environment(make_s01,tmp_path,11);original=h.analyze
    def fail(catalog,entity,*args,**kwargs):
        if entity['sku']=='V2-SKU-5':raise ValueError('synthetic missing evidence')
        return original(catalog,entity,*args,**kwargs)
    monkeypatch.setattr(h,'analyze',fail)
    tid,report=run(e)
    assert report['dataReport']['summary']['coverage']==round(10/11,12)
    assert e.service.read_report(e.principal,tid)==report

def service(e,tmp_path):
    factory=lambda *_:TeachingRequisitionClient(ERPConfig(access_token='synthetic-source-token'),transport=e.erp.transport,sleeper=lambda _:None)
    return V2RequisitionService(e.service,e.policy,factory,tmp_path/'requests')

def another_single(e,first):
    item=e.service.read_report(e.principal,first)['dataReport']['item']
    entity={k:item[k] for k in ['entityKey','sourceTenant','storeId','warehouseId','productId','sku','storeName','warehouseName']}
    view=e.service.create(e.principal,uuid4().hex,'S01_V2_SINGLE',e.scope,dict(entity=entity,explainAI=False),'synthetic')
    assert Worker(e.service).once()
    return view['taskRef']['taskId']

@pytest.mark.parametrize('phase',['CREATE_UNKNOWN','SUBMIT_UNKNOWN','SUBMITTED','PREPARING'])
def test_same_business_object_stays_blocked_after_new_analysis(make_s01,tmp_path,phase):
    e=owned_environment(make_s01,tmp_path);tid,_=run(e);first=single(e,tid)
    rq=service(e,tmp_path);saved=rq.confirm(e.principal,first,'first',48,'','synthetic')
    with e.database.engine.begin() as c:
        c.execute(update(requisitions).where(requisitions.c.report_id==first).values(state=phase))
    second=another_single(e,first);mutations=e.erp.mutations
    restored=rq.read(e.principal,second)
    assert restored['reportId']==first and restored['blockedByOtherAnalysis'] and restored['state']==phase
    with pytest.raises(TaskError,match='BUSINESS_OBJECT_REQUISITION_EXISTS'):
        rq.confirm(e.principal,second,'new-command',48,'','synthetic')
    assert e.erp.mutations==mutations==2
    with e.database.engine.connect() as c:assert len(c.execute(select(requisitions).where(requisitions.c.tenant_id==e.tenant)).all())==1

def test_concurrent_reports_only_create_one_purchase(make_s01,tmp_path):
    e=owned_environment(make_s01,tmp_path);tid,_=run(e);first=single(e,tid);ids=[first,another_single(e,first)];rq=service(e,tmp_path)
    def confirm(i):
        try:return rq.confirm(e.principal,ids[i],'command-'+str(i),48,'','synthetic')['state']
        except TaskError as ex:return ex.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(confirm,[0,1]))
    assert sorted(results)==['BUSINESS_OBJECT_REQUISITION_EXISTS','SUBMITTED']
    assert e.erp.mutations==2


def test_voided_order_allows_new_analysis_purchase_and_preserves_original_command(make_s01,tmp_path):
    e=owned_environment(make_s01,tmp_path);tid,_=run(e);first=single(e,tid)
    rq=service(e,tmp_path);original=rq.confirm(e.principal,first,'first',48,'','synthetic')
    next(iter(e.erp.orders.values()))['status_text']='已作废'
    second=another_single(e,first)
    assert rq.read(e.principal,second) is None
    # Replaying the original report cannot create a replacement order.
    assert rq.confirm(e.principal,first,'first',48,'','synthetic')['operationId']==original['operationId']
    assert e.erp.mutations==2
    replacement=rq.confirm(e.principal,second,'replacement',48,'','synthetic')
    assert replacement['state']=='SUBMITTED' and replacement['erpId']!=original['erpId']
    assert e.erp.mutations==4 and len(e.erp.orders)==2
    third=another_single(e,first)
    assert rq.read(e.principal,third)['reportId']==second
    with pytest.raises(TaskError,match='BUSINESS_OBJECT_REQUISITION_EXISTS'):
        rq.confirm(e.principal,third,'duplicate',48,'','synthetic')
    assert e.erp.mutations==4


@pytest.mark.parametrize('fault',['read_failure','foreign_tenant','wrong_id','changed_quantity','changed_product','unknown_phase','active_again'])
def test_void_label_does_not_release_unverified_or_active_operation(make_s01,tmp_path,fault):
    e=owned_environment(make_s01,tmp_path);tid,_=run(e);first=single(e,tid)
    rq=service(e,tmp_path);rq.confirm(e.principal,first,'first',48,'','synthetic')
    order=next(iter(e.erp.orders.values()));order['status_text']='已作废'
    second=another_single(e,first)
    if fault=='foreign_tenant':order['tenant_id']=99
    elif fault=='wrong_id':order['id']=99999
    elif fault=='changed_quantity':order['item_list'][0]['quantity']=96
    elif fault=='changed_product':order['item_list'][0]['product_id']=99999
    elif fault=='unknown_phase':
        with e.database.engine.begin() as c:c.execute(update(requisitions).where(requisitions.c.report_id==first).values(state='SUBMIT_UNKNOWN'))
    elif fault=='active_again':
        assert rq.read(e.principal,second) is None
        order['status_text']='待审核'
    else:
        from commerce_hub.adapters.erp import ERPError
        def unavailable(*args):raise ERPError('ERP_TIMEOUT')
        rq.client_factory=lambda *_:type('Unavailable',(),{'read_requisition':unavailable})()
    restored=rq.read(e.principal,second)
    assert restored and restored['reportId']==first
    with pytest.raises(TaskError,match='BUSINESS_OBJECT_REQUISITION_EXISTS'):
        rq.confirm(e.principal,second,'new',48,'','synthetic')
    assert e.erp.mutations==2
