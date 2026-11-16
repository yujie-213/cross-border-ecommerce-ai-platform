"""B domain commands. Business sources and human decisions stay separate."""
from copy import deepcopy
from datetime import timedelta
import json
from uuid import uuid4

from sqlalchemy import insert,select,func
from commerce_hub.capabilities.metrics.after_sales import validate_records, DEFAULT_RULE
from .common import SOURCE,SOURCE_TENANT,WORKSPACE,digest,now,timestamp,require,safety,scope
from .store import Store
from .tables import assets,chunks,manifests
from .policies import applicable,validate_policy


class AfterSales:
    def __init__(self,tasks,source_reader=None,provider=None):
        self.tasks=tasks;self.store=Store(tasks);self.source_reader=source_reader;self.provider=provider

    def create_case(self,actor,key,data):
        require(data['message'] or data.get('erpStoreName'),'CUSTOMER_MESSAGE_REQUIRED')
        if data.get('businessDate'):timestamp(data['businessDate'])
        def operation(conn):
            body=dict(title=data['title'],messages=[dict(role='CUSTOMER',text=data['message'],source='CLAIM',at=now(),actor=actor.principal_id)] if data['message'] else [],
                region=data['region'],platform=data['platform'],language=data['language'],businessDate=data.get('businessDate'),
                datasetId=data.get('datasetId'),identity=None,linkHistory=[],evidence=None,advice=[],reviews=[])
            body['orderId']=data.get('orderId')
            body['erpTicketId']=data.get('erpTicketId');body['erpStoreName']=data.get('erpStoreName')
            source='TEACHING_ERP_OBSERVED' if body['erpStoreName'] else SOURCE
            if body['erpStoreName']:
                require(not body['datasetId'] and self.source_reader is not None,'SOURCE_MIXED')
                self.source_reader._store(body['erpStoreName'])
            if data.get('datasetId'):
                dataset=self.store.get(conn,actor,'DATASET',data['datasetId'])
                require(dataset['state']=='ACTIVE','DATASET_NOT_VERIFIED')
                body['datasetRevision']=dataset['revision'];body['datasetVersion']=dataset['body']['manifest']['version']
            result=self.store.create(conn,actor,'CASE',body,scope(actor.tenant_id,'CASE',source=source,source_tenant='1' if source=='TEACHING_ERP_OBSERVED' else SOURCE_TENANT),state='ESCALATED' if safety(data['message']) else 'OPEN')
            return dict(kind='CASE',**result)
        return self.store.command(actor,key,'create-case',data,operation)

    def create_dataset(self,actor,key,data):
        manifest=data['manifest']
        require(isinstance(manifest,dict) and set(manifest)=={'schemaVersion','datasetId','version','sourceNature','sourceTenant','timezone','coverageComplete','coverageThrough','warehouseIds','population','counts','chunks','windows','asOf'},'MANIFEST_INVALID')
        require(all(isinstance(manifest[k],str) and 0<len(manifest[k])<=128 for k in ('datasetId','version','sourceNature','sourceTenant','timezone')),'MANIFEST_INVALID')
        require(isinstance(manifest['chunks'],list) and isinstance(manifest['counts'],dict) and isinstance(manifest['population'],list) and isinstance(manifest['warehouseIds'],list),'MANIFEST_INVALID')
        require(all(isinstance(v,str) and v for k in ('population','warehouseIds') for v in manifest[k]) and len(manifest['population'])<=10000 and 0<len(manifest['warehouseIds'])<=100,'MANIFEST_INVALID')
        for number,chunk in enumerate(manifest['chunks']):
            require(isinstance(chunk,dict) and set(chunk)=={'number','count','hash'} and type(chunk['number']) is int and chunk['number']==number and type(chunk['count']) is int and 0<chunk['count']<=1000
                and isinstance(chunk['hash'],str) and len(chunk['hash'])==64,'MANIFEST_INVALID')
        timestamp(manifest['asOf']);timestamp(manifest['coverageThrough'])
        require(manifest['schemaVersion']=='1.0.0' and manifest['sourceNature']==SOURCE and manifest['sourceTenant']==SOURCE_TENANT,'SOURCE_MIXED')
        require('teacher' not in json.dumps(manifest).lower() and 1<=len(manifest['chunks'])<=300,'MANIFEST_INVALID')
        def operation(conn):
            duplicate=conn.execute(select(assets.c.id).filter_by(tenant_id=actor.tenant_id,kind='DATASET').where(
                assets.c.id==digest([manifest['datasetId'],manifest['version']])[:32])).first()
            require(duplicate is None,'DATASET_VERSION_EXISTS',409)
            return dict(kind='DATASET',**self.store.create(conn,actor,'DATASET',dict(manifest=manifest,issues=[],validation=None),scope(actor.tenant_id,'DATASET'),state='DRAFT',rid=digest([manifest['datasetId'],manifest['version']])[:32]))
        return self.store.command(actor,key,'create-dataset',data,operation)

    def create_policy(self,actor,key,data):
        validate_policy(data)
        return self.store.command(actor,key,'create-policy',data,lambda conn:dict(kind='POLICY',**self.store.create(conn,actor,'POLICY',data,scope(actor.tenant_id,'POLICY'),state='DRAFT')))

    def records(self,conn,dataset):
        manifest=dataset['body']['manifest']
        rows=conn.execute(select(chunks).filter_by(tenant_id=dataset['tenant_id'],dataset_id=dataset['id']).order_by(chunks.c.chunk_no)).mappings().all()
        require(len(rows)==len(manifest['chunks']),'CHUNKS_MISSING')
        result=[]
        for row,expected in zip(rows,manifest['chunks']):
            require(row['chunk_no']==expected['number'] and digest(row['records'])==expected['hash']==row['content_hash'] and len(row['records'])==expected['count'],'CHUNK_HASH_MISMATCH')
            result.extend(row['records'])
        require(len(json.dumps(result).encode())<=10*1024*1024,'DATASET_LIMIT')
        return result

    def upload(self,actor,rid,key,number,records,revision):
        require(len(json.dumps(records,ensure_ascii=False).encode())<=48*1024,'CHUNK_TOO_LARGE')
        payload=dict(number=number,records=records,expectedRevision=revision)
        def operation(conn):
            row=self.store.get(conn,actor,'DATASET',rid,'b:dataset:manage',lock=True)
            require(row['state']=='DRAFT','DATASET_SEALED',409)
            old=conn.execute(select(chunks).filter_by(tenant_id=actor.tenant_id,dataset_id=rid,chunk_no=number)).mappings().first()
            if old:
                require(old['content_hash']==digest(records),'CHUNK_CONFLICT',409)
                return dict(kind='DATASET',id=rid,revision=row['revision'],state=row['state'])
            require(revision==row['revision'],'REVISION_CONFLICT',409)
            expected=[c for c in row['body']['manifest']['chunks'] if c['number']==number]
            require(len(expected)==1 and expected[0]['hash']==digest(records) and expected[0]['count']==len(records),'CHUNK_HASH_MISMATCH')
            require(not any('teacher' in json.dumps(r).lower() for r in records),'TEACHER_ASSET_FORBIDDEN')
            conn.execute(insert(chunks).values(tenant_id=actor.tenant_id,dataset_id=rid,chunk_no=number,content_hash=digest(records),records=records))
            return dict(kind='DATASET',**self.store.save(conn,actor,row,row['body']))
        return self.store.command(actor,key,'chunk-'+rid,payload,operation)

    def mutate(self,actor,kind,rid,action,key,revision,data):
        allowed={'CASE':{'messages','links','reviews'},'POLICY':{'submit-review','publish','revoke','new-version'},
            'DATASET':{'seal','activate','deactivate'},'REPORT':{'classifications'},'INVESTIGATION':{'entries'},'RISK':{'decisions'},'BINDING':{'revoke'}}
        require(action in allowed.get(kind,set()),'ACTION_INVALID')
        permission={'CASE':'b:case:review' if action=='reviews' else 'b:case:write',
            'POLICY':'b:policy:publish' if action in {'publish','revoke'} else 'b:policy:write',
            'DATASET':'b:dataset:manage','REPORT':'b:investigate','INVESTIGATION':'b:investigate',
            'RISK':'b:risk:confirm','BINDING':'b:binding:manage'}[kind]
        def operation(conn):
            row=self.store.get(conn,actor,kind,rid,permission,lock=True)
            require(row['revision']==revision,'REVISION_CONFLICT',409)
            body=deepcopy(row['body']);state=row['state']
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
            elif kind=='DATASET':
                require(not data,'FIELDS_INVALID')
                if action=='seal':
                    require(state=='DRAFT','DATASET_STATE_INVALID',409)
                    records=self.records(conn,row);body['sealedHash']=digest(records);state='SEALED'
                elif action=='activate':
                    require(state=='READBACK_VERIFIED' and body.get('readbackHash')==body.get('sealedHash'),'DATASET_NOT_VERIFIED',409)
                    body['activatedBy']=actor.principal_id;body['activatedAt']=now();state='ACTIVE'
                else:require(state=='ACTIVE','DATASET_STATE_INVALID',409);state='INACTIVE'
            elif kind=='REPORT':
                require(set(data)=={'feedbackId','labels','span','reason'} and data['reason'],'FIELDS_INVALID')
                require(isinstance(data['feedbackId'],str) and isinstance(data['span'],str) and isinstance(data['reason'],str)
                    and isinstance(data['labels'],list) and all(isinstance(l,str) for l in data['labels']),'CLASSIFICATION_INVALID')
                from .model import LABELS
                dataset=self.store.get(conn,actor,'DATASET',body['datasetId'])
                require(dataset['state']=='ACTIVE','DATASET_NOT_VERIFIED')
                feedback=next((r for r in self.records(conn,dataset) if r['type']=='feedback' and r['id']==data['feedbackId']),None)
                require(feedback and data['span'] in feedback['text'] and set(data['labels'])<=LABELS and data['labels'],'CLASSIFICATION_INVALID')
                body.setdefault('classificationCorrections',[]).append(dict(**data,actor=actor.principal_id,at=now(),version=revision+1))
            elif kind=='INVESTIGATION':
                require(set(data)=={'text','evidenceRefs','conclusion'} and isinstance(data['text'],str) and 0<len(data['text'])<=6000
                    and isinstance(data['conclusion'],str) and data['conclusion'] in {'OPEN','SUPPORTED','REJECTED','NEEDS_EVIDENCE'},'INVESTIGATION_INVALID')
                origin=self.store.get(conn,actor,body['origin']['kind'],body['origin']['id'])
                self._evidence_ids(conn,actor,origin,data['evidenceRefs'])
                require(data['conclusion']!='SUPPORTED' or data['evidenceRefs'],'INVESTIGATION_EVIDENCE_REQUIRED')
                body['entries'].append(dict(**data,actor=actor.principal_id,at=now()));state=data['conclusion']
            elif kind=='RISK':
                body,state=self._risk_decide(conn,actor,row,data)
            else:require(set(data)=={'reason'} and data['reason'],'REASON_REQUIRED');state='REVOKED';body['revocationReason']=data['reason']
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
            if not b.get('datasetId'):
                candidates=(b.get('evidence') or {}).get('identityCandidates',[])
                identity=next((i for i in candidates if i['lineId']==data['lineId']),None)
                require(identity and (not b.get('identity') or data['reason']),'LINK_INVALID')
                b['linkHistory'].append(dict(previous=b.get('identity'),current=identity,reason=data['reason'],actor=actor.principal_id,at=now()))
                b['identity']=identity
                return b,'EVIDENCE_PENDING'
            dataset=self.store.get(conn,actor,'DATASET',b['datasetId'])
            require(dataset['state']=='ACTIVE','DATASET_NOT_VERIFIED')
            records=self.records(conn,dataset)
            line=next((r for r in records if r['type']=='line' and r['id']==data['lineId']),None)
            require(line is not None,'IDENTITY_UNRESOLVED')
            # Once an order is identified, candidate choices cannot cross its lines.
            current=b.get('identity')
            require((not current or current['orderId']==line['orderId']) and (not b.get('orderId') or b['orderId']==line['orderId']),'CROSS_ORDER_LINK_REJECTED')
            require(not current or data['reason'],'CORRECTION_REASON_REQUIRED')
            product=next(r for r in records if r['type']=='product' and r['id']==line['productId'])
            identity=dict(**{k:line[k] for k in ('orderId','productId','sku','storeId','warehouseId')},lineId=line['id'],category=product['category'],attributes=product['attributes'],name=product['name'],source='SIMULATED')
            b['linkHistory'].append(dict(previous=current,current=identity,reason=data['reason'],actor=actor.principal_id,at=now()))
            b['identity']=identity;b['evidence']=None;state='EVIDENCE_PENDING'
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
        with self.store.engine.begin() as conn:
            row=self.store.get(conn,actor,kind,rid,'b:binding:manage' if job=='binding' else 'b:dataset:manage' if job=='validate' else 'b:analyze')
            require(row['revision']==revision,'REVISION_CONFLICT',409)
            if job=='validate':require(row['state'] in {'SEALED','READBACK_VERIFIED'},'DATASET_NOT_SEALED')
            if job=='analysis':require(row['state']=='ACTIVE','DATASET_NOT_VERIFIED')
            resource=row['scope']
        scenario={'evidence':'B_CASE_EVIDENCE_V1','advice':'B_CASE_ADVICE_V1','validate':'B_DATASET_VALIDATE_V1','analysis':'B_EXPERIENCE_V1','binding':'B_TEACHING_BINDING_V1'}[job]
        return self.tasks.create(actor,key,scenario,resource,dict(id=rid,kind=kind,expectedRevision=revision,options=data),uuid4().hex)

    def investigation(self,actor,key,data):
        require(set(data)=={'kind','id','text','evidenceRefs'} and isinstance(data['kind'],str) and data['kind'] in {'CASE','REPORT'}
            and isinstance(data['id'],str) and isinstance(data['text'],str) and 0<len(data['text'])<=6000,'INVESTIGATION_INVALID')
        def operation(conn):
            origin=self.store.get(conn,actor,data['kind'],data['id'],'b:investigate')
            self._evidence_ids(conn,actor,origin,data['evidenceRefs'])
            return dict(kind='INVESTIGATION',**self.store.create(conn,actor,'INVESTIGATION',dict(origin=dict(kind=data['kind'],id=data['id'],revision=origin['revision']),
                entries=[dict(text=data['text'],evidenceRefs=data['evidenceRefs'],conclusion='OPEN',actor=actor.principal_id,at=now())]),origin['scope']))
        return self.store.command(actor,key,'investigation',data,operation)

    def _evidence_ids(self,conn,actor,origin,refs):
        require(isinstance(refs,list) and len(refs)<=100 and all(isinstance(r,str) for r in refs),'EVIDENCE_REFS_INVALID')
        if origin['kind']=='REPORT':
            ds=self.store.get(conn,actor,'DATASET',origin['body']['datasetId'])
            allowed={r['id'] for r in self.records(conn,ds)}
        else:allowed={f['id'] for f in (origin['body'].get('evidence') or {}).get('facts',[])}
        require(set(refs)<=allowed,'EVIDENCE_REF_NOT_IN_SOURCE')

    def evidence(self,actor,kind,rid,eid):
        with self.store.engine.begin() as conn:
            origin=self.store.get(conn,actor,kind,rid)
            self._evidence_ids(conn,actor,origin,[eid])
            if kind=='REPORT':
                ds=self.store.get(conn,actor,'DATASET',origin['body']['datasetId'])
                record=next(r for r in self.records(conn,ds) if r['id']==eid)
                return dict(sourceNature=ds['scope']['sourceNature'],datasetVersion=ds['body']['manifest']['version'],record=record,hash=digest(record),snapshotRef=origin['body']['snapshotRef'])
            record=next(f for f in origin['body']['evidence']['facts'] if f['id']==eid)
            return dict(sourceNature=origin['scope']['sourceNature'],record=record,hash=digest(record),snapshotRef=origin['body']['evidence']['snapshotRef'])

    def risk(self,actor,key,data):
        require(set(data)=={'investigationId','reason','limitations','identity','datasetId'} and data['reason'] and data['limitations'],'RISK_INVALID')
        require(all(isinstance(data[k],str) and 0<len(data[k])<=6000 for k in ('investigationId','reason','limitations'))
            and (data['datasetId'] is None or isinstance(data['datasetId'],str)),'RISK_INVALID')
        def operation(conn):
            investigation=self.store.get(conn,actor,'INVESTIGATION',data['investigationId'],'b:investigate')
            identity=data['identity'];self.validate_identity(identity)
            require(bool(data['datasetId'])==(investigation['scope']['sourceNature']==SOURCE),'RISK_SOURCE_MISMATCH')
            if data['datasetId']:
                ds=self.store.get(conn,actor,'DATASET',data['datasetId'])
                require(ds['state']=='ACTIVE','DATASET_NOT_VERIFIED')
                origin=investigation['body']['origin']
                origin_row=self.store.get(conn,actor,origin['kind'],origin['id'])
                require((origin['kind']=='REPORT' and origin_row['body']['datasetId']==ds['id']) or (origin['kind']=='CASE' and origin_row['body'].get('datasetId')==ds['id']),'RISK_SOURCE_MISMATCH')
                product=next((r for r in self.records(conn,ds) if r['type']=='product' and r['id']==identity['productId'] and r['sku']==identity['sku']),None)
                require(product is not None and identity['sourceTenant']==ds['scope']['sourceTenant'] and any(r['type']=='line' and r['productId']==identity['productId'] and r['storeId']==identity['storeId'] and (identity['warehouseMode']=='ALL_STORE_WAREHOUSES' or r['warehouseId'] in identity['warehouseIds']) for r in self.records(conn,ds)),'RISK_SOURCE_MISMATCH')
                allowed_warehouses={r['warehouseId'] for r in self.records(conn,ds) if r['type']=='line' and r['productId']==identity['productId'] and r['storeId']==identity['storeId']}
                require(set(identity['warehouseIds'])<=allowed_warehouses,'RISK_SOURCE_MISMATCH')
            else:
                origin=investigation['body']['origin'];case=self.store.get(conn,actor,'CASE',origin['id'])
                linked=case['body'].get('identity') or {}
                require(all(str(linked.get(k))==str(identity[k]) for k in ('productId','sku','storeId'))
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
            if b.get('datasetId'):
                dataset=self.store.get(conn,actor,'DATASET',b['datasetId'])
                records=self.records(conn,dataset)
                lids={r['id'] for r in records if r['type']=='line' and r['productId']==b['identity']['productId'] and r['storeId']==b['identity']['storeId']}
                refs=set(investigation['body']['entries'][-1]['evidenceRefs'])
                require(any(r['id'] in refs and r.get('lineId') in lids for r in records),'RISK_EVIDENCE_PRODUCT_MISMATCH')
            end=timestamp(data['validUntil']) if data['validUntil'] else timestamp(now())+timedelta(days=30)
            start=timestamp(now());require(start<end<=start+timedelta(days=30),'RISK_VALIDITY_INVALID')
            if b.get('datasetId'):require(self.store.get(conn,actor,'DATASET',b['datasetId'])['state']=='ACTIVE','DATASET_NOT_VERIFIED')
            b.update(validFrom=start.isoformat(),validUntil=end.isoformat(),confirmedBy=actor.principal_id,investigationRevision=investigation['revision'])
        b['decisions'].append(dict(**data,actor=actor.principal_id,at=now(),fromVersion=row['revision']))
        return b,transitions[state][decision]
