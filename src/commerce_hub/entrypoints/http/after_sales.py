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
    datasetId:str|None=None
    orderId:str|None=None
    erpTicketId:str|None=Field(default=None,pattern=r'^[1-9][0-9]{0,19}$')
    erpVoiceId:str|None=Field(default=None,pattern=r'^[1-9][0-9]{0,19}$')
    erpVoiceKind:Literal['reviews','feedback']|None=None
    erpStoreName:str|None=Field(default=None,max_length=128)


class DatasetCreate(Strict):
    manifest:dict


class Change(Strict):
    expectedRevision:int=Field(ge=1)
    data:dict=Field(default_factory=dict)


class Upload(Strict):
    expectedRevision:int=Field(ge=1)
    number:int=Field(ge=0,le=299)
    records:list[dict]=Field(max_length=1000)


class Lookups(Strict):
    identities:list[dict]=Field(max_length=100)


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
                try:
                    with d.store.engine.begin() as conn:
                        resource=scope(actor.tenant_id,'CASE',source='TEACHING_ERP_OBSERVED',source_tenant=item['sourceTenant'])
                        d.store.authorize(conn,actor,'b:read',resource)
                        d.store.authorize(conn,actor,'b:case:write',resource)
                    stores.append(name)
                except AccessDenied:continue
        return dict(workspaceId=WORKSPACE,modelEnabled=d.provider is not None,sourceStores=stores,sourceNature='MIDDLEWARE_TEACHING_DATA')

    @app.get(prefix+'/source-inbox')
    def source_inbox(request:Request,store:str=Query(min_length=1,max_length=128),kind:Literal['tickets','reviews','feedback']='tickets',
                     dateFrom:str|None=Query(default=None,pattern=r'^\d{4}-\d{2}-\d{2}$'),dateTo:str|None=Query(default=None,pattern=r'^\d{4}-\d{2}-\d{2}$'),actor=Depends(principal)):
        from datetime import date
        try:
            start=date.fromisoformat(dateFrom) if dateFrom else None
            end=date.fromisoformat(dateTo) if dateTo else None
            require(not start or not end or start<=end,'SOURCE_DATE_INVALID')
        except ValueError:require(False,'SOURCE_DATE_INVALID')
        return domain(request).source_inbox(actor,store,kind,dateFrom,dateTo)

    @app.get(prefix+'/mapping-options')
    def mapping_options(request:Request,datasetId:str,store:str=Query(min_length=1,max_length=128),sku:str=Query(min_length=1,max_length=128),actor=Depends(principal)):
        d=domain(request);require(d.source_reader is not None,'ERP_SOURCE_NOT_CONFIGURED',503)
        def check():
            with d.store.engine.begin() as conn:d.store.get(conn,actor,'DATASET',datasetId,'b:binding:manage')
        check();result=d.source_reader.mapping_options(store,sku,check);check();return result

    @app.get(prefix+'/workbench')
    def workbench(request:Request,actor=Depends(principal)):
        d=domain(request)
        return {kind.lower():d.store.list(actor,kind,limit=100) for kind in ('CASE','DATASET','POLICY','REPORT','INVESTIGATION','RISK','BINDING')}

    @app.post(prefix+'/cases')
    def create_case(body:CaseCreate,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).create_case(actor,key,body.model_dump())

    @app.post(prefix+'/datasets')
    def create_dataset(body:DatasetCreate,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).create_dataset(actor,key,body.model_dump())

    @app.post(prefix+'/policies')
    def create_policy(body:dict,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).create_policy(actor,key,body)

    @app.post(prefix+'/investigations')
    def investigation(body:dict,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).investigation(actor,key,body)

    @app.post(prefix+'/risks')
    def risk(body:dict,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).risk(actor,key,body)

    @app.get(prefix+'/teaching-package')
    def package(request:Request,actor=Depends(principal)):
        d=domain(request)
        from commerce_hub.scenarios.after_sales.common import scope
        with d.store.engine.begin() as conn:d.store.authorize(conn,actor,'b:dataset:manage',scope(actor.tenant_id,'DATASET'))
        from commerce_hub.scenarios.after_sales.teaching import golden_package
        manifest,blocks=golden_package()
        return dict(manifest=manifest,chunks=blocks)

    @app.get(prefix+'/policy-starters')
    def starters(request:Request,actor=Depends(principal)):
        d=domain(request)
        from commerce_hub.scenarios.after_sales.common import scope
        with d.store.engine.begin() as conn:d.store.authorize(conn,actor,'b:policy:write',scope(actor.tenant_id,'POLICY'))
        from commerce_hub.scenarios.after_sales.teaching import policy_starters
        return [dict((k,v) for k,v in p.items() if k!='id') for p in policy_starters()]

    names={'cases':'CASE','datasets':'DATASET','policies':'POLICY','analyses':'REPORT','investigations':'INVESTIGATION','risks':'RISK','teaching-bindings':'BINDING'}

    @app.get(prefix+'/commands/{key}')
    def command_result(key:str,request:Request,actor=Depends(principal)):
        d=domain(request)
        from sqlalchemy import select
        from commerce_hub.scenarios.after_sales.tables import commands
        with d.store.engine.begin() as conn:
            d.store.access._assert_current(conn,actor,lock=True)
            row=conn.execute(select(commands).filter_by(tenant_id=actor.tenant_id,actor=actor.principal_id,command_key=key)).mappings().first()
            if row:
                r=row['result'];d.store.get(conn,actor,r['kind'],r['id']);return dict(status='FOUND',result=r)
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

    @app.get(prefix+'/datasets/{rid}/records')
    def records(rid:str,request:Request,offset:int=Query(default=0,ge=0),actor=Depends(principal)):
        d=domain(request)
        with d.store.engine.begin() as conn:
            row=d.store.get(conn,actor,'DATASET',rid)
            values=d.records(conn,row)
            return dict(items=values[offset:offset+100],total=len(values),nextOffset=offset+100 if offset+100<len(values) else None,sourceNature=row['scope']['sourceNature'])

    @app.get(prefix+'/{collection}/{rid}/evidence/{eid}')
    def evidence(collection:str,rid:str,eid:str,request:Request,actor=Depends(principal)):
        require(collection in {'cases','analyses'},'NOT_FOUND',404)
        return domain(request).evidence(actor,names[collection],rid,eid)

    @app.post(prefix+'/datasets/{rid}/chunks')
    def upload(rid:str,body:Upload,request:Request,key:command_key,actor=Depends(principal)):
        return domain(request).upload(actor,rid,key,body.number,body.records,body.expectedRevision)

    @app.post(prefix+'/risk-lookups')
    def lookups(body:Lookups,request:Request,actor=Depends(principal)):
        return dict(items=QualityRiskReadPort(domain(request)).lookup(actor,body.identities))

    @app.post(prefix+'/{collection}/{rid}/{action}')
    def change(collection:str,rid:str,action:str,body:Change,request:Request,key:command_key,actor=Depends(principal)):
        require(collection in names,'NOT_FOUND',404);d=domain(request);kind=names[collection]
        job={'evidence-jobs':'evidence','advice-jobs':'advice','validation-jobs':'validate','analysis-jobs':'analysis','binding-jobs':'binding'}.get(action)
        if job:
            require((kind=='CASE' and job in {'evidence','advice'}) or (kind=='DATASET' and job in {'validate','analysis','binding'}),'ACTION_INVALID')
            from starlette.responses import JSONResponse
            return JSONResponse(d.job(actor,kind,rid,job,key,body.expectedRevision,body.data),status_code=202)
        return d.mutate(actor,kind,rid,action,key,body.expectedRevision,body.data)
