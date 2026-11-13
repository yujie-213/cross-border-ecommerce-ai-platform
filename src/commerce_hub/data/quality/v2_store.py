"""D03 immutable task acquisition manifests; deduplicated across SKU results."""
from sqlalchemy import Table,Column,String,JSON,MetaData,select,insert
from commerce_hub.data.contracts import fingerprint

metadata=MetaData()
manifests=Table('d03_v2_manifests',metadata,Column('snapshot_ref',String(128),primary_key=True),
    Column('tenant_id',String(64),nullable=False),Column('task_id',String(64),nullable=False),Column('content',JSON,nullable=False),
    mysql_engine='InnoDB',mysql_charset='utf8mb4',mysql_collate='utf8mb4_bin')


class ManifestStore:
    @staticmethod
    def save(conn,tenant,task,manifest):
        existing=conn.execute(select(manifests).filter_by(snapshot_ref=manifest['snapshotRef'])).mappings().first()
        if existing:
            if existing['tenant_id']!=tenant or existing['task_id']!=task or existing['content']!=manifest:raise ValueError('V2_MANIFEST_CONFLICT')
        else:conn.execute(insert(manifests).values(snapshot_ref=manifest['snapshotRef'],tenant_id=tenant,task_id=task,content=manifest))
    @staticmethod
    def read(conn,tenant,task,reference):
        value=conn.execute(select(manifests.c.content).filter_by(snapshot_ref=reference,tenant_id=tenant,task_id=task)).scalar_one()
        body={k:v for k,v in value.items() if k!='snapshotRef'}
        if 'snapshot-'+fingerprint(body)!=reference:raise ValueError('V2_MANIFEST_DIGEST_MISMATCH')
        return value
