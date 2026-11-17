"""Same identity/CSRF dependencies as S01. Ownership always resolves from persisted assets."""
from typing import Annotated,Literal
from fastapi import Depends,Header,Request,Query
from pydantic import BaseModel,ConfigDict,Field
from commerce_hub.scenarios.after_sales.common import require,WORKSPACE
from commerce_hub.scenarios.after_sales.risk import QualityRiskReadPort


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',hide_input_in_errors=True)


class CaseCreate(Strict):
    title:str=Field(min_length=1,max_length=200)
    message:str=Field(default='',max_length=6000)
    region:str=Field(min_length=1,max_length=32)
    platform:str=Field(min_length=1,max_length=64)
    language:str=Field(min_length=1,max_length=16)
    businessDate:str|None=None
    orderId:str|None=None
    erpTicketId:str|None=Field(default=None,pattern=r'^[1-9][0-9]{0,19}$')
    erpVoiceId:str|None=Field(default=None,pattern=r'^[1-9][0-9]{0,19}$')
    erpVoiceKind:Literal['reviews','feedback']|None=None
    erpStoreName:str|None=Field(default=None,max_length=128)


class Change(Strict):
    expectedRevision:int=Field(ge=1)
    data:dict=Field(default_factory=dict)


class Lookups(Strict):
    identities:list[dict]=Field(max_length=100)


class ReturnCaseCreate(Strict):
    store:str=Field(min_length=1,max_length=128)
    returnId:str=Field(pattern=r'^[1-9][0-9]{0,19}$')
    sku:str=Field(min_length=1,max_length=50)


class MonitorCaseCreate(Strict):
    store:str=Field(min_length=1,max_length=128)
    sku:str=Field(min_length=1,max_length=50)
    endDate:str|None=Field(default=None,pattern=r'^\d{4}-\d{2}-\d{2}$')
    windowDays:int=Field(default=7,ge=3,le=30)


