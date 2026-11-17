"""O01 production handlers. External IO outside locks, results committed with lease/CAS."""
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import insert,select
from commerce_hub.orchestration.contracts import DomainResult
from .common import digest,now,require,redacted,safety
from .tables import steps,manifests
from .service import AfterSales
from .policies import retrieve
from .model import invoke,Advice,Classifications,Explanation


class Handler:
    def __init__(self,job,*,source_reader=None,provider=None):
        require(job in {'evidence','advice'},'ACTION_INVALID')
        self.job=job;self.source_reader=source_reader;self.provider=provider

    def validate(self,parameters):
        if (set(parameters)!={'id','kind','expectedRevision','options'} or parameters['kind']!='CASE'
            or type(parameters['expectedRevision']) is not int or not isinstance(parameters['options'],dict)):
            raise ValueError('B_PARAMETERS_INVALID')
        if parameters['options']:raise ValueError('B_OPTIONS_INVALID')

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
            row=store.get(conn,actor,parameters['kind'],parameters['id'],'b:analyze')
            require(row['revision']==parameters['expectedRevision'],'REVISION_CONFLICT',409)
            body=deepcopy(row['body'])
        snapshot_id=uuid4().hex
        new_body=body;state=row['state']
        if self.job=='evidence':
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
                        previous_evidence=body.get('evidence') or {}
                        evidence=dict(facts=previous_evidence.get('facts',[]),missing=[getattr(error,'code','ERP_READ_FAILED'),'本次读取未核实；已有事实仅保留原观察时间'],
                            observedAt=previous_evidence.get('observedAt'),latestUnverified=True,identity=None,identityCandidates=previous_evidence.get('identityCandidates',[]))
                    body['evidence']=dict(**evidence,snapshotRef=snapshot_id)
                    previous_identity=body.get('identity')
                    refreshed=next((i for i in evidence.get('identityCandidates',[]) if previous_identity
                        and i['lineId']==previous_identity['lineId'] and i['productId']==previous_identity['productId']),None)
                    body['identity']=refreshed or previous_identity or evidence.get('identity')
                    if body['identity'] and not any(i['lineId']==body['identity']['lineId'] and i['productId']==body['identity']['productId'] for i in evidence.get('identityCandidates',[])):
                        body['evidence']['missing'].append('当前关联与最新ERP证据冲突，请重新核实')
                    if evidence.get('title'):body['title']=evidence['title']
                    if evidence.get('customerText'):
                        ref=('customer-voice:'+body['erpVoiceKind']+':'+body['erpVoiceId'] if body.get('erpVoiceId')
                            else 'customer-ticket:'+body['erpTicketId'])
                        if not any(m.get('sourceRef')==ref and m['text']==evidence['customerText'] for m in body['messages']):
                            body['messages'].append(dict(role='CUSTOMER',text=evidence['customerText'],source='OBSERVED',sourceRef=ref,at=evidence['observedAt']))
                    for message in evidence.get('supplementalMessages',[]):
                        if not any(m.get('sourceRef')==message['sourceRef'] and m['text']==message['text'] for m in body['messages']):
                            body['messages'].append(message)
                    if evidence.get('businessDate'):
                        date=evidence['businessDate']
                        body['businessDate']=date+'T00:00:00+08:00' if len(date)==10 else date
                    if evidence.get('platform'):body['platform']=evidence['platform']
                    if evidence.get('region'):body['region']=evidence['region']
                    state='EVIDENCE_PENDING' if not body['identity'] else 'OPEN'
            text=' '.join(m['text'] for m in body['messages'])
            if body.get('identity',{}):
                if body['identity']['category']=='ELECTRONICS' and any(w in text for w in ('尺码','尺寸偏小','size too small')):
                    body['evidence']['missing'].append('客户尺码诉求与已核商品属性冲突，请澄清');state='NEEDS_CLARIFICATION'
            if safety(text):state='ESCALATED'
        elif self.job=='advice':
            require(body.get('identity') and body.get('evidence'),'IDENTITY_UNRESOLVED')
            require(not any('冲突' in x for x in body['evidence'].get('missing',[])),'CLAIM_ATTRIBUTE_CONFLICT')
            policies=store.list(actor,'POLICY',limit=100)['items']
            from .policies import advice_block_reason
            blocked=advice_block_reason(body)
            selected=retrieve(policies,body,body.get('businessDate')) if not blocked else []
            ai=dict(status='NOT_ATTEMPTED',reason=blocked or 'POLICY_NOT_APPLICABLE',output=None)
            if selected:
                data=dict(messages=[dict(role=m['role'],text=redacted(m['text'])) for m in body['messages'][-8:]],
                    identity={k:body['identity'].get(k) for k in ('category','attributes','name')},
                    facts=[dict(ref=f['id'],kind=f['kind'],domain=f['domain'],value=f.get('value'),text=f.get('text')) for f in body['evidence']['facts']],
                    orderLinked=body['identity'].get('orderId') not in (None,'','UNKNOWN'),missing=body['evidence']['missing'],safetySignal=safety(' '.join(m['text'] for m in body['messages'])),policies=selected,omissions=['客户身份与地址','可复用订单号','较早非安全消息'])
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
        context.check()
        def commit(conn):
            completed=conn.execute(select(steps).filter_by(**key)).mappings().first()
            if completed:return DomainResult.model_validate(completed['result'])
            current=store.get(conn,actor,row['kind'],row['id'],'b:analyze',lock=True)
            require(current['revision']==row['revision'],'REVISION_CONFLICT',409)
            if self.job=='advice':
                for ref in body['advice'][-1]['policies']:
                    p=store.get(conn,actor,'POLICY',ref['policyId']);require(p['revision']==ref['version'] and p['state']=='PUBLISHED','POLICY_NO_LONGER_AVAILABLE',409)
            reference=store.save(conn,actor,current,new_body,state)
            manifest_body=dict(sourceNature=row['scope']['sourceNature'],assetKind=row['kind'],assetId=row['id'],assetRevision=row['revision'],inputHash=digest(row['body']),
                domainRef=reference,observedAt=now())
            conn.execute(insert(manifests).values(tenant_id=actor.tenant_id,snapshot_id=snapshot_id,scope=row['scope'],body=manifest_body,content_hash=digest(manifest_body)))
            result=DomainResult(contractVersion='0.2.0',sourceNature=row['scope']['sourceNature'],completeness='PARTIAL',scope=context.task['scope'],snapshotRef=snapshot_id,
                sourceBundleRef=dict(kind='B_INPUT_MANIFEST',id=snapshot_id,version='1',hash=digest(manifest_body)),
                dataReport=dict(manifest=manifest_body),analysisReport=dict(domainKind=row['kind'],domainRef=reference,modelStatus=(body['advice'][-1]['ai']['status'] if self.job=='advice' else 'NOT_REQUESTED')))
            receipts=[body['advice'][-1]['ai']] if self.job=='advice' else []
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
