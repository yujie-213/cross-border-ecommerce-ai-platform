"""Short, authorized aggregate transactions and immutable audit/history versions."""
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import insert, select, update, func

from commerce_hub.governance.access.b_resources import register_created_resource
from commerce_hub.governance.access.service import AccessDenied
from .common import WORKSPACE, digest, require, scope
from .tables import assets, versions, commands


class Store:
    def __init__(self, tasks):
        self.tasks = tasks
        self.engine, self.access, self.audit = tasks.engine, tasks.access, tasks.audit
        self.source_visible=lambda conn,row:True

    def authorize(self, conn, actor, action, resource):
        require(self.tasks.after_sales_enabled, 'B_NOT_ENABLED', 503)
        self.access.authorize_b_resource(conn, actor, action, resource)

    def get(self, conn, actor, kind, rid, action='b:read', *, lock=False):
        q=select(assets).filter_by(tenant_id=actor.tenant_id,kind=kind,id=rid,workspace=WORKSPACE)
        row=conn.execute(q.with_for_update() if lock else q).mappings().first()
        require(row is not None,'NOT_FOUND',404)
        require(self.source_visible(conn,row),'NOT_FOUND',404)
        try: self.authorize(conn,actor,action,row['scope'])
        except AccessDenied: require(False,'NOT_FOUND',404)
        return dict(row)

    def view(self,row):
        return dict(id=row['id'],kind=row['kind'],revision=row['revision'],state=row['state'],
            sourceNature=row['scope']['sourceNature'],scope=row['scope'],body=row['body'],updatedAt=row['updated_at'].isoformat()+'Z')

    def read(self,actor,kind,rid,version=None):
        with self.engine.begin() as conn:
            row=self.get(conn,actor,kind,rid)
            history=conn.execute(select(versions).filter_by(tenant_id=actor.tenant_id,kind=kind,id=rid).order_by(versions.c.version)).mappings().all()
            result=self.view(row)
            result['history']=[dict(version=v['version'],body=v['body'],actor=v['actor'],createdAt=v['created_at'].isoformat()+'Z',hash=v['content_hash']) for v in history]
            if version is not None:
                selected=[v for v in result['history'] if v['version']==version]
                require(selected,'NOT_FOUND',404);result['body']=selected[0]['body'];result['revision']=version
            return result

    def list(self,actor,kind,*,before=None,limit=20):
        require(1<=limit<=100,'LIMIT_INVALID')
        with self.engine.begin() as conn:
            self.access._assert_current(conn,actor,lock=True)
            q=select(assets).filter_by(tenant_id=actor.tenant_id,workspace=WORKSPACE,kind=kind)
            if before: q=q.where(assets.c.id<before)
            rows=conn.execute(q.order_by(assets.c.id.desc()).limit(201)).mappings().all()
            result=[];last=None
            for row in rows[:200]:
                last=row['id']
                try:self.authorize(conn,actor,'b:read',row['scope'])
                except AccessDenied:continue
                if not self.source_visible(conn,row):continue
                result.append(self.view(row))
                if len(result)==limit: break
            return dict(items=result,nextCursor=last if len(rows)>0 and (len(result)==limit or len(rows)>200) else None)

    def save(self,conn,actor,row,body,state=None):
        rev=row['revision']+1
        body=deepcopy(body);body['_state']=state or row['state']
        changed=conn.execute(update(assets).filter_by(tenant_id=actor.tenant_id,kind=row['kind'],id=row['id'],revision=row['revision'])
            .values(body=body,state=state or row['state'],revision=rev,updated_at=func.utc_timestamp(6)))
        require(changed.rowcount==1,'REVISION_CONFLICT',409)
        conn.execute(insert(versions).values(tenant_id=actor.tenant_id,kind=row['kind'],id=row['id'],version=rev,
            body=body,content_hash=digest(body),actor=actor.principal_id,created_at=func.utc_timestamp(6)))
        self.audit.record(conn,tenant_id=actor.tenant_id,principal_id=actor.principal_id,action='B_'+row['kind']+'_UPDATED',details=dict(id=row['id'],version=rev,hash=digest(body)))
        return dict(id=row['id'],revision=rev,state=state or row['state'])

    def create(self,conn,actor,kind,body,resource,state='OPEN',rid=None):
        rid=rid or uuid4().hex
        resource=deepcopy(resource)
        if resource['createParent']:
            self.authorize(conn,actor,{'CASE':'b:case:write','POLICY':'b:policy:write','DATASET':'b:dataset:manage'}[kind],resource)
            resource.update(resourceId=rid,createParent=False)
            if kind=='DATASET':resource['datasetVersion']=body['manifest']['version']
            register_created_resource(self.access,conn,actor,resource,self.audit)
        else:self.authorize(conn,actor,'b:binding:manage' if kind=='BINDING' else 'b:investigate' if kind in {'INVESTIGATION','RISK'} else 'b:analyze',resource)
        body=deepcopy(body);body['_state']=state
        values=dict(tenant_id=actor.tenant_id,kind=kind,id=rid,workspace=WORKSPACE,scope=resource,revision=1,state=state,
            body=body,created_by=actor.principal_id,created_at=func.utc_timestamp(6),updated_at=func.utc_timestamp(6))
        conn.execute(insert(assets).values(**values))
        conn.execute(insert(versions).values(tenant_id=actor.tenant_id,kind=kind,id=rid,version=1,body=body,
            content_hash=digest(body),actor=actor.principal_id,created_at=func.utc_timestamp(6)))
        self.audit.record(conn,tenant_id=actor.tenant_id,principal_id=actor.principal_id,action='B_'+kind+'_CREATED',details=dict(id=rid,hash=digest(body)))
        return dict(id=rid,revision=1,state=state)

    def command(self,actor,key,operation,payload,callback):
        require(isinstance(key,str) and 1<=len(key)<=128,'COMMAND_KEY_REQUIRED')
        fp=digest([operation,payload])
        with self.engine.begin() as conn:
            # Same principal lock as G01: serialize command keys and permission changes.
            self.access._assert_current(conn,actor,lock=True)
            ck=dict(tenant_id=actor.tenant_id,actor=actor.principal_id,command_key=key)
            old=conn.execute(select(commands).filter_by(**ck)).mappings().first()
            if old:
                require(old['fingerprint']==fp,'COMMAND_CONFLICT',409)
                r=old['result'];self.get(conn,actor,r['kind'],r['id'])
                return r
            result=callback(conn)
            conn.execute(insert(commands).values(**ck,fingerprint=fp,result=result))
            return result
