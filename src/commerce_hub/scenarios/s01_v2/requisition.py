"""Scheme B strategy over P3's existing durable create/submit/reconciliation state machine."""
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import json
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.s01_backend.requisition import RequisitionService
from commerce_hub.data.sync.v2 import V2Reader
from commerce_hub.data.sync.v2_catalog import collect_catalog
from commerce_hub.data.projection.v2 import entities
from commerce_hub.scenarios.s01_v2.analysis import analyze


def comparable(item):
    decision=item.get('decision')
    stable_decision={k:decision.get(k) for k in ['status','horizonDays','leadDays','referenceReplenishmentQuantity','purchasableQuantity','forecastQuantity','horizonBasis']} if decision else None
    result={k:item.get(k) for k in ['sourceTenant','storeId','warehouseId','productId','sku','sourceGrade','quantity',
        'inventory','constraints','formalPurchases','sourceSuggestion']}|dict(forecast=(item.get('ruleResult') or {}).get('forecast'),decision=stable_decision)
    if item.get('admissionVersion'):
        basis=item.get('inventoryBasis') or {};cp=basis.get('checkpoint') or {}
        result['admissionBasis']=dict(version=item['admissionVersion'],status=basis.get('status'),residual=basis.get('residual'),
            issues=basis.get('issues'),checkpointVersion=cp.get('version'),checkpointDigest=cp.get('evidenceDigest'))
    return result


class V2RequisitionService(RequisitionService):
    def __init__(self,tasks,policy,client_factory,private_root):
        super().__init__(tasks,policy,client_factory)
        self.private_root=Path(private_root)
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
