"""B domain commands. Business sources and human decisions stay separate."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from .common import WORKSPACE,now,timestamp,require,safety,scope
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
            'INVESTIGATION':{'entries'},'RISK':{'decisions'}}
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
                require(set(data)=={'text','evidenceRefs','conclusion'} and isinstance(data['text'],str) and 0<len(data['text'])<=6000
                    and isinstance(data['conclusion'],str) and data['conclusion'] in {'OPEN','SUPPORTED','REJECTED','NEEDS_EVIDENCE'},'INVESTIGATION_INVALID')
                origin=self.store.get(conn,actor,body['origin']['kind'],body['origin']['id'])
                self._evidence_ids(conn,actor,origin,data['evidenceRefs'])
                require(data['conclusion']!='SUPPORTED' or data['evidenceRefs'],'INVESTIGATION_EVIDENCE_REQUIRED')
                body['entries'].append(dict(**data,actor=actor.principal_id,at=now()));state=data['conclusion']
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
        require(kind=='CASE' and job in {'evidence','advice'},'ACTION_INVALID')
        with self.store.engine.begin() as conn:
            row=self.store.get(conn,actor,kind,rid,'b:analyze')
            require(row['revision']==revision,'REVISION_CONFLICT',409)
            require((row['body'].get('confirmation') or {}).get('status') not in {'PREPARED','SENDING','PENDING'},'CONFIRMATION_PENDING',409)
            resource=row['scope']
        scenario={'evidence':'B_CASE_EVIDENCE_V1','advice':'B_CASE_ADVICE_V1'}[job]
        return self.tasks.create(actor,key,scenario,resource,dict(id=rid,kind=kind,expectedRevision=revision,options=data),uuid4().hex)

    def investigation(self,actor,key,data):
        require(set(data)=={'kind','id','text','evidenceRefs'} and isinstance(data['kind'],str) and data['kind']=='CASE'
            and isinstance(data['id'],str) and isinstance(data['text'],str) and 0<len(data['text'])<=6000,'INVESTIGATION_INVALID')
        def operation(conn):
            origin=self.store.get(conn,actor,data['kind'],data['id'],'b:investigate')
            self._evidence_ids(conn,actor,origin,data['evidenceRefs'])
            return dict(kind='INVESTIGATION',**self.store.create(conn,actor,'INVESTIGATION',dict(origin=dict(kind=data['kind'],id=data['id'],revision=origin['revision']),
                entries=[dict(text=data['text'],evidenceRefs=data['evidenceRefs'],conclusion='OPEN',actor=actor.principal_id,at=now())]),origin['scope']))
        return self.store.command(actor,key,'investigation',data,operation)

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
            identity=data['identity'];self.validate_identity(identity)
            origin=investigation['body']['origin'];case=self.store.get(conn,actor,'CASE',origin['id'])
            linked=case['body'].get('identity') or {}
            require(all(str(linked.get(k))==str(identity[k]) for k in ('productId','sku','storeId'))
                and identity['warehouseMode']=='EXPLICIT_IDS' and linked.get('warehouseId') not in {None,'UNKNOWN'} and identity['warehouseIds']==[linked['warehouseId']]
                and not (case['body'].get('evidence') or {}).get('latestUnverified')
                and identity['sourceTenant']==case['scope']['sourceTenant'] and linked.get('category') in {'APPAREL','ELECTRONICS'}
                and not any('冲突' in gap for gap in (case['body'].get('evidence') or {}).get('missing',[])),'RISK_SOURCE_MISMATCH')
            body=dict(**data,createdBy=actor.principal_id,createdAt=now(),decisions=[],validFrom=None,validUntil=None)
            return dict(kind='RISK',**self.store.create(conn,actor,'RISK',body,investigation['scope'],state='SUSPECTED'))
        return self.store.command(actor,key,'risk',data,operation)

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
            end=timestamp(data['validUntil']) if data['validUntil'] else timestamp(now())+timedelta(days=30)
            start=timestamp(now());require(start<end<=start+timedelta(days=30),'RISK_VALIDITY_INVALID')
            b.update(validFrom=start.isoformat(),validUntil=end.isoformat(),confirmedBy=actor.principal_id,investigationRevision=investigation['revision'])
        b['decisions'].append(dict(**data,actor=actor.principal_id,at=now(),fromVersion=row['revision']))
        return b,transitions[state][decision]
