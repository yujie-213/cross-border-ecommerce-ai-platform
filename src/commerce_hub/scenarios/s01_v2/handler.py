"""S01 scenarios reuse O01 task lifecycle, I01 leases, G01 and D01-D03 ownership."""
from copy import deepcopy
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.sync.v2_catalog import collect_catalog
from commerce_hub.data.projection.v2 import entities
from commerce_hub.data.quality.v2 import catalog_manifest,seal_result,verify_result
from commerce_hub.data.quality.v2_store import ManifestStore
from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.s01_v2.analysis import analyze,statistics
from .store import ItemStore
from .explanation import explain,validate_ai


def collection_scope(tenant):
    return dict(tenantId=tenant,storeIds=['s01-v2-authorized-stores'],warehouseIds=['s01-v2-authorized-warehouses'],canonicalSkuIds=['s01-v2-catalog'],fields=['quantity'])


class V2Handler:
    def __init__(self,engine,policy,reader_factory,*,single=False,provider=None):
        self.engine,self.policy,self.reader_factory=engine,policy,reader_factory
        self.single,self.provider=single,provider
        if not single and provider is not None:raise ValueError('BATCH_MODEL_FORBIDDEN')
    def validate(self,p):
        if not isinstance(p,dict) or (not self.single and p) or (self.single and (not {'entity'}<=set(p)<= {'entity','explainAI'} or 'explainAI' in p and type(p['explainAI']) is not bool)):raise ValueError('V2_PARAMETERS_INVALID')
        if self.single:
            e=p['entity']
            required={'entityKey','sourceTenant','storeId','warehouseId','productId','sku','storeName','warehouseName'}
            if not isinstance(e,dict) or set(e)!=required or any(not isinstance(v,str) or not 1<=len(v)<=128 for v in e.values()):raise ValueError('V2_ENTITY_INVALID')
            if e['sourceTenant']!=self.policy.source_tenant:raise ValueError('V2_SOURCE_TENANT_MISMATCH')
    def validate_scope(self,p,scope):
        self.validate(p)
        if scope!=collection_scope(self.policy.app_tenant):raise ValueError('V2_COLLECTION_SCOPE_INVALID')
    def run(self,context,parameters):
        self.validate_scope(parameters,context.task['scope'])
        reader=self.reader_factory(context)
        try:
            members=self.policy.read_members() if self.policy.owned_only else None
            if members is not None:
                from commerce_hub.data.sync.registered_catalog import collect_registered
                catalog=collect_registered(reader,self.policy.source_tenant,members,parameters.get('entity'))
            else:catalog=collect_catalog(reader,self.policy.source_tenant,parameters['entity'] if self.single else None)
        except ERPError as exc:raise TaskError(exc.code,503) from None
        candidates=entities(catalog,self.policy.source_tenant)
        if members is not None:
            from commerce_hub.data.sync.registered_catalog import registered_entities
            candidates=registered_entities(catalog,candidates)
        if self.single:
            e=parameters['entity']
            candidates=[r for r in candidates if all(r[k]==e[k] for k in ['sourceTenant','storeId','warehouseId','productId','sku'])]
            if len(candidates)!=1:raise ValueError('V2_LATEST_ENTITY_RELATION_UNRESOLVED')
        tenant,task=context.task['tenant_id'],context.task['task_id']
        previous=context.commit_data(lambda c:ItemStore.seed(c,tenant,task,candidates))
        def manifest_for():
            receipt=reader.receipt();receipt['taskRef']=dict(tenantId=tenant,taskId=task)
            return catalog_manifest(receipt,self.policy.source_tenant)
        for entity in candidates:
            context.check()
            if previous.get(entity['entityKey'],{}).get('analysisState') not in {None,'PENDING'}:continue
            try:
                binding=self.policy.opening_binding(entity)
                # Advisory capability uses this task's registered scope. The
                # submit service still rereads current authorization; avoid a
                # per-catalog-SKU registry query merely to render an indicator.
                result=analyze(catalog,entity,reader,opening_binding=binding,
                    requisition_authorized=bool(self.policy.requisition_enabled and binding is not None))
            except (ERPError,ValueError,KeyError,ArithmeticError,TypeError) as exc:
                if isinstance(exc,ERPError) and exc.code=='ERP_AUTH_REJECTED':raise
                result=dict(entity,analysisState='FAILED',sourceGrade='UNAVAILABLE',quantity=None,
                    uncertainties=[exc.code if isinstance(exc,ERPError) else 'SOURCE_FIELDS_INVALID'],riskGroup='UNVERIFIED',riskDate=None,modelCalls=0)
                if reader.state.get('admissionVersion')=='s01-runtime-v1':
                    from commerce_hub.data.quality.runtime import failed_admission
                    result.update(failed_admission(result['uncertainties'][0]))
            manifest=manifest_for()
            context.commit_data(lambda c:ManifestStore.save(c,tenant,task,manifest))
            result=seal_result(result,manifest['snapshotRef'])
            context.commit_data(lambda c,r=result:ItemStore.save(c,tenant,task,r))
        rows=context.commit_data(lambda c:ItemStore.read(c,tenant,task))
        # Manifest includes enrichment performed during analysis; individual results retain their original input manifest.
        complete=all(catalog[n]['complete'] for n in ['products','stores','warehouses','inventory'])
        manifest=manifest_for()
        context.commit_data(lambda c:ManifestStore.save(c,tenant,task,manifest))
        stat_version='product-counts-v1' if reader.state.get('decisionVersion') else 'v2-counts-v2'
        data=dict(version='s01-v2-v1',statisticsVersion=stat_version,summary=statistics(rows.values(),stat_version),enumerationComplete=complete,
            sourceTenant=self.policy.source_tenant,catalogManifest=manifest,
            resultDigest=fingerprint(rows),sourceLimits={n:{k:v for k,v in cap.items() if k!='rows'} for n,cap in catalog.items() if isinstance(cap,dict) and 'rows' in cap},
            analysisRange='OWNED_REGISTERED' if members is not None else 'LEGACY_SHARED',monitoring=catalog.get('monitoring'),
            actionMeaning='HUMAN_CONFIRMED_ERP_REQUISITION_ONLY',batchModelCalls=0,batchBusinessMutations=0)
        ai=dict(status='NOT_ATTEMPTED',reason='BATCH_ZERO_AI',explanation=None)
        if self.single:
            data['item']=next(iter(rows.values()))
            data['summary'].pop('modelCalls',None)
            if data['item']['analysisState']!='FAILED':
                ai=explain(data['item'],context,self.provider if parameters.get('explainAI',True) else None)
        limited=not complete or any(not cap.get('complete') for cap in catalog.values() if isinstance(cap,dict) and 'rows' in cap) or data['summary']['unanalyzable'] or data['summary']['failed']
        return DomainResult(contractVersion='0.1.0',sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',
            completeness='PARTIAL' if limited else 'RULES_ONLY',scope=context.task['scope'],snapshotRef=data['catalogManifest']['snapshotRef'],
            dataReport=data,analysisReport=dict(ai=ai))
    def validate_publication(self,result,task_ref,plan_version):
        if result.scope!=collection_scope(self.policy.app_tenant) or result.dataReport.get('version')!='s01-v2-v1':raise ValueError('V2_PUBLICATION_INVALID')
        with self.engine.connect() as conn:rows=ItemStore.read(conn,task_ref['tenantId'],task_ref['taskId'])
        expected_summary=statistics(rows.values(),result.dataReport.get('statisticsVersion','v2-counts-v1'))
        if self.single:expected_summary.pop('modelCalls',None)
        if result.dataReport['resultDigest']!=fingerprint(rows) or result.dataReport['summary']!=expected_summary:raise ValueError('V2_RESULT_BINDING_INVALID')
        with self.engine.connect() as conn:
            checked=set()
            for row in rows.values():
                verify_result(row)
                ref=row['snapshotManifest']['inputSnapshotRef']
                if ref not in checked:ManifestStore.read(conn,task_ref['tenantId'],task_ref['taskId'],ref);checked.add(ref)
        if self.single:
            if len(rows)!=1 or result.dataReport['item']!=next(iter(rows.values())):raise ValueError('V2_SINGLE_BINDING_INVALID')
            ai=result.analysisReport['ai'];validate_ai(ai,result.dataReport['item'])
            if ai.get('binding') and (ai['binding']['taskRef']!=task_ref or ai['binding']['planVersion']!=plan_version):raise ValueError('V2_AI_TASK_BINDING_INVALID')
        elif result.analysisReport['ai']!=dict(status='NOT_ATTEMPTED',reason='BATCH_ZERO_AI',explanation=None):raise ValueError('BATCH_MODEL_FORBIDDEN')
    def validate_report_parameters(self,report,params):
        self.validate(params)
        if self.single and report['dataReport']['item']['entityKey']!=params['entity']['entityKey']:raise ValueError('V2_ENTITY_BINDING_INVALID')
    def report_view(self,report):
        result=DomainResult.model_validate({k:report[k] for k in DomainResult.model_fields})
        self.validate_publication(result,report['taskRef'],report['planVersion'])
        view=deepcopy(report)
        if self.single and view['dataReport']['item'].get('ruleResult'):
            view['dataReport']['item']['ruleResult'].pop('input',None)
        return view
    def model_receipts(self,report):
        ai=report['analysisReport']['ai']
        return [ai] if ai.get('status')=='AVAILABLE' else []
