"""V2 HTTP uses the same trusted principal/CSRF dependency as existing tasks."""
from typing import Annotated
from fastapi import Depends,Header,Request,Query
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from commerce_hub.scenarios.s01_v2.handler import collection_scope
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.scenarios.s01_v2.analysis import priority,statistics
from commerce_hub.orchestration.service import TaskError
from commerce_hub.governance.access.service import AccessDenied
from commerce_hub.bootstrap.logging import trace_id


class Empty(BaseModel):model_config=ConfigDict(extra='forbid')
class Cancel(Empty):expectedRevision:int=Field(ge=1,strict=True)
class Single(Empty):
    batchId:str=Field(min_length=1,max_length=64)
    entityKey:str=Field(pattern=r'^[0-9a-f]{64}$')
    explainAI:bool=Field(default=False,strict=True)
class Confirm(Empty):
    finalQuantity:int=Field(ge=1,le=100000,strict=True)
    adjustmentReason:str=Field(default='',max_length=1000)
    sourceAcknowledged:bool=Field(strict=True)


def register_v2_routes(app,principal):
    def services(request,actor):
        s=request.app.state.tasks
        if not s or 'S01_V2_BATCH' not in s.registry:raise TaskError('V2_NOT_ENABLED',409)
        spec=s.registry['S01_V2_BATCH'];scope=collection_scope(actor.tenant_id)
        spec.handler.validate_scope({},scope)
        with s.engine.begin() as c:s.access.authorize(c,actor,'tasks:read',scope)
        return s,spec.handler.policy,scope
    def data(request,actor,task_id):
        s,p,scope=services(request,actor);view=s.read(actor,task_id)
        if view['scenarioId'] not in {'S01_V2_BATCH','S01_V2_SINGLE'}:raise TaskError('NOT_FOUND',404)
        with s.engine.connect() as c:rows=ItemStore.read(c,actor.tenant_id,task_id)
        for row in rows.values():
            if row.get('procurementEligibility'):row['procurementEligibility']['scopeAuthorized']=p.can_write(row)
        return s,p,view,rows
    @app.get('/api/v1/s01/v2/options')
    def options(request:Request,actor=Depends(principal)):
        s,p,scope=services(request,actor)
        can_submit=False
        try:
            with s.engine.begin() as c:s.access.authorize(c,actor,'s01:requisition',scope)
            can_submit=p.requisition_enabled
        except AccessDenied:pass
        return dict(enabled=True,scope=scope,analysisRange='OWNED_REGISTERED' if p.owned_only else 'ALL_GRANTED_READABLE_STORES_WAREHOUSES_SKUS_IN_SOURCE_TENANT',sourceTenant=p.source_tenant,
            procurementRange='EXPLICIT_OWNED_TEACHING_RESOURCES_ONLY',batchModelCalls=0,batchWrites=0,singleAIEnabled=s.registry['S01_V2_SINGLE'].handler.provider is not None,
            sourcePolicy='s01-v2-scheme-b-v1',canSubmit=can_submit,principalRef=dict(tenantId=actor.tenant_id,principalId=actor.principal_id))
    @app.post('/api/v1/s01/v2/batches',status_code=202)
    def create(body:Empty,request:Request,key:Annotated[str,Header(alias='Idempotency-Key',min_length=1,max_length=128)],actor=Depends(principal)):
        s,p,scope=services(request,actor)
        return s.create(actor,key,'S01_V2_BATCH',scope,{},trace_id.get())
    @app.get('/api/v1/s01/v2/batches')
    def history(request:Request,before:str|None=None,actor=Depends(principal)):
        s,p,scope=services(request,actor)
        history=s.history(actor,scope,scenario_id='S01_V2_BATCH',limit=20,before=before)
        from commerce_hub.data.sync.v2_store import AcquisitionCheckpoint
        with s.engine.connect() as c:ranges=AcquisitionCheckpoint.public_ranges(c,actor.tenant_id,[r['taskRef']['taskId'] for r in history['items']])
        for row in history['items']:row['analysisRange']=ranges.get(row['taskRef']['taskId'],'NOT_STARTED')
        return history
    @app.get('/api/v1/s01/v2/batches/{task_id}')
    def progress(task_id:str,request:Request,actor=Depends(principal)):
        s,p,view,rows=data(request,actor,task_id)
        version='product-counts-v1' if any(r.get('decisionVersion') for r in rows.values()) else 'v2-counts-v2'
        result=dict(task=view,summary=statistics(rows.values(),version),statisticsVersion=version,enumerationComplete=None)
        from commerce_hub.data.sync.v2_store import AcquisitionCheckpoint
        with s.engine.connect() as c:result['analysisRange']=AcquisitionCheckpoint.public_ranges(c,actor.tenant_id,[task_id]).get(task_id,'NOT_STARTED')
        if view['state']=='SUCCEEDED':
            report=s.read_report(actor,task_id);result.update(summary=report['dataReport']['summary'],statisticsVersion=report['dataReport'].get('statisticsVersion','v2-counts-v1'),enumerationComplete=report['dataReport']['enumerationComplete'],sourceLimits=report['dataReport']['sourceLimits'])
        return result
    @app.get('/api/v1/s01/v2/batches/{task_id}/items')
    def listing(task_id:str,request:Request,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),q:str=Query('',max_length=128),store:str='',warehouse:str='',state:str='',source:str='',risk:str='',group:str='',decision:str='',actor=Depends(principal)):
        s,p,view,rows=data(request,actor,task_id)
        values=[r for r in rows.values() if (not q or q.lower() in (r['sku']+' '+r.get('name','')).lower()) and (not store or r.get('storeId')==store)
            and (not warehouse or r.get('warehouseId')==warehouse) and (not state or r['analysisState']==state)
            and (not source or r['sourceGrade']==source) and (not risk or r.get('riskGroup')==risk)]
        values.sort(key=priority)
        if group=='sku':
            from commerce_hub.scenarios.s01_v2.products import group_products
            values=group_products(values,priority)
        def matches(r):
            if not decision:return True
            p=r.get('productSummary');d=r.get('decision',{})
            if decision=='RISK':return bool(p['riskScopeCount'] if p else d.get('stockoutRisk'))
            if decision=='DIFFERENCE':return bool(p['erpDifferenceScopeCount'] if p else r.get('erpComparison',{}).get('significant'))
            if decision=='FORECAST':return bool(p['analyzedSkuCount'] if p else d.get('forecast',{}).get('available'))
            if p:
                return bool(p['replenishScopeCount']) if decision=='REPLENISH' else p['noReplenishmentScopeCount']==p['scopeCount'] if decision=='NO_REPLENISHMENT' else p['judgedScopeCount']==0 if decision=='NEEDS_REVIEW' else False
            return d.get('status')==decision
        values=[r for r in values if matches(r)]
        return dict(total=len(values),offset=offset,limit=limit,items=[{k:v for k,v in r.items() if k not in {'ruleResult','sourceSuggestion','snapshotManifest'}} for r in values[offset:offset+limit]],
            stores=sorted({(r.get('storeId') or '',r.get('storeName') or '') for r in rows.values()}),warehouses=sorted({(r.get('warehouseId') or '',r.get('warehouseName') or '') for r in rows.values()}))
    @app.get('/api/v1/s01/v2/batches/{task_id}/items/{entity_key}')
    def detail(task_id:str,entity_key:str,request:Request,actor=Depends(principal)):
        s,p,view,rows=data(request,actor,task_id)
        if entity_key not in rows:raise TaskError('NOT_FOUND',404)
        row=rows[entity_key]
        if row.get('ruleResult'):row['ruleResult'].pop('input',None)
        result=dict(row)
        result['relatedScopes']=[{k:v for k,v in r.items() if k not in {'ruleResult','snapshotManifest'}} for r in sorted(rows.values(),key=priority) if r['sku']==row['sku']]
        return result
    @app.post('/api/v1/s01/v2/batches/{task_id}/cancel')
    def cancel(task_id:str,body:Cancel,request:Request,key:Annotated[str,Header(alias='Idempotency-Key',min_length=1,max_length=128)],actor=Depends(principal)):
        s,p,view,rows=data(request,actor,task_id)
        return s.cancel(actor,task_id,key,body.expectedRevision,trace_id.get())
    @app.post('/api/v1/s01/v2/batches/{task_id}/retry',status_code=202)
    def retry(task_id:str,body:Empty,request:Request,key:Annotated[str,Header(alias='Idempotency-Key',min_length=1,max_length=128)],actor=Depends(principal)):
        s,p,view,rows=data(request,actor,task_id)
        return s.create(actor,key,'S01_V2_BATCH',collection_scope(actor.tenant_id),{},trace_id.get())
    @app.get('/api/v1/s01/v2/purchase-status')
    def purchase_status(request:Request,batchId:str=Query(min_length=1,max_length=64),actor=Depends(principal)):
        s,p,view,rows=data(request,actor,batchId)
        if view['scenarioId']!='S01_V2_BATCH' or view['state']!='SUCCEEDED':raise TaskError('PURCHASE_TRACKING_BATCH_REQUIRED',409)
        factory=getattr(s.registry['S01_V2_BATCH'].handler,'purchase_reader_factory',None)
        if factory is None:raise TaskError('PURCHASE_TRACKING_NOT_AVAILABLE',409)
        from commerce_hub.scenarios.s01_v2.tracking import track_purchases
        from commerce_hub.scenarios.s01_backend.requisition_store import saved_tracking_references
        try:return track_purchases(rows.values(),p,factory(),saved_tracking_references(s.engine,actor.tenant_id),discover=True)
        except ValueError as exc:raise TaskError(str(exc),409) from None

    @app.post('/api/v1/s01/v2/singles',status_code=202)
    def single(body:Single,request:Request,key:Annotated[str,Header(alias='Idempotency-Key',min_length=1,max_length=128)],actor=Depends(principal)):
        s,p,view,rows=data(request,actor,body.batchId)
        e=rows.get(body.entityKey)
        if e is None or not e.get('identityVerified'):raise TaskError('V2_BUSINESS_SCOPE_UNRESOLVED',422)
        if p.owned_only and p.opening_binding(e) is None:raise TaskError('V2_BUSINESS_SCOPE_NOT_REGISTERED',403)
        entity={k:e[k] for k in ['entityKey','sourceTenant','storeId','warehouseId','productId','sku','storeName','warehouseName']}
        return s.create(actor,key,'S01_V2_SINGLE',collection_scope(actor.tenant_id),dict(entity=entity,explainAI=body.explainAI),trace_id.get())
    @app.get('/api/v1/s01/v2/singles/{task_id}')
    def single_report(task_id:str,request:Request,actor=Depends(principal)):
        s,p,view,rows=data(request,actor,task_id)
        if view['scenarioId']!='S01_V2_SINGLE':raise TaskError('NOT_FOUND',404)
        report=s.read_report(actor,task_id) if view['state']=='SUCCEEDED' else None
        if report:
            item=report['dataReport']['item']
            item['procurementEligibility']['scopeAuthorized']=p.can_write(item)
        return dict(task=view,report=report)
    @app.get('/api/v1/s01/v2/singles')
    def single_history(request:Request,before:str|None=None,actor=Depends(principal)):
        s,p,scope=services(request,actor)
        history=s.history(actor,scope,scenario_id='S01_V2_SINGLE',limit=20,before=before)
        for row in history['items']:
            if row['state']=='SUCCEEDED':
                report=s.read_report(actor,row['taskRef']['taskId']);item=report['dataReport']['item']
                row.update(sku=item['sku'],entityKey=item['entityKey'],sourceGrade=item['sourceGrade'],
                    aiStatus=report.get('analysisReport',{}).get('ai',{}).get('status'),observedAt=item.get('observedAt'))
        return history
    @app.post('/api/v1/s01/v2/singles/{task_id}/requisition')
    def confirm(task_id:str,body:Confirm,request:Request,key:Annotated[str,Header(alias='Idempotency-Key',min_length=1,max_length=128)],actor=Depends(principal)):
        s,p,scope=services(request,actor)
        if not body.sourceAcknowledged:raise TaskError('SOURCE_ACKNOWLEDGEMENT_REQUIRED',422)
        rq=getattr(s,'v2_requisitions',None)
        if rq is None:raise TaskError('REQUISITION_NOT_ENABLED',409)
        return rq.confirm(actor,task_id,key,body.finalQuantity,body.adjustmentReason,trace_id.get())
    @app.get('/api/v1/s01/v2/singles/{task_id}/requisition')
    def saved(task_id:str,request:Request,actor=Depends(principal)):
        s,p,scope=services(request,actor)
        rq=getattr(s,'v2_requisitions',None)
        if rq is None:
            # Local saved-state reads do not need an ERP client or write permission.
            # Keep the submit endpoint disabled when the requisition feature is off.
            from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService
            rq=V2RequisitionService(s,p,None,'.')
        value=rq.read(actor,task_id)
        if value and value.get('erpId'):
            # Display fresh source status without rewriting the durable command outcome.
            factory=getattr(s.registry['S01_V2_BATCH'].handler,'purchase_reader_factory',None)
            report=s.read_report(actor,task_id)
            item=report['dataReport']['item']
            if factory:
                from commerce_hub.scenarios.s01_v2.tracking import track_purchases
                tracked=track_purchases([item],p,factory(),[dict(value,entityKey=item['entityKey'])])
                current=next((r for r in tracked['items'] if r['erpId']==str(value['erpId'])),None)
                value=dict(value,previousErpStatus=value.get('erpStatus'),erpStatus=current['status'] if current and current['verified'] else None,
                    verifiedAt=current['verifiedAt'] if current else None,liveVerified=bool(current and current['verified']),
                    liveError=current['error'] if current else 'PURCHASE_TRACKING_NOT_AVAILABLE')
        return value
