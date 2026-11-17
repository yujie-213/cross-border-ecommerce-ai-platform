"""B domain commands. Business sources and human decisions stay separate."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from .common import WORKSPACE,now,timestamp,require,safety,scope,digest
from .store import Store
from .tables import assets
from .policies import applicable,validate_policy


class AfterSales:
    def __init__(self,tasks,source_reader=None,provider=None):
        self.tasks=tasks;self.store=Store(tasks);self.source_reader=source_reader;self.provider=provider
        self.store.source_visible=self.source_visible

    def source_visible(self,conn,row):
        if row['kind']=='POLICY':return True
        if row['scope']['sourceNature']!='TEACHING_ERP_OBSERVED' or row['kind'] not in {'CASE','INVESTIGATION','RISK'}:return False
        if not self.source_reader:return False
        b=row['body']
        if row['kind']=='CASE':return not hasattr(self.source_reader,'allows_case') or self.source_reader.allows_case(b)
        if row['kind']=='RISK':
            if hasattr(self.source_reader,'allows_identity') and not self.source_reader.allows_identity(b['identity']):return False
            kind,rid='INVESTIGATION',b['investigationId']
        elif row['kind']=='INVESTIGATION':kind,rid=b['origin']['kind'],b['origin']['id']
        else:return False
        origin=conn.execute(select(assets).filter_by(tenant_id=row['tenant_id'],kind=kind,id=rid)).mappings().first()
        return bool(origin and self.source_visible(conn,origin))

    def source_inbox(self,actor,store,kind,date_from=None,date_to=None,full=False):
        require(self.source_reader is not None,'ERP_SOURCE_NOT_CONFIGURED',503)
        expected=self.source_reader._store(store)
        resource=scope(actor.tenant_id,'CASE',source='TEACHING_ERP_OBSERVED',source_tenant=expected['sourceTenant'])
        def check():
            with self.store.engine.begin() as conn:
                self.store.authorize(conn,actor,'b:read',resource)
                self.store.authorize(conn,actor,'b:case:write',resource)
        check()
        result=self.source_reader.inbox(store,kind,check,date_from,date_to,full=True) if full else self.source_reader.inbox(store,kind,check,date_from,date_to)
        check()
        return result

    def return_analysis(self,actor,store,end_date=None,window_days=7):
        require(self.source_reader is not None,'ERP_SOURCE_NOT_CONFIGURED',503)
        expected=self.source_reader._store(store)
        resource=scope(actor.tenant_id,'CASE',source='TEACHING_ERP_OBSERVED',source_tenant=expected['sourceTenant'])
        def check():
            with self.store.engine.begin() as conn:
                self.store.authorize(conn,actor,'b:read',resource)
                self.store.authorize(conn,actor,'b:case:write',resource)
        check()
        result=self.source_reader.return_analysis(store,check,end_date=end_date,window_days=window_days)
        check()
        return result

    def create_return_case(self,actor,key,store,return_id,sku=None):
        from .analysis_evidence import return_evidence
        require(isinstance(return_id,str) and return_id.isdigit(),'RETURN_ID_INVALID')
        data=dict(store=store,returnId=return_id,sku=sku)
        snapshot=self.return_analysis(actor,store)
        proof=return_evidence(snapshot,return_id,sku);identity=proof['identity']
        resource=scope(actor.tenant_id,'CASE',source='TEACHING_ERP_OBSERVED',source_tenant=identity['sourceTenant'])
        body=dict(title=proof['title'],messages=[dict(role='CUSTOMER',text=proof['customerText'],source='ERP_RETURN_REASON',at=proof.get('businessDate') or snapshot['observedAt'])],
            region=proof['region'],platform=proof['platform'],language='zh',businessDate=proof.get('businessDate'),identity=identity,
            linkHistory=[],evidence=proof,advice=[],reviews=[],erpStoreName=store,erpReturnId=return_id,erpReturnSku=identity['sku'],sourceMembership=[identity])
        def operation(conn):
            old=conn.execute(select(assets).filter_by(tenant_id=actor.tenant_id,kind='CASE',workspace=WORKSPACE)
                .where(assets.c.body['erpReturnId'].as_string()==return_id,
                    assets.c.body['erpStoreName'].as_string()==store,
                    assets.c.body['identity']['sku'].as_string()==identity['sku']).limit(1)).mappings().first()
            if old:
                row=self.store.get(conn,actor,'CASE',old['id']);return dict(kind='CASE',id=row['id'],revision=row['revision'],state=row['state'])
            return dict(kind='CASE',**self.store.create(conn,actor,'CASE',body,resource,state='OPEN'))
        return self.store.command(actor,key,'create-return-case',data,operation)

    def create_monitor_case(self,actor,key,store,sku,end_date=None,window_days=7):
        from .analysis_evidence import monitor_evidence
        result=self.return_analysis(actor,store,end_date,window_days)
        proof=monitor_evidence(result,sku,self.source_reader.members(store));identity=proof['identity']
        resource=scope(actor.tenant_id,'CASE',source='TEACHING_ERP_OBSERVED',source_tenant=identity['sourceTenant'])
        body=dict(title=proof['title'],messages=[],region='UNKNOWN',platform='ERP',language='zh',businessDate=proof['businessDate'],
            identity=identity,linkHistory=[],evidence=proof,advice=[],reviews=[],erpStoreName=store,erpMonitorSku=sku,
            erpMonitorWindow=dict(endDate=result['window']['endDate'],windowDays=window_days),sourceMembership=[identity])
        data=dict(store=store,sku=sku,endDate=end_date,windowDays=window_days)
        def operation(conn):
            old=conn.execute(select(assets).filter_by(tenant_id=actor.tenant_id,kind='CASE',workspace=WORKSPACE)
                .where(assets.c.body['erpMonitorSku'].as_string()==sku,assets.c.body['erpStoreName'].as_string()==store,
                    assets.c.body['erpMonitorWindow']['endDate'].as_string()==result['window']['endDate'],
                    assets.c.body['erpMonitorWindow']['windowDays'].as_integer()==window_days).limit(1)).mappings().first()
            if old:
                row=self.store.get(conn,actor,'CASE',old['id']);return dict(kind='CASE',id=row['id'],revision=row['revision'],state=row['state'])
            return dict(kind='CASE',**self.store.create(conn,actor,'CASE',body,resource,state='OPEN'))
        return self.store.command(actor,key,'create-monitor-case',data,operation)

    def create_case(self,actor,key,data):
        require(not data.get('datasetId') and data.get('erpStoreName') and (data.get('erpTicketId') or data.get('erpVoiceId')),'ERP_SOURCE_REQUIRED')
        require(self.source_reader is not None,'ERP_SOURCE_NOT_CONFIGURED',503)
        if data.get('businessDate'):timestamp(data['businessDate'])
        membership=[]
        if data.get('erpStoreName') and self.source_reader and getattr(self.source_reader,'owned_provider',None) is not None:
            require(data.get('erpTicketId') or data.get('erpVoiceId'),'OWNED_SOURCE_RECORD_REQUIRED')
            expected=self.source_reader._store(data['erpStoreName'])
            def check_source():
                with self.store.engine.begin() as conn:
                    self.store.authorize(conn,actor,'b:case:write',scope(actor.tenant_id,'CASE',source='TEACHING_ERP_OBSERVED',source_tenant=expected['sourceTenant']))
            check_source()
            proof=(self.source_reader.voice_evidence(data['erpVoiceId'],data['erpVoiceKind'],data['erpStoreName'],check_source,'admission-'+uuid4().hex)
                if data.get('erpVoiceId') else self.source_reader.evidence(data['erpTicketId'],data['erpStoreName'],check_source,'admission-'+uuid4().hex))
            membership=proof['identityCandidates']
        def operation(conn):
            body=dict(title=data['title'],messages=[dict(role='CUSTOMER',text=data['message'],source='CLAIM',at=now(),actor=actor.principal_id)] if data['message'] else [],
                region=data['region'],platform=data['platform'],language=data['language'],businessDate=data.get('businessDate'),
                identity=None,linkHistory=[],evidence=None,advice=[],reviews=[])
            body['orderId']=data.get('orderId')
            if membership:body['sourceMembership']=membership
            body['erpTicketId']=data.get('erpTicketId');body['erpStoreName']=data.get('erpStoreName')
            body['erpVoiceId']=data.get('erpVoiceId');body['erpVoiceKind']=data.get('erpVoiceKind')
            require(not body['erpVoiceId'] or body['erpVoiceKind'] in {'reviews','feedback'} and body['erpStoreName'] and not body['erpTicketId'],'SOURCE_MIXED')
            source='TEACHING_ERP_OBSERVED'
            if body['erpStoreName']:
                require(self.source_reader is not None,'ERP_SOURCE_NOT_CONFIGURED',503)
                self.source_reader._store(body['erpStoreName'])
            if body['erpStoreName'] and (body['erpTicketId'] or body['erpVoiceId']):
                query=select(assets.c.id).filter_by(tenant_id=actor.tenant_id,kind='CASE',workspace=WORKSPACE).where(
                    assets.c.body['erpStoreName'].as_string()==body['erpStoreName'])
                if body['erpTicketId']:query=query.where(assets.c.body['erpTicketId'].as_string()==body['erpTicketId'])
                else:query=query.where(assets.c.body['erpVoiceId'].as_string()==body['erpVoiceId'],assets.c.body['erpVoiceKind'].as_string()==body['erpVoiceKind'])
                existing=conn.execute(query.limit(1)).scalar()
                if existing:
                    row=self.store.get(conn,actor,'CASE',existing)
                    return dict(kind='CASE',id=existing,revision=row['revision'],state=row['state'])
            result=self.store.create(conn,actor,'CASE',body,scope(actor.tenant_id,'CASE',source=source,source_tenant=self.source_reader._store(body['erpStoreName'])['sourceTenant']),state='ESCALATED' if safety(data['message']) else 'OPEN')
            return dict(kind='CASE',**result)
        return self.store.command(actor,key,'create-case',data,operation)

    def create_policy(self,actor,key,data):
        validate_policy(data)
        return self.store.command(actor,key,'create-policy',data,lambda conn:dict(kind='POLICY',**self.store.create(conn,actor,'POLICY',data,scope(actor.tenant_id,'POLICY'),state='DRAFT')))

    def mutate(self,actor,kind,rid,action,key,revision,data):
        if kind=='CASE' and action=='reviews' and data.get('decision') in {'ACCEPT','MANUAL'}:
            with self.store.engine.begin() as conn:
                row=self.store.get(conn,actor,kind,rid,'b:case:review')
            if row['body'].get('erpVoiceId'):
                from .confirmation import Confirmation
                return Confirmation(self).confirm(actor,rid,key,revision,data)
        allowed={'CASE':{'messages','links','reviews'},'POLICY':{'submit-review','publish','revoke','new-version'},
            'INVESTIGATION':{'entries','evidence'},'RISK':{'decisions'}}
        require(action in allowed.get(kind,set()),'ACTION_INVALID')
        permission={'CASE':'b:case:review' if action=='reviews' else 'b:case:write',
            'POLICY':'b:policy:publish' if action in {'publish','revoke'} else 'b:policy:write',
            'INVESTIGATION':'b:investigate','RISK':'b:risk:confirm'}[kind]
        def operation(conn):
            row=self.store.get(conn,actor,kind,rid,permission,lock=True)
            require(row['revision']==revision,'REVISION_CONFLICT',409)
            body=deepcopy(row['body']);state=row['state']
            require((body.get('confirmation') or {}).get('status') not in {'PREPARED','SENDING','PENDING'},'CONFIRMATION_PENDING',409)
            if kind=='CASE':body,state=self._case_command(conn,actor,row,action,data)
            elif kind=='POLICY':
                require(set(data)<=({'policy'} if action=='new-version' else {'reason'}),'FIELDS_INVALID')
                if action=='submit-review':require(state=='DRAFT','POLICY_STATE_INVALID',409);state='IN_REVIEW'
                elif action=='publish':
                    require(state=='IN_REVIEW' and data.get('reason'),'POLICY_REVIEW_REQUIRED',409)
                    body['publishedBy']=actor.principal_id;body['publishedAt']=now();body['publishReason']=data['reason'];state='PUBLISHED'
                elif action=='revoke':
                    require(state=='PUBLISHED' and data.get('reason'),'POLICY_STATE_INVALID',409);state='REVOKED';body['revocationReason']=data['reason']
                else:
                    require('policy' in data,'POLICY_INVALID');body=validate_policy(data['policy']);state='DRAFT'
            elif kind=='INVESTIGATION':
                if action=='evidence':
                    require(set(data)=={'text','sourceRef'} and isinstance(data['text'],str) and 0<len(data['text'].strip())<=6000
                        and isinstance(data['sourceRef'],str) and 0<len(data['sourceRef'].strip())<=256,'EVIDENCE_INVALID')
                    body.setdefault('additionalEvidence',[]).append(dict(id='human-'+uuid4().hex,domain='MANUAL_EVIDENCE',kind='CLAIM',
                        text=data['text'].strip(),sourceRef=data['sourceRef'].strip(),actor=actor.principal_id,observedAt=now()))
                    require(len(body['additionalEvidence'])<=100,'EVIDENCE_LIMIT')
                    # New evidence requires a fresh human conclusion before a new confirmation.
                    return dict(kind=kind,**self.store.save(conn,actor,row,body,'OPEN'))
                require(set(data)=={'text','evidenceRefs','conclusion'} and isinstance(data['text'],str) and 0<len(data['text'])<=6000
                    and isinstance(data['conclusion'],str) and data['conclusion'] in {'OPEN','SUPPORTED','REJECTED','NEEDS_EVIDENCE'},'INVESTIGATION_INVALID')
                origin=self.store.get(conn,actor,body['origin']['kind'],body['origin']['id'])
                allowed_refs=self.investigation_facts(conn,actor,row)
                require(isinstance(data['evidenceRefs'],list) and len(data['evidenceRefs'])<=100 and
                    all(isinstance(ref,str) and ref in {f['id'] for f in allowed_refs} for ref in data['evidenceRefs']),'EVIDENCE_REF_NOT_IN_SOURCE')
                require(data['conclusion']!='SUPPORTED' or data['evidenceRefs'],'INVESTIGATION_EVIDENCE_REQUIRED')
                by_id={f['id']:f for f in allowed_refs}
                body['entries'].append(dict(**data,evidenceHashes={ref:digest(by_id[ref]) for ref in data['evidenceRefs']},actor=actor.principal_id,at=now()));state=data['conclusion']
            elif kind=='RISK':
                body,state=self._risk_decide(conn,actor,row,data)
            return dict(kind=kind,**self.store.save(conn,actor,row,body,state))
        return self.store.command(actor,key,kind+rid+action,dict(expectedRevision=revision,data=data),operation)

    def _case_command(self,conn,actor,row,action,data):
        b=deepcopy(row['body']);state=row['state']
        if action=='messages':
            require({'text'}<=set(data)<={'text','attachmentRefs'} and isinstance(data['text'],str) and 0<len(data['text'])<=6000,'MESSAGE_INVALID')
            attachments=data.get('attachmentRefs',[])
            require(isinstance(attachments,list) and len(attachments)<=10 and all(isinstance(a,str) and 0<len(a)<=256 for a in attachments),'ATTACHMENT_REFS_INVALID')
            b['messages'].append(dict(role='CUSTOMER',text=data['text'],attachmentRefs=attachments,source='CLAIM',at=now(),actor=actor.principal_id))
            state='ESCALATED' if safety(data['text']) or state=='ESCALATED' else 'OPEN'
        elif action=='links':
            require(set(data)=={'lineId','reason'},'LINK_INVALID')
            candidates=(b.get('evidence') or {}).get('identityCandidates',[])
            identity=next((i for i in candidates if i['lineId']==data['lineId']),None)
            require(identity and (not b.get('identity') or data['reason']),'LINK_INVALID')
            b['linkHistory'].append(dict(previous=b.get('identity'),current=identity,reason=data['reason'],actor=actor.principal_id,at=now()))
            b['identity']=identity
            return b,'EVIDENCE_PENDING'
        else:
            require(set(data)=={'adviceVersion','text','decision','reason'} and data['decision'] in {'ACCEPT','RETURN','ESCALATE','MANUAL'} and data['text'] and data['reason'],'REVIEW_INVALID')
            if data['decision']=='ACCEPT':
                require(b['advice'] and b['advice'][-1]['version']==data['adviceVersion'],'STALE_ADVICE',409)
                advice=b['advice'][-1]
                require(advice['caseRevision']==row['revision'] and advice['ai']['status']=='AVAILABLE','STALE_ADVICE',409)
                for ref in advice['policies']:
                    p=self.store.get(conn,actor,'POLICY',ref['policyId'])
                    require(p['revision']==ref['version'] and applicable(p,b,b.get('businessDate')),'POLICY_NO_LONGER_AVAILABLE',409)
            b['reviews'].append(dict(**data,actor=actor.principal_id,at=now(),caseRevision=row['revision'],externalAction='NONE'))
            state={'ACCEPT':'HANDLED','MANUAL':'HANDLED','RETURN':'OPEN','ESCALATE':'ESCALATED'}[data['decision']]
        return b,state

    def job(self,actor,kind,rid,job,key,revision,data):
        require(kind=='CASE' and job in {'evidence','advice','investigation'},'ACTION_INVALID')
        with self.store.engine.begin() as conn:
            row=self.store.get(conn,actor,kind,rid,'b:analyze')
            require(row['revision']==revision,'REVISION_CONFLICT',409)
            require((row['body'].get('confirmation') or {}).get('status') not in {'PREPARED','SENDING','PENDING'},'CONFIRMATION_PENDING',409)
            if job=='investigation':
                require(set(data)=={'investigationId'},'INVESTIGATION_INVALID')
                investigation=self.store.get(conn,actor,'INVESTIGATION',data['investigationId'],'b:investigate')
                require(investigation['body']['origin']['id']==rid,'INVESTIGATION_SOURCE_MISMATCH')
            resource=row['scope']
        scenario={'evidence':'B_CASE_EVIDENCE_V1','advice':'B_CASE_ADVICE_V1','investigation':'B_INVESTIGATION_ASSIST_V1'}[job]
        return self.tasks.create(actor,key,scenario,resource,dict(id=rid,kind=kind,expectedRevision=revision,options=data),uuid4().hex)

    def investigation(self,actor,key,data):
        require(set(data)=={'kind','id','text','evidenceRefs'} and isinstance(data['kind'],str) and data['kind']=='CASE'
            and isinstance(data['id'],str) and isinstance(data['text'],str) and 0<len(data['text'])<=6000,'INVESTIGATION_INVALID')
        def operation(conn):
            origin=self.store.get(conn,actor,data['kind'],data['id'],'b:investigate')
            self._evidence_ids(conn,actor,origin,data['evidenceRefs'])
            identity=origin['body'].get('identity') or {}
            candidates=conn.execute(select(assets).filter_by(tenant_id=actor.tenant_id,kind='INVESTIGATION',workspace=WORKSPACE)
                .where(assets.c.state.in_(['OPEN','NEEDS_EVIDENCE','SUPPORTED']))).mappings().all()
            for candidate in candidates:
                if not self.source_visible(conn,candidate):continue
                existing=self.store.get(conn,actor,'CASE',candidate['body']['origin']['id'],'b:investigate')
                linked=existing['body'].get('identity') or {}
                same=(existing['id']==origin['id'] or identity and all(identity.get(k) not in (None,'UNKNOWN')
                    and identity.get(k)==linked.get(k) for k in ('sourceTenant','storeId','productId','sku')))
                if not same:continue
                inv=self.store.get(conn,actor,'INVESTIGATION',candidate['id'],'b:investigate',lock=True)
                b=deepcopy(inv['body']);related=b.setdefault('relatedSources',[])
                if existing['id']!=origin['id'] and not any(r['id']==origin['id'] for r in related):
                    related.append(dict(id=origin['id'],revision=origin['revision']))
                    require(len(related)<=50,'INVESTIGATION_SOURCE_LIMIT')
                    b['entries'].append(dict(text=data['text'],evidenceRefs=[],originId=origin['id'],conclusion='OPEN',actor=actor.principal_id,at=now()))
                    saved=self.store.save(conn,actor,inv,b,'OPEN')
                    return dict(kind='INVESTIGATION',**saved)
                return dict(kind='INVESTIGATION',id=inv['id'],revision=inv['revision'],state=inv['state'])
            return dict(kind='INVESTIGATION',**self.store.create(conn,actor,'INVESTIGATION',dict(origin=dict(kind=data['kind'],id=data['id'],revision=origin['revision']),
                entries=[dict(text=data['text'],evidenceRefs=data['evidenceRefs'],conclusion='OPEN',actor=actor.principal_id,at=now())]),origin['scope']))
        return self.store.command(actor,key,'investigation',data,operation)

    def investigation_facts(self,conn,actor,investigation):
        body=investigation['body'];origin=self.store.get(conn,actor,'CASE',body['origin']['id'])
        facts=deepcopy((origin['body'].get('evidence') or {}).get('facts',[]))
        for source in body.get('relatedSources',[]):
            row=self.store.get(conn,actor,'CASE',source['id'])
            for fact in (row['body'].get('evidence') or {}).get('facts',[]):
                facts.append(dict(fact,id=row['id']+':'+fact['id']))
        return facts+deepcopy(body.get('additionalEvidence',[]))

    def _evidence_ids(self,conn,actor,origin,refs):
        require(isinstance(refs,list) and len(refs)<=100 and all(isinstance(r,str) for r in refs),'EVIDENCE_REFS_INVALID')
        allowed={f['id'] for f in (origin['body'].get('evidence') or {}).get('facts',[])}
        require(set(refs)<=allowed,'EVIDENCE_REF_NOT_IN_SOURCE')

    def evidence(self,actor,kind,rid,eid):
        require(kind=='CASE','NOT_FOUND',404)
        with self.store.engine.begin() as conn:
            origin=self.store.get(conn,actor,kind,rid)
            self._evidence_ids(conn,actor,origin,[eid])
            record=next(f for f in origin['body']['evidence']['facts'] if f['id']==eid)
            return dict(sourceNature=origin['scope']['sourceNature'],record=record,hash=digest(record),snapshotRef=origin['body']['evidence']['snapshotRef'])

    def risk(self,actor,key,data):
        require(set(data)=={'investigationId','reason','limitations','identity'} and data['reason'] and data['limitations'],'RISK_INVALID')
        require(all(isinstance(data[k],str) and 0<len(data[k])<=6000 for k in ('investigationId','reason','limitations')),'RISK_INVALID')
        def operation(conn):
            investigation=self.store.get(conn,actor,'INVESTIGATION',data['investigationId'],'b:investigate')
            return self._create_risk(conn,actor,investigation,data)
        return self.store.command(actor,key,'risk',data,operation)

    def confirm_risk(self,actor,rid,key,revision,data):
        require(set(data)=={'reason','limitations','identity','validUntil'} and all(isinstance(data[k],str) and 0<len(data[k].strip())<=6000 for k in ('reason','limitations')),'RISK_INVALID')
        def operation(conn):
            investigation=self.store.get(conn,actor,'INVESTIGATION',rid,'b:risk:confirm',lock=True)
            require(investigation['revision']==revision,'REVISION_CONFLICT',409)
            require(investigation['state']=='SUPPORTED','INVESTIGATION_CONCLUSION_REQUIRED',409)
            # Serialize on the investigation to avoid duplicate active reminders.
            duplicate=conn.execute(select(assets.c.id).filter_by(tenant_id=actor.tenant_id,kind='RISK')
                .where(assets.c.body['investigationId'].as_string()==rid,assets.c.state.in_(['SUSPECTED','CONFIRMED']))).first()
            require(not duplicate,'INVESTIGATION_RISK_EXISTS',409)
            result=self._create_risk(conn,actor,investigation,dict(investigationId=rid,**{k:data[k] for k in ('reason','limitations','identity')}))
            risk=self.store.get(conn,actor,'RISK',result['id'],'b:risk:confirm',lock=True)
            body,state=self._risk_decide(conn,actor,risk,dict(decision='CONFIRM',reason=data['reason'],validUntil=data['validUntil']))
            return dict(kind='RISK',**self.store.save(conn,actor,risk,body,state))
        return self.store.command(actor,key,'confirm-risk:'+rid,dict(expectedRevision=revision,data=data),operation)

    def _create_risk(self,conn,actor,investigation,data):
        identity=data['identity'];self.validate_identity(identity)
        origin=investigation['body']['origin'];case=self.store.get(conn,actor,'CASE',origin['id'])
        linked=case['body'].get('identity') or {}
        require(all(str(linked.get(k))==str(identity[k]) for k in ('productId','sku','storeId'))
            and ((identity['warehouseMode']=='EXPLICIT_IDS' and linked.get('warehouseId') not in {None,'UNKNOWN'} and identity['warehouseIds']==[linked['warehouseId']])
                or identity['warehouseMode']=='ALL_STORE_WAREHOUSES' and self.source_reader is not None
                    and any(m.sku==identity['sku'] and m.monitor.productId==identity['productId'] and m.sourceStore==identity['storeId']
                        and m.sourceTenant==identity['sourceTenant'] for m in (self.source_reader.members() or [])))
            and not (case['body'].get('evidence') or {}).get('latestUnverified')
            and identity['sourceTenant']==case['scope']['sourceTenant'] and linked.get('category') in {'APPAREL','ELECTRONICS'}
            and not any('冲突' in gap for gap in (case['body'].get('evidence') or {}).get('missing',[])),'RISK_SOURCE_MISMATCH')
        body=dict(**data,createdBy=actor.principal_id,createdAt=now(),decisions=[],validFrom=None,validUntil=None)
        return dict(kind='RISK',**self.store.create(conn,actor,'RISK',body,investigation['scope'],state='SUSPECTED'))

    @staticmethod
    def validate_identity(identity):
        require(isinstance(identity,dict) and set(identity)=={'sourceTenant','productId','sku','storeId','warehouseMode','warehouseIds'} and all(isinstance(identity[k],str) and identity[k] and '*' not in identity[k] for k in ('sourceTenant','productId','sku','storeId'))
            and identity['warehouseMode'] in {'EXPLICIT_IDS','ALL_STORE_WAREHOUSES'} and isinstance(identity['warehouseIds'],list)
            and all(isinstance(w,str) and w and '*' not in w for w in identity['warehouseIds']) and len(identity['warehouseIds'])<=100
            and (identity['warehouseMode']=='ALL_STORE_WAREHOUSES' and not identity['warehouseIds'] or identity['warehouseMode']=='EXPLICIT_IDS' and identity['warehouseIds']),'RISK_SCOPE_INVALID')

    def _risk_decide(self,conn,actor,row,data):
        require(set(data)=={'decision','reason','validUntil'} and isinstance(data['reason'],str) and 0<len(data['reason'])<=1000
            and isinstance(data['decision'],str),'RISK_DECISION_INVALID')
        b=deepcopy(row['body']);state=row['state'];decision=data['decision']
        transitions={'SUSPECTED':{'CONFIRM':'CONFIRMED','REJECT':'REJECTED'},'CONFIRMED':{'CLOSE':'CLOSED','REVOKE':'REVOKED'},'REJECTED':{},'CLOSED':{},'REVOKED':{}}
        require(decision in transitions.get(state,{}),'RISK_STATE_INVALID',409)
        investigation=self.store.get(conn,actor,'INVESTIGATION',b['investigationId'])
        if decision=='CONFIRM':
            require(investigation['state']=='SUPPORTED','INVESTIGATION_CONCLUSION_REQUIRED',409)
            require(investigation['body']['entries'][-1]['evidenceRefs'],'INVESTIGATION_EVIDENCE_REQUIRED',409)
            facts=self.investigation_facts(conn,actor,investigation)
            evidence={f['id']:f for f in facts}
            refs=investigation['body']['entries'][-1]['evidenceRefs']
            require(all(ref in evidence for ref in refs),'EVIDENCE_REF_NOT_IN_SOURCE')
            hashes=investigation['body']['entries'][-1].get('evidenceHashes',{})
            require(all(digest(evidence[ref])==value for ref,value in hashes.items()),'INVESTIGATION_EVIDENCE_CHANGED',409)
            for rid in [investigation['body']['origin']['id']]+[s['id'] for s in investigation['body'].get('relatedSources',[])]:
                source=self.store.get(conn,actor,'CASE',rid)
                require(not (source['body'].get('evidence') or {}).get('latestUnverified'),'EVIDENCE_UNVERIFIED',409)
            b['confirmedEvidence']=[deepcopy(evidence[ref]) for ref in refs]
            end=timestamp(data['validUntil']) if data['validUntil'] else timestamp(now())+timedelta(days=30)
            start=timestamp(now());require(start<end<=start+timedelta(days=30),'RISK_VALIDITY_INVALID')
            b.update(validFrom=start.isoformat(),validUntil=end.isoformat(),confirmedBy=actor.principal_id,investigationRevision=investigation['revision'])
        b['decisions'].append(dict(**data,actor=actor.principal_id,at=now(),fromVersion=row['revision']))
        return b,transitions[state][decision]
