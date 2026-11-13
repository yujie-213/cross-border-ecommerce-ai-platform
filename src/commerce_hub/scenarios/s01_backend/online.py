"""Online S01 extension. O01, D01-D04 and B01/B02 keep their existing ownership."""
from copy import deepcopy
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.sync.online import MODE, collect
from commerce_hub.data.sync.online_store import AcquisitionStore
from commerce_hub.data.projection.online import observed, normalize_online
from commerce_hub.data.quality.online import capture_online, verify_asset, calculation_snapshot
from commerce_hub.data.quality.online_store import OnlineSnapshotStore
from commerce_hub.data.quality.observed import capture_observations
from commerce_hub.data.projection.observed import verify_observations
from commerce_hub.data.evidence import locator
from commerce_hub.capabilities.forecasting import propose
from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.scenarios.s01_backend import S01BackendHandler
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.scenarios.s01.natural_explanation import (NATURAL_SEMANTIC_POLICY,
    validate_result_versions,validate_result_explanation)
from commerce_hub.scenarios.s01_supply_inventory import facts_for
from decimal import Decimal


class OnlineS01Handler:
    def __init__(self, mappings, reader_factory, *, fixed=None,provider=None,timeout_seconds=30):
        if not 1 <= len(mappings) <= 20:
            raise ValueError('ONLINE_MAPPING_LIMIT')
        self.mappings = [m.validate_scope() for m in mappings]
        if len({fingerprint(m.scope) for m in self.mappings}) != len(self.mappings):
            raise ValueError('DUPLICATE_ONLINE_MAPPING')
        self.reader_factory, self.fixed = reader_factory, fixed
        self.acquisitions, self.snapshots = AcquisitionStore(), OnlineSnapshotStore()
        self.gateway=ModelGateway(provider,timeout_seconds=timeout_seconds) if provider else None
        self.explanation_mode='natural'
        self.request_cost_reservation=Decimal('.05')
        self.logical_namespace=fingerprint('s01-online-20261113-r1')[:12]

    natural_logical_call=S01BackendHandler.natural_logical_call

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
            scope=deepcopy(m.scope),asOf=None,sourceNature='TEACHING_ERP_OBSERVED',
            displayLabels=dict(sku=m.sku,store=m.storeName,warehouse=m.warehouseName)) for m in self.mappings if m.scope['tenantId'] == tenant_id]
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
            normalization=normalize_online(captures,mapping,receipt,verified)
            asset = capture_online(projection,receipt,verified,normalization)
            def persist(conn):
                self.snapshots.save(conn,row['tenant_id'],row['task_id'],row['acquisition_id'],asset)
                self.acquisitions.finish(conn,row,receipt,asset['snapshotId'])
            context.commit_data(persist)
        result = self.rules_result(asset,parameters.get('_previousReportRef'))
        # A verified identity plus actual collected domains is a legal limited
        # context. Explanations preserve missing baseline/quality as UNKNOWN;
        # unverified identity never sends quantities or model context.
        if self.gateway and asset['manifest']['mappingVerified'] and 'normalization' in asset:
            return S01BackendHandler.explain_result(self,context,result,model_allowed=True)
        context.check()
        self.validate_publication(result,dict(tenantId=row['tenant_id'],taskId=row['task_id']),str(row['plan_version']))
        return result

    @staticmethod
    def rules_result(asset, previous=None):
        verify_asset(asset)
        projection = verify_observations(asset['observationProjection'])
        snapshot = calculation_snapshot(asset)
        acquisition = asset['manifest']['acquisition']
        normalization=asset.get('normalization',{})
        supplied=propose(snapshot)
        calc=snapshot.calculation_allowed
        completeness='BLOCKED' if not calc else 'PARTIAL' if not snapshot.candidates_allowed else 'RULES_ONLY'
        paths=['observedDomains','quality','acquisition']
        if supplied['baseline'] is not None:paths.append('supplyDemand/baseline')
        paths += [f'supplyDemand/candidates/{i}' for i in range(len(supplied['candidates']))]
        data = dict(manifest=asset['manifest'],onlineAsset=asset,
            observedDomains=[d.model_dump(mode='json') for d in projection.domains],
            quality=deepcopy(asset['manifest']['quality']),supplyDemand=supplied,
            scenarioSupplement=dict(inputMode=MODE,sourceMode=MODE,asOf=projection.observedAt.isoformat(),
                procurementEligible=False,realAdmission='BLOCKED',engineeringFixture=False,
                sourceSynthetic=projection.sourceSynthetic,calculationStatus='PASS' if calc else 'BLOCKED',previousReportRef=previous,
                acquisitionId=acquisition['acquisitionId'],mappingVersion=acquisition['mappingVersion']),
            acquisition=acquisition,
            evidence=[locator(asset['snapshotId'],path,source_module={'acquisition':'D01','quality':'D03'}.get(path)
                if 'normalization' in asset else None) for path in paths])
        if normalization.get('input') is not None:
            data['inputProjection']=snapshot.projection.model_dump(mode='json')
        if 'normalization' in asset:
            data['scenarioSupplement'].update(ruleVersion=normalization.get('ruleVersion'),unverifiedRules=normalization.get('assumptions',[]))
        source=normalization.get('input',{}).get('sourceNature','TEACHING_ERP_OBSERVED') if normalization.get('input') else 'TEACHING_ERP_OBSERVED'
        return DomainResult(contractVersion='0.1.0',sourceNature=source,completeness=completeness,
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
                or result.model_copy(update={'analysisReport':expected.analysisReport}) != expected):
                raise ValueError('ONLINE_PUBLICATION_BINDING_REJECTED')
            ai=result.analysisReport.get('ai')
            if ai != expected.analysisReport['ai']:
                binding=dict(taskRef=task_ref,planVersion=str(plan_version),snapshotId=result.snapshotRef,participantId='s01')
                if (not asset_verified_for_ai(result) or ai.get('binding')!=binding
                    or ai.get('provider')!='AUTHORIZED_PROVIDER' or ai.get('semanticPolicy')!=NATURAL_SEMANTIC_POLICY
                    or ai.get('realModelAcceptance')!='REVIEW' or ai.get('supportCatalog')!=facts_for(result)
                    or ai.get('usageStatus') not in {'KNOWN','UNKNOWN','NOT_SENT'}):
                    raise ValueError('ONLINE_AI_BINDING_REJECTED')
                if ai.get('versionBundle'):validate_result_versions(ai,result)
                if ai.get('status')=='AVAILABLE':validate_result_explanation(ai,result)
                elif ai.get('status')!='UNAVAILABLE' or ai.get('explanation') is not None:
                    raise ValueError('ONLINE_AI_BINDING_REJECTED')
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
        if report['dataReport']['scenarioSupplement'].get('inputMode') == MODE:
            ai=report['analysisReport']['ai']
            return [ai] if ai.get('status')=='AVAILABLE' else []
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


def asset_verified_for_ai(result):
    asset=result.dataReport['onlineAsset']
    return asset['manifest']['mappingVerified'] is True and 'normalization' in asset
