from dataclasses import dataclass
import threading

from sqlalchemy import select

from commerce_hub.governance.access.service import Principal, AccessDenied
from commerce_hub.infrastructure.work import LeaseLost
from .budget import TaskBudgetHandle
from .service import TaskError
from .tables import tasks


class RetryableStep(RuntimeError):
    pass


@dataclass
class ExecutionContext:
    service: object
    lease: object
    principal: Principal
    task: dict
    lost: threading.Event

    def check(self):
        if self.lost.is_set():
            raise LeaseLost("LEASE_LOST")
        self.service.checkpoint(self.lease, self.principal, self.task["plan_version"])

    @property
    def budget(self):
        return TaskBudgetHandle(self.service, self.lease, self.principal, self.task["plan_version"])

    def commit_data(self, operation):
        if self.lost.is_set():
            raise LeaseLost('LEASE_LOST')
        return self.service.execution_transaction(self.lease, self.principal, self.task['plan_version'], operation)


class Worker:
    def __init__(self, service, heartbeat_seconds=2):
        self.service = service
        self.heartbeat_seconds = heartbeat_seconds

    def once(self):
        queue = self.service.queue
        kinds = [spec.work_kind for spec in self.service.registry.values()]
        if not kinds:
            return False
        queue.recover_expired(kinds)
        self.service.reconcile_dead()
        lease = queue.claim(kinds)
        if lease is None:
            return False
        stopped, lost = threading.Event(), threading.Event()
        def heartbeat():
            while not stopped.wait(self.heartbeat_seconds):
                try:
                    queue.heartbeat(lease)
                except Exception:
                    lost.set()
                    return
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            with self.service.engine.connect() as conn:
                row = conn.execute(select(tasks).filter_by(tenant_id=lease.tenant_id, task_id=lease.owner_id)).mappings().one()
            principal = Principal(row["tenant_id"], row["principal_id"], row["principal_revision"], row["token_id"])
            task = self.service.start(lease, principal)
            spec = self.service.registry.get(task["scenario_id"])
            if spec is None or spec.version != task["scenario_version"] or spec.work_kind != lease.kind:
                raise TaskError("HANDLER_VERSION_MISMATCH")
            context = ExecutionContext(self.service, lease, principal, task, lost)
            # Handler runs outside a transaction and returns a public DomainResult.
            result = spec.handler.run(context, task["parameters"])
            context.check()
            self.service.complete(lease, principal, task["plan_version"], result)
        except LeaseLost:
            pass
        except Exception as exc:
            code = exc.code if isinstance(exc, TaskError) else "POLICY_DENIED" if isinstance(exc, AccessDenied) else "STEP_FAILED"
            try:
                self.service.fail(lease, code, retryable=isinstance(exc, RetryableStep))
            except Exception:
                # Lease expiry/re-entry is durable. Never log raw handler/DB exceptions.
                pass
        finally:
            stopped.set()
            thread.join(timeout=self.heartbeat_seconds + 1)
        return True
