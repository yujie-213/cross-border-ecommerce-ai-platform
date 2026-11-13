"""Online S01 extension. O01, D01-D04 and B01/B02 keep their existing ownership."""
from copy import deepcopy
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.sync.online import MODE, collect
from commerce_hub.data.sync.online_store import AcquisitionStore
from commerce_hub.data.projection.online import observed
from commerce_hub.data.quality.online import capture_online, verify_asset
from commerce_hub.data.quality.online_store import OnlineSnapshotStore
from commerce_hub.data.quality.observed import capture_observations
from commerce_hub.data.projection.observed import verify_observations
from commerce_hub.data.evidence import locator
from commerce_hub.capabilities.forecasting import propose
from commerce_hub.orchestration.contracts import DomainResult


class OnlineS01Handler:
    def __init__(self, mappings, reader_factory, *, fixed=None):
        if not 1 <= len(mappings) <= 20:
            raise ValueError('ONLINE_MAPPING_LIMIT')
        self.mappings = [m.validate_scope() for m in mappings]
        if len({fingerprint(m.scope) for m in self.mappings}) != len(self.mappings):
            raise ValueError('DUPLICATE_ONLINE_MAPPING')
        self.reader_factory, self.fixed = reader_factory, fixed
        self.acquisitions, self.snapshots = AcquisitionStore(), OnlineSnapshotStore()

    @staticmethod
    def online(parameters):
        return isinstance(parameters,dict) and parameters.get('inputMode') == MODE

    def validate(self, parameters):
        if not self.online(parameters):
            if self.fixed is None: raise ValueError('FIXED_CATALOG_NOT_ENABLED')
            return self.fixed.validate(parameters)
        if set(parameters) - {'inputMode','_previousReportRef'}:
            raise ValueError('INVALID_ONLINE_PARAMETERS')
        previous = parameters.get('_previousReportRef')
        if previous is not None and (not isinstance(previous,dict) or set(previous) != {'tenantId','reportId'}
            or any(not isinstance(v,str) or not 1 <= len(v) <= 64 for v in previous.values())):
            raise ValueError('INVALID_PREVIOUS_REPORT_REFERENCE')

    def validate_scope(self, parameters, scope):
        self.validate(parameters)
        if not self.online(parameters): return self.fixed.validate_scope(parameters, scope)
        if not any(m.scope == scope for m in self.mappings):
            raise ValueError('ONLINE_SCOPE_NOT_MAPPED')
        if parameters.get('_previousReportRef',{}).get('tenantId',scope['tenantId']) != scope['tenantId']:
            raise ValueError('PREVIOUS_REPORT_TENANT_MISMATCH')

    def bind_previous_report(self, parameters, reference):
        self.validate(parameters)
        return dict(parameters, _previousReportRef=deepcopy(reference))

    def options(self, tenant_id):
        choices = [dict(choiceRef='online-'+fingerprint(m.scope),inputMode=MODE,sourceMode=MODE,
            scope=deepcopy(m.scope),asOf=None,sourceNature='TEACHING_ERP_OBSERVED') for m in self.mappings if m.scope['tenantId'] == tenant_id]
        return choices + (self.fixed.options(tenant_id) if self.fixed else [])

    def run(self, context, parameters):
        self.validate_scope(parameters,context.task['scope'])
        if not self.online(parameters): return self.fixed.run(context,parameters)
        mapping = next(m for m in self.mappings if m.scope == context.task['scope'])
        request_digest = fingerprint(dict(scope=mapping.scope,parameters=parameters,mappingVersion=mapping.version))
        row = context.commit_data(lambda conn:self.acquisitions.begin(conn,context.task,context.lease.attempt,request_digest))
        if row['state'] == 'CAPTURED':
            asset = context.commit_data(lambda conn:self.snapshots.read(conn,row['tenant_id'],row['task_id'],row['snapshot_ref']))
        else:
            reader = self.reader_factory(context,row['acquisition_id'])
            captures, receipt = collect(reader,mapping,context,row['acquisition_id'])
            receipt.update(taskRef=dict(tenantId=row['tenant_id'],taskId=row['task_id']),
                planVersion=str(row['plan_version']), delivery=row['delivery'], requestDigest=request_digest)
            projection, verified = observed(captures,mapping,receipt)
            asset = capture_online(projection,receipt,verified)
            def persist(conn):
                self.snapshots.save(conn,row['tenant_id'],row['task_id'],row['acquisition_id'],asset)
                self.acquisitions.finish(conn,row,receipt,asset['snapshotId'])
            context.commit_data(persist)
        result = self.rules_result(asset,parameters.get('_previousReportRef'))
        context.check()
        self.validate_publication(result,dict(tenantId=row['tenant_id'],taskId=row['task_id']),str(row['plan_version']))
        return result

    @staticmethod
    def rules_result(asset, previous=None):
        verify_asset(asset)
        projection = verify_observations(asset['observationProjection'])
        snapshot = capture_observations(projection)
        acquisition = asset['manifest']['acquisition']
        data = dict(manifest=asset['manifest'],onlineAsset=asset,
            observedDomains=[d.model_dump(mode='json') for d in projection.domains],
            quality=[i.model_dump() for i in snapshot.issues],supplyDemand=propose(snapshot),
            scenarioSupplement=dict(inputMode=MODE,sourceMode=MODE,asOf=projection.observedAt.isoformat(),
                procurementEligible=False,realAdmission='BLOCKED',engineeringFixture=False,
                sourceSynthetic=projection.sourceSynthetic,calculationStatus='BLOCKED',previousReportRef=previous,
                acquisitionId=acquisition['acquisitionId'],mappingVersion=acquisition['mappingVersion']),
            acquisition=acquisition,
            evidence=[locator(asset['snapshotId'],path) for path in ['observedDomains','quality','acquisition']])
        return DomainResult(contractVersion='0.1.0',sourceNature='TEACHING_ERP_OBSERVED',completeness='BLOCKED',
            scope=deepcopy(projection.scope),snapshotRef=asset['snapshotId'],dataReport=data,
            analysisReport=dict(ai=dict(status='NOT_ATTEMPTED',reason='MODEL_NOT_ENABLED')))

    def validate_publication(self,result,task_ref,plan_version):
        if result.dataReport.get('scenarioSupplement',{}).get('inputMode') != MODE:
            if self.fixed is None: raise ValueError('FIXED_CATALOG_NOT_ENABLED')
            return self.fixed.validate_publication(result,task_ref,plan_version)
        try:
            acquisition=result.dataReport['acquisition']
            expected=self.rules_result(result.dataReport['onlineAsset'],result.dataReport['scenarioSupplement'].get('previousReportRef'))
            if (acquisition['taskRef'] != task_ref or acquisition['planVersion'] != str(plan_version)
                or result != expected):
                raise ValueError('ONLINE_PUBLICATION_BINDING_REJECTED')
        except (KeyError,TypeError,AttributeError):
            raise ValueError('ONLINE_PUBLICATION_BINDING_REJECTED') from None

    def validate_report_parameters(self,report,parameters):
        if not self.online(parameters):
            if self.fixed is None: raise ValueError('FIXED_CATALOG_NOT_ENABLED')
            return self.fixed.validate_report_parameters(report,parameters)
        receipt=report['dataReport']['acquisition']
        if receipt['requestDigest'] != fingerprint(dict(scope=report['scope'],parameters=parameters,mappingVersion=receipt['mappingVersion'])):
            raise ValueError('ONLINE_REPORT_INPUT_BINDING_REJECTED')

    def model_receipts(self,report):
        return self.fixed.model_receipts(report) if report['dataReport']['scenarioSupplement'].get('inputMode') != MODE and self.fixed else []

    def report_view(self,report):
        if report['dataReport']['scenarioSupplement'].get('inputMode') != MODE:
            if self.fixed is None: raise ValueError('FIXED_CATALOG_NOT_ENABLED')
            return self.fixed.report_view(report)
        result=DomainResult.model_validate({k:report[k] for k in DomainResult.model_fields})
        self.validate_publication(result,report['taskRef'],report['planVersion'])
        view=deepcopy(report)
        view['dataReport']={k:deepcopy(report['dataReport'][k]) for k in
            ('observedDomains','quality','supplyDemand','scenarioSupplement','acquisition','evidence')}
        return view
