"""One S01 operation per source report; no procurement management subsystem."""
from sqlalchemy import Table, Column, String, JSON, MetaData, UniqueConstraint, select
from sqlalchemy.dialects.mysql import DATETIME

metadata = MetaData()
requisitions = Table('s01_requisitions', metadata,
    Column('tenant_id', String(64), primary_key=True),
    Column('report_id', String(64), primary_key=True),
    Column('operation_id', String(64), nullable=False),
    Column('principal_id', String(64), nullable=False),
    Column('command_key', String(128), nullable=False),
    Column('fingerprint', String(64), nullable=False),
    Column('state', String(32), nullable=False),
    Column('owner', String(64), nullable=True),
    Column('busy_until', DATETIME(fsp=6), nullable=True),
    Column('content', JSON, nullable=False),
    Column('created_at', DATETIME(fsp=6), nullable=False),
    Column('updated_at', DATETIME(fsp=6), nullable=False),
    UniqueConstraint('tenant_id', 'principal_id', 'command_key', name='uq_s01_requisition_command'),
    UniqueConstraint('operation_id', name='uq_s01_requisition_operation'),
    mysql_engine='InnoDB', mysql_charset='utf8mb4', mysql_collate='utf8mb4_bin')


def verified_purchase_proofs(engine, scope):
    with engine.connect() as conn:
        rows = conn.execute(select(requisitions.c.content).filter_by(tenant_id=scope['tenantId'], state='SUBMITTED')).scalars().all()
    return [dict(erpId=r['erpId'], erpNumber=r['erpNumber'], scope=r['scope'], datasetId=r['datasetId'], purpose=r['purpose'])
        for r in rows if r.get('scope') == scope and r.get('erpId')]
