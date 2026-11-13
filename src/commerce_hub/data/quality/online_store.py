"""D03 immutable snapshot assets. No source network and no business report storage."""
from sqlalchemy import MetaData, Table, Column, String, JSON, select, insert
from commerce_hub.data.contracts import fingerprint

metadata = MetaData()
snapshots = Table('d03_online_snapshots', metadata,
    Column('tenant_id', String(64), primary_key=True), Column('snapshot_id', String(80), primary_key=True),
    Column('task_id', String(64), nullable=False), Column('acquisition_id', String(64), nullable=False),
    Column('asset_digest', String(64), nullable=False), Column('asset', JSON, nullable=False),
    mysql_engine='InnoDB',mysql_charset='utf8mb4',mysql_collate='utf8mb4_bin')


class OnlineSnapshotStore:
    def save(self, conn, tenant_id, task_id, acquisition_id, asset):
        conn.execute(insert(snapshots).values(tenant_id=tenant_id, task_id=task_id,
            acquisition_id=acquisition_id, snapshot_id=asset['snapshotId'], asset_digest=fingerprint(asset), asset=asset))

    def read(self, conn, tenant_id, task_id, snapshot_id):
        row = conn.execute(select(snapshots).filter_by(tenant_id=tenant_id, task_id=task_id,
            snapshot_id=snapshot_id)).mappings().one()
        if fingerprint(row['asset']) != row['asset_digest']:
            raise ValueError('ONLINE_SNAPSHOT_CORRUPTED')
        return row['asset']