def register_b_routes(app,principal):
    prefix='/api/b/v1'
    command_key=Annotated[str,Header(alias='Idempotency-Key',min_length=1,max_length=128)]
    def domain(request):
        service=request.app.state.tasks
        require(service.after_sales_enabled,'B_NOT_ENABLED',503)
        from sqlalchemy import inspect
        require(inspect(service.engine).has_table('b_assets'),'B_NOT_READY',503)
        return service.after_sales

    @app.get(prefix+'/workspace')
    def workspace(request:Request,actor=Depends(principal)):
        d=domain(request)
        # Parent scopes only describe permitted creation, never reveal existing counts.
        from commerce_hub.scenarios.after_sales.common import scope
        with d.store.engine.begin() as conn:d.store.authorize(conn,actor,'b:read',scope(actor.tenant_id,'CASE'))
        from commerce_hub.governance.access.service import AccessDenied
        stores=[]
        if d.source_reader:
            for name,item in d.source_reader.stores.items():
                if hasattr(d.source_reader,'members') and d.source_reader.members(name)==[]:continue
                try:
                    with d.store.engine.begin() as conn:
                        resource=scope(actor.tenant_id,'CASE',source='TEACHING_ERP_OBSERVED',source_tenant=item['sourceTenant'])
                        d.store.authorize(conn,actor,'b:read',resource)
                        d.store.authorize(conn,actor,'b:case:write',resource)
                    stores.append(name)
                except AccessDenied:continue
        members=d.source_reader.members() if d.source_reader and hasattr(d.source_reader,'members') else []
        capabilities={}
        for name,action,kind in [('policyWrite','b:policy:write','POLICY'),('policyPublish','b:policy:publish','POLICY')]:
            try:
                with d.store.engine.begin() as conn:d.store.authorize(conn,actor,action,scope(actor.tenant_id,kind))
                capabilities[name]=True
            except AccessDenied:capabilities[name]=False
        return dict(workspaceId=WORKSPACE,modelEnabled=d.provider is not None,sourceStores=stores,sourceNature='TEACHING_ERP_OBSERVED',
            capabilities=capabilities,sourceProductCounts={name:len({m.sku for m in (members or []) if m.storeName==name}) for name in stores} if members is not None else {},trackingScope='PROJECT_OWNED_ERP',trackedProducts=len({(m.sourceTenant,m.monitor.productId) for m in members}) if members is not None else None)

    @app.get(prefix+'/source-inbox')
    def source_inbox(request:Request,store:str=Query(min_length=1,max_length=128),kind:Literal['tickets','reviews','feedback']='tickets',
                     dateFrom:str|None=Query(default=None,pattern=r'^\d{4}-\d{2}-\d{2}$'),dateTo:str|None=Query(default=None,pattern=r'^\d{4}-\d{2}-\d{2}$'),full:bool=False,actor=Depends(principal)):
        from datetime import date
        try:
            start=date.fromisoformat(dateFrom) if dateFrom else None
            end=date.fromisoformat(dateTo) if dateTo else None
            require(not start or not end or start<=end,'SOURCE_DATE_INVALID')
        except ValueError:require(False,'SOURCE_DATE_INVALID')
        return domain(request).source_inbox(actor,store,kind,dateFrom,dateTo,full)

    @app.get(prefix+'/return-analysis')
    def return_analysis(request:Request,store:str=Query(min_length=1,max_length=128),endDate:str|None=Query(default=None,pattern=r'^\d{4}-\d{2}-\d{2}$'),
                        windowDays:int=Query(default=7,ge=3,le=30),actor=Depends(principal)):
        return domain(request).return_analysis(actor,store,endDate,windowDays)

    @app.post(prefix+'/return-cases')
    def create_return_case(body:ReturnCaseCreate,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).create_return_case(actor,key,body.store,body.returnId,body.sku)

    @app.post(prefix+'/monitor-cases')
    def create_monitor_case(body:MonitorCaseCreate,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).create_monitor_case(actor,key,body.store,body.sku,body.endDate,body.windowDays)

    @app.get(prefix+'/workbench')
    def workbench(request:Request,actor=Depends(principal)):
        d=domain(request)
        return {kind.lower():d.store.list(actor,kind,limit=100) for kind in ('CASE','POLICY','INVESTIGATION','RISK')}

    @app.post(prefix+'/cases')
    def create_case(body:CaseCreate,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).create_case(actor,key,body.model_dump())

    @app.post(prefix+'/policies')
    def create_policy(body:dict,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).create_policy(actor,key,body)

    @app.post(prefix+'/investigations')
    def investigation(body:dict,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).investigation(actor,key,body)

    @app.get(prefix+'/investigations/{rid}/facts')
    def investigation_facts(rid:str,request:Request,actor=Depends(principal)):
        d=domain(request)
        with d.store.engine.begin() as conn:
            investigation=d.store.get(conn,actor,'INVESTIGATION',rid)
            return dict(items=d.investigation_facts(conn,actor,investigation))

    @app.post(prefix+'/risks')
    def risk(body:dict,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).risk(actor,key,body)

    @app.post(prefix+'/investigations/{rid}/confirm-risk')
    def confirm_risk(rid:str,body:Change,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).confirm_risk(actor,rid,key,body.expectedRevision,body.data)

    @app.get(prefix+'/policy-starters')
    def starters(request:Request,region:Literal['CN','US']='CN',platform:Literal['TEACHING','Amazon']='TEACHING',actor=Depends(principal)):
        d=domain(request)
        from commerce_hub.scenarios.after_sales.common import scope
        with d.store.engine.begin() as conn:d.store.authorize(conn,actor,'b:policy:write',scope(actor.tenant_id,'POLICY'))
        from commerce_hub.scenarios.after_sales.policy_templates import policy_starters
        return [dict((k,v) for k,v in p.items() if k!='id') for p in policy_starters(region,platform)]

    names={'cases':'CASE','policies':'POLICY','investigations':'INVESTIGATION','risks':'RISK'}

    @app.get(prefix+'/commands/{key}')
    def command_result(key:str,request:Request,actor=Depends(principal)):
        d=domain(request)
        from sqlalchemy import select
        from commerce_hub.scenarios.after_sales.tables import commands
        with d.store.engine.begin() as conn:
            d.store.access._assert_current(conn,actor,lock=True)
            row=conn.execute(select(commands).filter_by(tenant_id=actor.tenant_id,actor=actor.principal_id,command_key=key)).mappings().first()
            if row:
                r=row['result'];d.store.get(conn,actor,r['kind'],r['id'])
        if row:
            if r.get('handlingStatus')=='PENDING':
                from commerce_hub.scenarios.after_sales.confirmation import Confirmation
                r=Confirmation(d).recover(actor,key,r['id'])
            return dict(status='FOUND',result=r)
        # O01 owns asynchronous command lookup and its current task authorization.
        return d.tasks.find_command(actor,key)

    @app.get(prefix+'/{collection}')
    def list_assets(collection:str,request:Request,before:str|None=None,limit:int=Query(default=20,ge=1,le=100),actor=Depends(principal)):
        require(collection in names,'NOT_FOUND',404)
        return domain(request).store.list(actor,names[collection],before=before,limit=limit)

    @app.get(prefix+'/{collection}/{rid}')
    def read_asset(collection:str,rid:str,request:Request,version:int|None=Query(default=None,ge=1),actor=Depends(principal)):
        require(collection in names,'NOT_FOUND',404)
        return domain(request).store.read(actor,names[collection],rid,version)

    @app.get(prefix+'/{collection}/{rid}/evidence/{eid}')
    def evidence(collection:str,rid:str,eid:str,request:Request,actor=Depends(principal)):
        require(collection=='cases','NOT_FOUND',404)
        return domain(request).evidence(actor,names[collection],rid,eid)

    @app.post(prefix+'/risk-lookups')
    def lookups(body:Lookups,request:Request,actor=Depends(principal)):
        return dict(items=QualityRiskReadPort(domain(request)).lookup(actor,body.identities))

    @app.post(prefix+'/{collection}/{rid}/{action}')
    def change(collection:str,rid:str,action:str,body:Change,request:Request,key:command_key,actor=Depends(principal)):
        require(collection in names,'NOT_FOUND',404);d=domain(request);kind=names[collection]
        job={'evidence-jobs':'evidence','advice-jobs':'advice','investigation-jobs':'investigation'}.get(action)
        if job:
            require(kind=='CASE' and job in {'evidence','advice','investigation'},'ACTION_INVALID')
            from starlette.responses import JSONResponse
            return JSONResponse(d.job(actor,kind,rid,job,key,body.expectedRevision,body.data),status_code=202)
        return d.mutate(actor,kind,rid,action,key,body.expectedRevision,body.data)
