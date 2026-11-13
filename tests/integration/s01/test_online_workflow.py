"""Real MySQL/O01 with a fixture transport; no ERP or model network."""
from dataclasses import replace
from datetime import timedelta
from threading import Event
import json
import pytest
from sqlalchemy import select,update,func
from commerce_hub.adapters.erp import ERPConfig,TeachingERPReader
from commerce_hub.scenarios.s01_backend.online import OnlineS01Handler
from commerce_hub.orchestration.worker import Worker,ExecutionContext
from commerce_hub.orchestration.service import TaskError
from commerce_hub.orchestration.tables import reports,tasks
from commerce_hub.infrastructure.work_tables import work_items
from commerce_hub.infrastructure.work import LeaseLost
from commerce_hub.data.sync.online_store import acquisitions
from commerce_hub.data.quality.online_store import snapshots
from tests.integration.orchestration.test_s01_reports import make_s01,count
from tests.unit.data.test_online import mapping,pages

pytestmark=pytest.mark.mysql

def environment(make_s01):
    env=make_s01();m=mapping().model_copy(update={'scope':env.scope});env.reads=[]
    def reader_factory(*_):
        def transport(method,path,*_):
            env.reads.append(path);values=pages().get(path.split('?')[0].split('/')[-1],[])
            return 200,json.dumps(dict(items=values,total=len(values)) if method=='GET' else dict(code=0,data=[],total=0)).encode()
        return TeachingERPReader(ERPConfig(access_token='fixture-only'),transport=transport,sleeper=lambda _:None)
    env.spec=replace(env.spec,scenario_id='S01_BACKEND',handler=OnlineS01Handler([m],reader_factory))
    env.service.registry={env.spec.scenario_id:env.spec};env.params=dict(inputMode='ONLINE_TEACHING_ERP')
    env.submit=lambda key:env.service.create(env.principal,key,env.spec.scenario_id,env.scope,env.params,'fixture')
    return env

def test_online_tasks_collect_independently_replay_and_history_never_recollect(make_s01):
    env=environment(make_s01);a=env.submit('a');assert not env.reads
    assert Worker(env.service).once();first=env.service.read_report(env.principal,a['taskRef']['taskId']);reads=len(env.reads)
    assert env.submit('a')['taskRef']==a['taskRef'];assert len(env.reads)==reads
    b=env.submit('b');assert Worker(env.service).once();second=env.service.read_report(env.principal,b['taskRef']['taskId'])
    assert first['snapshotRef']!=second['snapshotRef']
    assert first['dataReport']['acquisition']['acquisitionId']!=second['dataReport']['acquisition']['acquisitionId']
    assert count(env,acquisitions)==count(env,snapshots)==2
    assert env.service.read_report(env.principal,a['taskRef']['taskId'])==first
    assert len(env.reads)==reads*2
    assert not {'onlineAsset','manifest'}&set(first['dataReport'])

def test_completed_acquisition_is_reused_after_a_worker_lease_crash(make_s01):
    env=environment(make_s01);tid=env.submit('crash')['taskRef']['taskId']
    lease=env.queue.claim([env.spec.work_kind]);row=env.service.start(lease,env.principal)
    ctx=ExecutionContext(env.service,lease,env.principal,row,Event());result=env.spec.handler.run(ctx,env.params);reads=len(env.reads)
    with env.database.engine.begin() as conn:
        conn.execute(update(work_items).filter_by(tenant_id=env.tenant).values(lease_expires=func.utc_timestamp(6)-__import__('sqlalchemy').text('INTERVAL 1 SECOND')))
    assert Worker(env.service).once()
    assert env.service.read_report(env.principal,tid)['snapshotRef']==result.snapshotRef
    assert len(env.reads)==reads and count(env,acquisitions)==1
    with pytest.raises(LeaseLost):ctx.commit_data(lambda conn:pytest.fail('Old lease cannot write'))

@pytest.mark.parametrize('fault',['cancel','deadline','plan','lease'])
def test_data_commit_is_fenced_by_original_task_authority(make_s01,fault):
    env=environment(make_s01);tid=env.submit('fence')['taskRef']['taskId'];lease=env.queue.claim([env.spec.work_kind])
    row=env.service.start(lease,env.principal);ctx=ExecutionContext(env.service,lease,env.principal,row,Event())
    if fault=='cancel':
        current=env.service.read(env.principal,tid);env.service.cancel(env.principal,tid,'cancel',current['revision'],'test')
    else:
        with env.database.engine.begin() as conn:
            if fault=='plan':conn.execute(update(tasks).filter_by(tenant_id=env.tenant).values(plan_version=2))
            elif fault=='deadline':conn.execute(update(tasks).filter_by(tenant_id=env.tenant).values(deadline=conn.scalar(select(func.utc_timestamp(6)))-timedelta(seconds=1)))
            else:conn.execute(update(work_items).filter_by(tenant_id=env.tenant).values(lease_expires=conn.scalar(select(func.utc_timestamp(6)))-timedelta(seconds=1)))
    with pytest.raises((TaskError,LeaseLost)):ctx.commit_data(lambda conn:pytest.fail('Rejected before data write'))
    assert count(env,acquisitions)==count(env,snapshots)==count(env,reports)==0
