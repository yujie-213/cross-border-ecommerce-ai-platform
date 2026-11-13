"""D01 acquisition ledger. Connections are lent by O01's fenced short transaction."""
from uuid import uuid4
from sqlalchemy import MetaData, Table, Column, String, Integer, JSON, select, insert, update

metadata = MetaData()
acquisitions = Table('d01_online_acquisitions', metadata,
    Column('tenant_id', String(64), primary_key=True), Column('task_id', String(64), primary_key=True),
    Column('plan_version', Integer, primary_key=True), Column('delivery', Integer, primary_key=True),
    Column('acquisition_id', String(64), nullable=False), Column('state', String(24), nullable=False),
    Column('request_digest', String(64), nullable=False), Column('receipt', JSON),
    Column('snapshot_ref', String(80)),mysql_engine='InnoDB',mysql_charset='utf8mb4',mysql_collate='utf8mb4_bin')


class AcquisitionStore:
    def begin(self, conn, task, delivery, request_digest):
        key = dict(tenant_id=task['tenant_id'], task_id=task['task_id'], plan_version=task['plan_version'])
        rows = conn.execute(select(acquisitions).filter_by(**key).order_by(acquisitions.c.delivery)
            .with_for_update()).mappings().all()
        if any(r['request_digest'] != request_digest for r in rows):
            raise ValueError('ACQUISITION_REQUEST_CHANGED')
        completed = [r for r in rows if r['state'] == 'CAPTURED']
        if completed:
            return dict(completed[-1])
        if any(r['delivery'] >= delivery for r in rows) or len(rows) >= 2:
            raise ValueError('ACQUISITION_REENTRY_LIMIT')
        for r in rows:
            if r['state'] == 'STARTED':
                conn.execute(update(acquisitions).filter_by(**key, delivery=r['delivery']).values(state='INTERRUPTED'))
        row = dict(**key, delivery=delivery, acquisition_id=uuid4().hex, state='STARTED',
            request_digest=request_digest, receipt=None, snapshot_ref=None)
        conn.execute(insert(acquisitions).values(**row))
        return row

    def finish(self, conn, row, receipt, snapshot_ref):
        result = conn.execute(update(acquisitions).filter_by(tenant_id=row['tenant_id'], task_id=row['task_id'],
            plan_version=row['plan_version'], delivery=row['delivery'], acquisition_id=row['acquisition_id'],
            state='STARTED').values(state='CAPTURED', receipt=receipt, snapshot_ref=snapshot_ref))
        if result.rowcount != 1:
            raise ValueError('ACQUISITION_ALREADY_FINAL')
