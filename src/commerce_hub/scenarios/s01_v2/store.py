"""S01 V2 owns per-entity progress/results; O01 owns task lifecycle."""
from sqlalchemy import Table,Column,String,JSON,MetaData,select,insert,update
from commerce_hub.data.contracts import fingerprint

metadata=MetaData()
items=Table('s01_v2_items',metadata,
    Column('tenant_id',String(64),primary_key=True),Column('task_id',String(64),primary_key=True),
    Column('entity_key',String(64),primary_key=True),Column('state',String(32),nullable=False),
    Column('content',JSON,nullable=False),Column('digest',String(64),nullable=False),
    mysql_engine='InnoDB',mysql_charset='utf8mb4',mysql_collate='utf8mb4_bin')


class ItemStore:
    @staticmethod
    def read(conn,tenant,task):
        rows=conn.execute(select(items).filter_by(tenant_id=tenant,task_id=task)).mappings().all()
        if any(fingerprint(r['content'])!=r['digest'] for r in rows):raise ValueError('V2_ITEM_DIGEST_MISMATCH')
        return {r['entity_key']:r['content'] for r in rows}
    @staticmethod
    def seed(conn,tenant,task,entities):
        existing=ItemStore.read(conn,tenant,task)
        for entity in entities:
            key=entity['entityKey']
            if key not in existing:
                content=dict(entity,analysisState='PENDING',sourceGrade='UNAVAILABLE',quantity=None,uncertainties=[])
                conn.execute(insert(items).values(tenant_id=tenant,task_id=task,entity_key=key,state='PENDING',content=content,digest=fingerprint(content)))
        return existing
    @staticmethod
    def save(conn,tenant,task,result):
        conn.execute(update(items).filter_by(tenant_id=tenant,task_id=task,entity_key=result['entityKey'])
            .values(state=result['analysisState'],content=result,digest=fingerprint(result)))
