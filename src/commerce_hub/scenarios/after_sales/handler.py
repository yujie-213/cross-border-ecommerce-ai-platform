"""O01 production handlers. External IO outside locks, results committed with lease/CAS."""
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import insert,select
from commerce_hub.capabilities.metrics.after_sales import analyze,validate_records,DEFAULT_RULE
from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.orchestration.service import TaskError
from .common import SOURCE,digest,now,require,redacted,safety,timestamp
from datetime import timedelta
from .tables import assets,steps,manifests
from .service import AfterSales
from .policies import retrieve
from .model import invoke,Advice,Classifications,Explanation


class Handler:
    def __init__(self,job,*,source_reader=None,provider=None):
        self.job=job;self.source_reader=source_reader;self.provider=provider

    def validate(self,parameters):
        if (set(parameters)!={'id','kind','expectedRevision','options'} or parameters['kind'] not in {'CASE','DATASET'}
            or type(parameters['expectedRevision']) is not int or not isinstance(parameters['options'],dict)):
            raise ValueError('B_PARAMETERS_INVALID')
        permitted={'analysis':{'windows','asOf','rule','ai','compareReportId'},'evidence':set(),'advice':set(),'validate':set(),'binding':{'teachingIdentity','erpIdentity','validUntil'}}[self.job]
        if set(parameters['options'])-permitted:raise ValueError('B_OPTIONS_INVALID')

    def run(self,context,parameters):
        domain=AfterSales(context.service,self.source_reader,self.provider);store=domain.store
        actor=context.principal;tid=context.task['task_id'];key=dict(tenant_id=actor.tenant_id,task_id=tid,step=self.job)
        fp=digest(parameters)
        context.check()
        with store.engine.begin() as conn:
            completed=conn.execute(select(steps).filter_by(**key)).mappings().first()
            if completed:
                require(completed['input_hash']==fp,'STEP_CONFLICT',409)
                return DomainResult.model_validate(completed['result'])
            row=store.get(conn,actor,parameters['kind'],parameters['id'],'b:binding:manage' if self.job=='binding' else 'b:dataset:manage' if self.job=='validate' else 'b:analyze')
            require(row['revision']==parameters['expectedRevision'],'REVISION_CONFLICT',409)
            body=deepcopy(row['body']);records=None;previous=None
            if row['kind']=='DATASET':records=domain.records(conn,row)
            elif body.get('datasetId'):
                dataset=store.get(conn,actor,'DATASET',body['datasetId'])
                require(dataset['state']=='ACTIVE','DATASET_NOT_VERIFIED')
                records=domain.records(conn,dataset)
            compare=parameters['options'].get('compareReportId')
            if compare:
                previous=store.get(conn,actor,'REPORT',compare)
                previous_ds=store.get(conn,actor,'DATASET',previous['body']['datasetId'])
                require(previous_ds['scope']['sourceNature']==row['scope']['sourceNature'] and previous_ds['scope']['sourceTenant']==row['scope']['sourceTenant']
                    and previous_ds['body']['manifest']['datasetId']==body['manifest']['datasetId'],'COMPARISON_SOURCE_MISMATCH')
        snapshot_id=uuid4().hex
        new_body=body;state=row['state'];created_report=None;created_binding=None
        if self.job=='binding':
            require(row['state']=='ACTIVE' and self.source_reader is not None,'DATASET_NOT_VERIFIED')
            options=parameters['options'];domain.validate_identity(options['teachingIdentity']);domain.validate_identity(options['erpIdentity'])
            ti=options['teachingIdentity']
            require(ti['sourceTenant']==row['scope']['sourceTenant'] and any(r['type']=='line' and r['productId']==ti['productId'] and r['sku']==ti['sku'] and r['storeId']==ti['storeId']
                and (ti['warehouseMode']=='ALL_STORE_WAREHOUSES' or r['warehouseId'] in ti['warehouseIds']) for r in records),'MAPPING_IDENTITY_MISMATCH')
            require(timestamp(now())<timestamp(options['validUntil'])<=timestamp(now())+timedelta(days=30),'BINDING_VALIDITY_INVALID')
            verified=self.source_reader.verify_mapping(options['erpIdentity'],context.check)
            created_binding=dict(**options,**verified,principalId=actor.principal_id,datasetId=row['id'],datasetVersion=body['manifest']['version'],
                datasetHash=body['readbackHash'],mappingVersion=digest(options),validFrom=now())
        elif self.job=='validate':
            issues=[]
            try:
                validate_records(records,body['manifest'])
            except TaskError as error:issues.append(error.code)
            # Independent connection and rehash, after the first read transaction ended.
            with store.engine.begin() as conn:
                independently=store.get(conn,actor,'DATASET',row['id'],'b:dataset:manage')
                replay=domain.records(conn,independently)
                require(digest(replay)==digest(records)==body.get('sealedHash'),'READBACK_HASH_MISMATCH')
            body.update(validation=dict(at=now(),count=len(records),hash=digest(records),independentReadback=True),issues=issues)
            body['readbackHash']=digest(replay) if not issues else None
            state='QUARANTINED' if issues else 'READBACK_VERIFIED'
        elif self.job=='evidence':
            if body.get('erpStoreName'):
                require(self.source_reader is not None,'ERP_SOURCE_NOT_CONFIGURED',503)
                if not body.get('erpTicketId') and not body.get('erpVoiceId'):
                    body['erpDiscovery']=self.source_reader.discover(body['erpStoreName'],context.check)
                    state='OPEN'
                else:
                    try:
                        evidence=(self.source_reader.voice_evidence(body['erpVoiceId'],body['erpVoiceKind'],body['erpStoreName'],context.check,tid)
                            if body.get('erpVoiceId') else self.source_reader.evidence(body['erpTicketId'],body['erpStoreName'],context.check,tid))
                    except Exception as error:
                        previous=body.get('evidence') or {}
                        evidence=dict(facts=previous.get('facts',[]),missing=[getattr(error,'code','ERP_READ_FAILED'),'本次读取未核实；已有事实仅保留原观察时间'],
                            observedAt=previous.get('observedAt'),latestUnverified=True,identity=None,identityCandidates=previous.get('identityCandidates',[]))
                    body['evidence']=dict(**evidence,snapshotRef=snapshot_id)
                    body['identity']=body.get('identity') or evidence.get('identity')
                    if body['identity'] and not any(i['lineId']==body['identity']['lineId'] and i['productId']==body['identity']['productId'] for i in evidence.get('identityCandidates',[])):
                        body['evidence']['missing'].append('当前关联与最新ERP证据冲突，请重新核实')
                    if evidence.get('title'):body['title']=evidence['title']
                    if evidence.get('customerText'):
                        ref='customer-voice:'+body['erpVoiceKind']+':'+body['erpVoiceId']
                        if not any(m.get('sourceRef')==ref and m['text']==evidence['customerText'] for m in body['messages']):
                            body['messages'].append(dict(role='CUSTOMER',text=evidence['customerText'],source='OBSERVED',sourceRef=ref,at=evidence['observedAt']))
                    if evidence.get('businessDate'):
                        date=evidence['businessDate']
                        body['businessDate']=date+'T00:00:00+08:00' if len(date)==10 else date
                    if evidence.get('platform'):body['platform']=evidence['platform']
                    state='EVIDENCE_PENDING' if not body['identity'] else 'OPEN'
            elif records is not None:
                lines=[r for r in records if r['type']=='line' and (not body.get('orderId') or r['orderId']==body['orderId'])]
                candidates=[]
                for line in lines[:20]:
                    product=next(r for r in records if r['type']=='product' and r['id']==line['productId'])
                    candidates.append(dict(**{k:line[k] for k in ('orderId','productId','sku','storeId','warehouseId')},lineId=line['id'],category=product['category'],attributes=product['attributes'],name=product['name'],source='SIMULATED'))
                if not body.get('identity') and len(candidates)==1:body['identity']=candidates[0]
                identity=body.get('identity');facts=[]
                if identity:
                    lids={identity['lineId']}
                    for r in records:
                        if r.get('lineId') in lids and r['type'] in {'shipment','return'} or r['type']=='order' and r['id']==identity['orderId']:
                            facts.append(dict(id=r['id'],kind='SIMULATED',domain=r['type'],value=r,sourceRef=r['id'],observedAt=now()))
                body['evidence']=dict(facts=facts,missing=[] if identity else ['请选择本订单中受影响的商品'],identityCandidates=candidates,snapshotRef=snapshot_id,observedAt=now(),sourceNature=SOURCE)
                state='OPEN' if identity else 'NEEDS_CLARIFICATION'
            else:
                body['evidence']=dict(facts=[],missing=['未关联获准的订单或资料'],snapshotRef=snapshot_id,observedAt=now(),identityCandidates=[])
                state='NEEDS_CLARIFICATION'
            text=' '.join(m['text'] for m in body['messages'])
            if body.get('identity',{}):
                if body['identity']['category']=='ELECTRONICS' and any(w in text for w in ('尺码','尺寸偏小','size too small')):
                    body['evidence']['missing'].append('客户尺码诉求与已核商品属性冲突，请澄清');state='NEEDS_CLARIFICATION'
            if safety(text):state='ESCALATED'
        elif self.job=='advice':
            require(body.get('identity') and body.get('evidence'),'IDENTITY_UNRESOLVED')
            require(not any('冲突' in x for x in body['evidence'].get('missing',[])),'CLAIM_ATTRIBUTE_CONFLICT')
            policies=store.list(actor,'POLICY',limit=100)['items']
            selected=retrieve(policies,body,body.get('businessDate')) if body['identity'].get('category') in {'APPAREL','ELECTRONICS'} and body['messages'] and body['evidence']['facts'] and not body['evidence'].get('latestUnverified') else []
            ai=dict(status='NOT_ATTEMPTED',reason='POLICY_NOT_APPLICABLE',output=None)
            if selected:
                data=dict(messages=[dict(role=m['role'],text=redacted(m['text'])) for m in body['messages'][-8:]],
                    identity={k:body['identity'].get(k) for k in ('category','attributes','name')},
                    facts=[dict(ref=f['id'],kind=f['kind'],value=f.get('value'),text=f.get('text')) for f in body['evidence']['facts']],
                    missing=body['evidence']['missing'],safetySignal=safety(' '.join(m['text'] for m in body['messages'])),policies=selected,omissions=['客户身份与地址','可复用订单号','较早非安全消息'])
                ai=invoke(context,self.provider,'b.case.advice.v1',data,Advice,'advice',snapshot_id=body['evidence']['snapshotRef'])
            feedback_ai=None
            if body.get('erpVoiceId'):
                feedback=[dict(feedbackId=f['id'],text=f['text']) for f in body['evidence']['facts'] if f['domain']=='feedback' and f.get('text')]
                classifications=invoke(context,self.provider,'b.feedback.classify.v1',dict(feedback=feedback,taxonomy=sorted(__import__('commerce_hub.scenarios.after_sales.model',fromlist=['LABELS']).LABELS)),Classifications,'voice-classify',snapshot_id=body['evidence']['snapshotRef'])
                explanation=invoke(context,self.provider,'b.experience.explain.v1',dict(feedback=feedback,identity=body['identity'],
                    facts=body['evidence']['facts'],missing=body['evidence']['missing'],factRefs=[f['id'] for f in body['evidence']['facts']]),Explanation,'voice-explain',snapshot_id=body['evidence']['snapshotRef'])
                feedback_ai=dict(classifications=classifications,analysis=explanation)
            advice=dict(version=len(body['advice'])+1,caseRevision=row['revision']+1,snapshotRef=body['evidence']['snapshotRef'],policies=selected,ai=ai,at=now())
            if feedback_ai:advice['feedbackAI']=feedback_ai
            body['advice'].append(advice);state='REVIEW_PENDING' if ai['status']=='AVAILABLE' else 'EVIDENCE_PENDING'
            if safety(' '.join(m['text'] for m in body['messages'])):state='ESCALATED'
        else:
            options=parameters['options'];manifest=body['manifest']
            metrics=analyze(records,manifest,options.get('windows',manifest['windows']),options.get('asOf',manifest['asOf']),options.get('rule',DEFAULT_RULE))
            lines_by_id={r['id']:r for r in records if r['type']=='line'}
            products_by_id={r['id']:r for r in records if r['type']=='product'}
            feedback=[]
            for r in records:
                if r['type']!='feedback':continue
                line=lines_by_id.get(r.get('lineId'));product=products_by_id.get(line['productId']) if line else None
                feedback.append(dict(feedbackId=r['id'],text=redacted(r['text']),lineId=r.get('lineId'),orderId=r['orderId'],channel=r.get('channel','UNKNOWN'),
                    productId=product['id'] if product else None,productName=product['name'] if product else None,sku=product['sku'] if product else None))
            classifications=[];receipts=[]
            for offset in range(0,len(feedback),5):
                context.check();batch=feedback[offset:offset+5]
                ai=invoke(context,self.provider if options.get('ai') else None,'b.feedback.classify.v1',dict(feedback=batch,taxonomy=sorted(__import__('commerce_hub.scenarios.after_sales.model',fromlist=['LABELS']).LABELS)),Classifications,str(offset),snapshot_id=snapshot_id)
                receipts.append(ai)
                classifications.extend(ai['output']['items'] if ai['status']=='AVAILABLE' else [dict(feedbackId=f['feedbackId'],labels=['UNKNOWN'],span='',reason=ai['reason']) for f in batch])
            fact_refs=[f"metric:{item['productId']}:{i}:{g['numerator']}/{g['denominator']}" for item in metrics['items'] for i,g in enumerate(item['groups'])]
            explanation=invoke(context,self.provider if options.get('ai') else None,'b.experience.explain.v1',dict(metrics=metrics,factRefs=fact_refs),Explanation,'explain',snapshot_id=snapshot_id)
            created_report=dict(datasetId=row['id'],datasetVersion=manifest['version'],snapshotRef=snapshot_id,
                metrics=metrics,feedback=feedback,classifications=classifications,classificationCorrections=[],classificationVersion='taxonomy-v1',
                ai=explanation,classificationReceipts=receipts,limitations=['中台独立教学数据，不是ERP原生交易','异常阈值仅为待调查线索'],
                ruleVersion=metrics['rule']['version'],inputHash=digest(records),createdAt=now())
            if previous:
                old=previous['body'];old_items={(i['productId'],i['sku'],i['storeId']):i for i in old['metrics']['items']}
                comparable=old['metrics']['windows']==metrics['windows'] and old['metrics']['rule']['observationDays']==metrics['rule']['observationDays']
                created_report['comparison']=dict(reportId=previous['id'],reportVersion=previous['revision'],datasetVersion=old['datasetVersion'],
                    comparable=comparable,changes=dict(datasetVersionChanged=old['datasetVersion']!=manifest['version'],inputChanged=old['inputHash']!=digest(records),
                        ruleChanged=old['metrics']['rule']!=metrics['rule'],windowChanged=old['metrics']['windows']!=metrics['windows']),
                    items=[dict(productId=i['productId'],sku=i['sku'],previous=old_items.get((i['productId'],i['sku'],i['storeId'])),current=i) for i in metrics['items']],
                    limitation='仅同来源身份、相同选择窗与观察周期可比较数量；版本差异不是自动归因')
        context.check()
        def commit(conn):
            completed=conn.execute(select(steps).filter_by(**key)).mappings().first()
            if completed:return DomainResult.model_validate(completed['result'])
            current=store.get(conn,actor,row['kind'],row['id'],'b:binding:manage' if self.job=='binding' else 'b:dataset:manage' if self.job=='validate' else 'b:analyze',lock=True)
            require(current['revision']==row['revision'],'REVISION_CONFLICT',409)
            if previous:
                checked=store.get(conn,actor,'REPORT',previous['id'])
                require(checked['revision']==previous['revision'],'COMPARISON_CHANGED',409)
            require(self.job not in {'analysis','binding'} or current['state']=='ACTIVE','DATASET_NOT_VERIFIED')
            if self.job=='advice':
                for ref in body['advice'][-1]['policies']:
                    p=store.get(conn,actor,'POLICY',ref['policyId']);require(p['revision']==ref['version'] and p['state']=='PUBLISHED','POLICY_NO_LONGER_AVAILABLE',409)
            reference=(store.create(conn,actor,'BINDING',created_binding,row['scope'],state='ACTIVE') if created_binding else
                store.create(conn,actor,'REPORT',created_report,row['scope'],state='READY') if created_report else store.save(conn,actor,current,new_body,state))
            manifest_body=dict(sourceNature=row['scope']['sourceNature'],assetKind=row['kind'],assetId=row['id'],assetRevision=row['revision'],inputHash=digest(records) if records is not None else digest(row['body']),
                domainRef=reference,observedAt=now())
            conn.execute(insert(manifests).values(tenant_id=actor.tenant_id,snapshot_id=snapshot_id,scope=row['scope'],body=manifest_body,content_hash=digest(manifest_body)))
            result=DomainResult(contractVersion='0.2.0',sourceNature=row['scope']['sourceNature'],completeness='PARTIAL',scope=context.task['scope'],snapshotRef=snapshot_id,
                sourceBundleRef=dict(kind='B_INPUT_MANIFEST',id=snapshot_id,version='1',hash=digest(manifest_body)),
                dataReport=dict(manifest=manifest_body),analysisReport=dict(domainKind='BINDING' if created_binding else 'REPORT' if created_report else row['kind'],domainRef=reference,modelStatus=(created_report['ai']['status'] if created_report else body['advice'][-1]['ai']['status'] if self.job=='advice' else 'NOT_REQUESTED')))
            receipts=([created_report['ai']]+created_report['classificationReceipts'] if created_report else [body['advice'][-1]['ai']] if self.job=='advice' else [])
            result.analysisReport['modelReceipts']=[r for r in receipts if r.get('auditRef')]
            conn.execute(insert(steps).values(**key,input_hash=fp,result=result.model_dump(mode='json')))
            return result
        return context.commit_data(commit)

    def validate_result(self,result):
        require(isinstance(result,DomainResult) and result.contractVersion=='0.2.0' and result.sourceBundleRef,'INVALID_B_RESULT')

    def report_view(self,payload):
        return {k:payload[k] for k in ('contractVersion','sourceNature','completeness','scope','snapshotRef','sourceBundleRef','taskRef','reportRef','dataReport','analysisReport')}

    def validate_report_parameters(self,payload,parameters):
        m=payload['dataReport']['manifest']
        if m['assetId']!=parameters['id'] or m['assetKind']!=parameters['kind'] or m['assetRevision']!=parameters['expectedRevision']:
            raise ValueError('B_REPORT_INPUT_MISMATCH')

    def model_receipts(self,payload):
        return payload['analysisReport'].get('modelReceipts',[])
