"""Scheme B strategy over P3's existing durable create/submit/reconciliation state machine."""
from datetime import datetime,timezone
from contextvars import ContextVar
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import json
from sqlalchemy import select
from commerce_hub.scenarios.s01_backend.requisition_store import requisitions
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.s01_backend.requisition import RequisitionService
from commerce_hub.data.sync.v2 import V2Reader
from commerce_hub.data.sync.v2_catalog import collect_catalog
from commerce_hub.data.projection.v2 import entities
from commerce_hub.scenarios.s01_v2.analysis import analyze
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.contracts import fingerprint


# Proofs belong to one confirmation call, never to the shared service instance.
_voided_operations = ContextVar('s01_v2_voided_operations', default=frozenset())


def operation_version(row):
    return fingerprint(dict(report=row['report_id'],operation=row['operation_id'],
        state=row['state'],content=row['content']))


def comparable(item):
    decision=item.get('decision')
    stable_decision={k:decision.get(k) for k in ['status','horizonDays','leadDays','referenceReplenishmentQuantity','purchasableQuantity','forecastQuantity','horizonBasis']} if decision else None
    result={k:item.get(k) for k in ['sourceTenant','storeId','warehouseId','productId','sku','sourceGrade','quantity',
        'inventory','constraints','formalPurchases','pendingPurchases','sourceSuggestion']}|dict(forecast=(item.get('ruleResult') or {}).get('forecast'),decision=stable_decision)
    if item.get('admissionVersion'):
        basis=item.get('inventoryBasis') or {};cp=basis.get('checkpoint') or {}
        result['admissionBasis']=dict(version=item['admissionVersion'],status=basis.get('status'),residual=basis.get('residual'),
            issues=basis.get('issues'),checkpointVersion=cp.get('version'),checkpointDigest=cp.get('evidenceDigest'))
    return result


