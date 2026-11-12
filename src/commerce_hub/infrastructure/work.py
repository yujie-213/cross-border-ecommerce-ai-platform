"""I01 persistent delivery only. Business state belongs to the owner."""
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import insert, select, update, func, tuple_

from .work_tables import work_items


class LeaseLost(RuntimeError):
    pass


@dataclass(frozen=True)
class Lease:
    tenant_id: str
    work_id: str
    owner_id: str
    kind: str
    token: str
    attempt: int
    owner_version: int = 1


class WorkStore:
    def __init__(self, engine, lease_seconds=10):
        self.engine, self.lease_seconds = engine, lease_seconds

    def enqueue(self, conn, *, tenant_id, work_id, owner_id, kind, max_attempts, owner_version=1):
        conn.execute(insert(work_items).values(tenant_id=tenant_id, work_id=work_id, owner_id=owner_id,
            kind=kind, owner_version=owner_version, state="PENDING", run_after=func.utc_timestamp(6), attempt=0, max_attempts=max_attempts))

    def claim(self, kinds):
        if not kinds:
            return None
        with self.engine.begin() as conn:
            now = conn.scalar(select(func.utc_timestamp(6)))
            row = conn.execute(select(work_items).where(work_items.c.kind.in_(list(kinds)),
                work_items.c.state.in_(["PENDING", "RETRY_WAIT"]), work_items.c.run_after <= now,
                work_items.c.attempt < work_items.c.max_attempts).order_by(work_items.c.run_after, work_items.c.work_id)
                .limit(1).with_for_update(skip_locked=True)).mappings().first()
            if not row:
                return None
            token = uuid4().hex
            conn.execute(update(work_items).where(work_items.c.tenant_id == row["tenant_id"],
                work_items.c.work_id == row["work_id"]).values(state="LEASED", lease_token=token,
                    lease_expires=now + timedelta(seconds=self.lease_seconds), attempt=row["attempt"] + 1))
            return Lease(row["tenant_id"], row["work_id"], row["owner_id"], row["kind"], token, row["attempt"] + 1, row["owner_version"])

    def validate(self, conn, lease):
        row = conn.execute(select(work_items).where(work_items.c.tenant_id == lease.tenant_id,
            work_items.c.work_id == lease.work_id).with_for_update()).mappings().first()
        now = conn.scalar(select(func.utc_timestamp(6)))
        if (not row or row["state"] != "LEASED" or row["lease_token"] != lease.token or row["lease_expires"] <= now
            or row["owner_id"] != lease.owner_id or row["kind"] != lease.kind or row["attempt"] != lease.attempt
            or row["owner_version"] != lease.owner_version):
            raise LeaseLost("LEASE_LOST")
        return row

    def heartbeat(self, lease):
        with self.engine.begin() as conn:
            self.validate(conn, lease)
            now = conn.scalar(select(func.utc_timestamp(6)))
            conn.execute(update(work_items).where(work_items.c.tenant_id == lease.tenant_id,
                work_items.c.work_id == lease.work_id).values(lease_expires=now + timedelta(seconds=self.lease_seconds)))

    def finish(self, conn, lease, state="DONE", delay=0):
        self.validate(conn, lease)
        now = conn.scalar(select(func.utc_timestamp(6)))
        conn.execute(update(work_items).where(work_items.c.tenant_id == lease.tenant_id,
            work_items.c.work_id == lease.work_id).values(state=state, lease_token=None, lease_expires=None,
                run_after=now + timedelta(seconds=delay)))

    def cancel(self, conn, tenant_id, work_id):
        conn.execute(update(work_items).where(work_items.c.tenant_id == tenant_id, work_items.c.work_id == work_id,
            work_items.c.state.in_(["PENDING", "RETRY_WAIT", "LEASED"])).values(state="CANCELLED", lease_token=None, lease_expires=None))

    def recover_expired(self, kinds=None):
        terminal = []
        if kinds is not None and not kinds:
            return terminal
        with self.engine.begin() as conn:
            now = conn.scalar(select(func.utc_timestamp(6)))
            query = select(work_items).where(work_items.c.state == "LEASED", work_items.c.lease_expires <= now)
            if kinds is not None:
                query = query.where(work_items.c.kind.in_(list(kinds)))
            rows = conn.execute(query.limit(100).with_for_update(skip_locked=True)).mappings().all()
            for row in rows:
                state = "RETRY_WAIT" if row["attempt"] < row["max_attempts"] else "DEAD"
                conn.execute(update(work_items).where(work_items.c.tenant_id == row["tenant_id"],
                    work_items.c.work_id == row["work_id"]).values(state=state, run_after=now, lease_token=None, lease_expires=None))
                if state == "DEAD":
                    terminal.append((row["tenant_id"], row["owner_id"]))
        return terminal

    def terminal_owners(self, kinds=None):
        # Reconciliation is repeatable after a crash between I01 and owner transactions.
        if kinds is not None and not kinds:
            return
        cursor = None
        while True:
            query = select(work_items.c.tenant_id, work_items.c.work_id, work_items.c.owner_id, work_items.c.owner_version).where(work_items.c.state == "DEAD")
            if kinds is not None:
                query = query.where(work_items.c.kind.in_(list(kinds)))
            if cursor:
                query = query.where(tuple_(work_items.c.tenant_id, work_items.c.work_id) > tuple_(*cursor))
            with self.engine.connect() as conn:
                batch = conn.execute(query.order_by(work_items.c.tenant_id, work_items.c.work_id).limit(100)).all()
            if not batch:
                return
            for tenant_id, work_id, owner_id, owner_version in batch:
                yield tenant_id, owner_id, work_id, owner_version
            cursor = (batch[-1].tenant_id, batch[-1].work_id)