class V2RequisitionService(RequisitionService):
    def __init__(self,tasks,policy,client_factory,private_root):
        super().__init__(tasks,policy,client_factory)
        self.private_root=Path(private_root)
    @staticmethod
    def _blocks(row):
        # A failure before ERP creation can be corrected with a new analysis.
        # All sent/possibly-sent operations retain their protection.
        if operation_version(row) in _voided_operations.get():return False
        return row['state']!='BLOCKED' or bool(row['content'].get('erpId') or row['content'].get('payload'))
    def _confirmed_voided(self,actor,row):
        # Only an independently read, exact original order can release exclusion.
        # UNKNOWN/BLOCKED phases and failed reads must keep their protection.
        content=row['content']
        if row['state']!='SUBMITTED' or not content.get('erpId') or not content.get('payload') or self.client_factory is None:return False
        try:
            report=self._source(actor,row['report_id'])
            mapping=self._mapping(report['scope'],report)
            client=self.client_factory(row['operation_id'],lambda:self._authorize(actor,report['scope'],write=False))
            current=client.read_requisition(content['erpId'])
            if str(current.get('id'))!=str(content['erpId']):return False
            self._matches(current,content,mapping)
            if str(current['item_list'][0].get('product_id'))!=str(content['payload']['item_list'][0]['product_id']):return False
            return current.get('status_text')=='已作废'
        except (ERPError,TaskError,OSError,ValueError,TypeError,KeyError):
            return False
    def confirm(self,actor,report_id,command_key,quantity,reason,trace_id):
        report=self._source(actor,report_id)
        with self.engine.connect() as conn:
            rows=self._business_rows(conn,actor,report['dataReport']['item']['entityKey'])
        # Network outside locks; the locked guard compares the entire operation
        # version so a concurrent local change invalidates this readback proof.
        released=frozenset(operation_version(r) for r in rows if r['report_id']!=report_id and self._confirmed_voided(actor,r))
        token=_voided_operations.set(released)
        try:return super().confirm(actor,report_id,command_key,quantity,reason,trace_id)
        finally:_voided_operations.reset(token)
    def _business_rows(self,conn,actor,entity_key,*,lock=False):
        query=select(requisitions).where(requisitions.c.tenant_id==actor.tenant_id,
            requisitions.c.content['entityKey'].as_string()==entity_key).order_by(requisitions.c.created_at)
        if lock:query=query.with_for_update()
        return conn.execute(query).mappings().all()
    def _guard_operation(self,conn,actor,report_id,report,mapping):
        rows=self._business_rows(conn,actor,mapping.entity['entityKey'],lock=True)
        if any(r['report_id']!=report_id and self._blocks(r) for r in rows):
            raise TaskError('BUSINESS_OBJECT_REQUISITION_EXISTS',409)
    def read(self,actor,report_id):
        report=self._source(actor,report_id)
        with self.engine.connect() as conn:
            own=self._row(conn,actor,report_id)
            if own:return self.view(own)
            rows=self._business_rows(conn,actor,report['dataReport']['item']['entityKey'])
        row=next((r for r in rows if self._blocks(r) and not self._confirmed_voided(actor,r)),None)
        return dict(self.view(row),blockedByOtherAnalysis=True) if row else None
    def _source(self,actor,report_id):
        report=self.tasks.read_report(actor,report_id)
        if report['scenarioId']!='S01_V2_SINGLE':raise TaskError('REQUISITION_SOURCE_NOT_ELIGIBLE',422)
        self._authorize(actor,report['scope'],write=False)
        report['dataReport']['acquisition']=report['dataReport']['catalogManifest']['acquisition']
        return report
    def _mapping(self,scope,report):
        item=report['dataReport']['item'];binding=self.registry.opening_binding(item)
        if binding is None:raise TaskError('V2_PROCUREMENT_SCOPE_NOT_AUTHORIZED',403)
        monitor=SimpleNamespace(datasetId=binding.monitor.datasetId,scopeVersion=binding.monitor.scopeVersion,
            importBatchId=binding.monitor.importBatchId,supplierId=item['constraints']['supplierId'],productId=item['productId'])
        return SimpleNamespace(scope=scope,entity=item,monitor=monitor,sku=item['sku'],sourceTenant=item['sourceTenant'],
            sourceStore=item['storeId'],sourceWarehouse=item['warehouseId'],storeName=item['storeName'],warehouseName=item['warehouseName'])
    def _authorize_operation(self,actor,scope,mapping):
        self._authorize(actor,scope)
        if not self.registry.can_write(mapping.entity):raise TaskError('V2_PROCUREMENT_SCOPE_NOT_AUTHORIZED',403)
    def _confirmation_metadata(self,report,mapping):
        item=report['dataReport']['item']
        return dict(entityKey=item['entityKey'],sourceGrade=item['sourceGrade'],sourceQuantity=item['quantity'],
            sourceUncertainties=item['uncertainties'],sourceAcknowledged=True,eligibilityPolicy='s01-v2-scheme-b-v1',
            sourceSuggestionId=(item.get('sourceSuggestion') or {}).get('id'),
            sourceSuggestionNumber=(item.get('sourceSuggestion') or {}).get('recommendation_no'))
    @staticmethod
    def validate_quantity(report,quantity,reason):
        item=report['dataReport']['item'];c=item['constraints']
        if not item['procurementEligibility']['eligible'] or item['sourceGrade'] not in {'RULE_CALCULATED','USABLE_FALLBACK','REFERENCE_ONLY','PLATFORM_REFERENCE'}:
            raise TaskError('REQUISITION_SOURCE_NOT_ELIGIBLE',422)
        if type(quantity) is not int or not 1<=quantity<=100000 or not isinstance(reason,str) or len(reason)>1000:raise TaskError('INVALID_REQUISITION_FIELDS',422)
        if quantity<c['moq'] or quantity%c['orderMultiple']:raise TaskError('MOQ_OR_CARTON_VIOLATION',422)
        if quantity!=item['quantity'] and not reason.strip():raise TaskError('ADJUSTMENT_REASON_REQUIRED',422)
        if Decimal(c['unitPrice'])*quantity<Decimal(c['minimumAmount']):raise TaskError('QUOTE_MINIMUM_AMOUNT_VIOLATION',422)
        return str(item['quantity'])
    def _prepare(self,actor,report,mapping,client,operation,quantity,reason):
        service=self
        root=self.private_root/operation/'revalidation';root.mkdir(parents=True,exist_ok=True)
        budget=root/'budget.json'
        class BudgetCheckpoint:
            def load(self):
                if budget.exists():return dict(requestCount=json.loads(budget.read_text(encoding='utf-8'))['requestCount'])
                return dict(requestCount=0)
            def save(self,value):
                temporary=budget.with_suffix('.part')
                temporary.write_text(json.dumps(dict(requestCount=value['requestCount'])),encoding='utf-8')
                temporary.replace(budget)
        reader=V2Reader(client.config,root,BudgetCheckpoint(),lambda:service._authorize_operation(actor,mapping.scope,mapping),transport=client.transport,request_limit=120)
        if self.registry.owned_only:
            from commerce_hub.data.sync.registered_catalog import collect_registered,registered_entities
            catalog=collect_registered(reader,mapping.sourceTenant,self.registry.read_members(),mapping.entity)
        else:catalog=collect_catalog(reader,mapping.sourceTenant,mapping.entity)
        candidates=entities(catalog,mapping.sourceTenant)
        if self.registry.owned_only:candidates=registered_entities(catalog,candidates)
        fresh=[e for e in candidates if e['entityKey']==mapping.entity['entityKey']]
        if len(fresh)!=1:raise TaskError('V2_LATEST_ENTITY_RELATION_UNRESOLVED',409)
        item=analyze(catalog,fresh[0],reader,opening_binding=self.registry.opening_binding(fresh[0]),requisition_authorized=self.registry.can_write(fresh[0]))
        if comparable(item)!=comparable(mapping.entity):raise TaskError('ANALYSIS_CHANGED_REANALYZE',409)
        current=dict(dataReport=dict(item=item));self.validate_quantity(current,quantity,reason)
        c=item['constraints']
        supplier=reader.resource('supplier-'+c['supplierId'],'/api/v1/suppliers/'+c['supplierId'],detail=True)
        quote=next(q for q in catalog['quotes']['rows'] if str(q['id'])==c['quoteId'])
        if (not supplier['complete'] or len(supplier['rows'])!=1 or str(supplier['rows'][0].get('tenant_id'))!=mapping.sourceTenant
            or str(supplier['rows'][0].get('id'))!=c['supplierId'] or supplier['rows'][0].get('name')!=quote.get('supplier_name')):
            raise TaskError('SUPPLIER_RELATION_UNCONFIRMED',422)
        amount=Decimal(c['unitPrice'])*quantity
        if amount!=amount.quantize(Decimal('.01')):raise TaskError('CURRENCY_PRECISION_UNCONFIRMED',422)
        number='S01-RQ-'+operation[:32]
        payload=dict(order_sn=number,supplier_id=int(c['supplierId']),supplier_name=supplier['rows'][0]['name'],
            warehouse_name=mapping.warehouseName,order_time=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            purchase_currency=c['currency'],amount=float(amount),purchase_user='S01-Human-Confirmed',source_plan_no=operation,
            remark='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP;SALES_REPLENISHMENT;'+mapping.monitor.datasetId,
            item_list=[dict(sku=mapping.sku,product_id=int(mapping.monitor.productId),quantity=quantity,unit_price=float(c['unitPrice']),amount=float(amount))])
        return dict(payload=payload,erpNumber=number,revalidatedAt=datetime.now(timezone.utc).isoformat(),
            revalidationDigest=__import__('commerce_hub.data.contracts',fromlist=['fingerprint']).fingerprint(comparable(item)))
    @staticmethod
    def view(row):
        view=RequisitionService.view(row)
        view.update({k:row['content'].get(k) for k in ['sourceGrade','sourceAcknowledged','sourceUncertainties','sourceSuggestionId','eligibilityPolicy']})
        return view
