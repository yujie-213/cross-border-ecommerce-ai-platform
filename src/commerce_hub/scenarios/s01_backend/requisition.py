"""Human confirmation -> teaching ERP request, using G01/O01/G02 public services."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError

from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.sync.owned import collect_owned
from commerce_hub.data.projection.online import observed, normalize_online
from commerce_hub.data.quality.online import capture_online
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.s01_backend.online import OnlineS01Handler
from commerce_hub.data.projection.purchases import POLICY
from .requisition_store import requisitions, verified_purchase_proofs


class RequisitionService:
    def __init__(self, tasks, scope_registry, client_factory):
        self.tasks, self.engine = tasks, tasks.engine
        self.registry, self.client_factory = scope_registry, client_factory

    def _authorize(self, actor, scope, *, write=True):
        try:
            self.registry.require_scope(scope)
        except ValueError:
            raise TaskError('MONITOR_SCOPE_NOT_ACTIVE', 409) from None
        with self.engine.begin() as conn:
            self.tasks.access.authorize(conn, actor, 's01:requisition' if write else 'tasks:read', scope)

    def _source(self, actor, report_id):
        # O01 validates immutable publication, current scope and source binding.
        report = self.tasks.read_report(actor, report_id)
        if report['scenarioId'] != 'S01_BACKEND':
            raise TaskError('REQUISITION_SOURCE_NOT_ELIGIBLE', 422)
        scope = report['scope']
        self._authorize(actor, scope, write=False)
        return report

    def _mapping(self, scope, report):
        return next((m for m in self.registry.mappings() if m.scope == scope), None)

    def _authorize_operation(self, actor, scope, mapping):
        self._authorize(actor, scope)

    def _confirmation_metadata(self, report, mapping):
        return {}

    def _row(self, conn, actor, report_id, *, lock=False):
        query = select(requisitions).filter_by(tenant_id=actor.tenant_id, report_id=report_id)
        if lock:
            query = query.with_for_update()
        return conn.execute(query).mappings().first()

    @staticmethod
    def view(row):
        c = row['content']
        keys = ('erpId', 'erpNumber', 'erpStatus', 'aiQuantity', 'finalQuantity', 'adjustmentReason', 'purpose',
                'sourceSnapshot', 'revalidatedAt', 'errorCode', 'verifiedAt')
        return dict(operationId=row['operation_id'], reportId=row['report_id'], state=row['state'],
            createdAt=row['created_at'].isoformat()+'Z', updatedAt=row['updated_at'].isoformat()+'Z',
            **{k:c.get(k) for k in keys}, resultMeaning='ERP_APPROVAL_REQUEST_ONLY',
            queryPath='/api/v1/purchase-orders/'+str(c['erpId']) if c.get('erpId') else None)

    def read(self, actor, report_id):
        self._source(actor, report_id)
        with self.engine.connect() as conn:
            row = self._row(conn, actor, report_id)
            return self.view(row) if row else None

    def _save(self, actor, report_id, owner, state, values=None):
        with self.engine.begin() as conn:
            row = self._row(conn, actor, report_id, lock=True)
            if row is None or row['owner'] != owner:
                raise TaskError('REQUISITION_OPERATION_BUSY')
            # Revocation must stop the next mutation; unknown outcomes still need a durable record.
            content = dict(row['content'], **(values or {}))
            now = conn.scalar(select(func.utc_timestamp(6)))
            conn.execute(update(requisitions).filter_by(tenant_id=actor.tenant_id, report_id=report_id, owner=owner)
                .values(state=state, content=content, updated_at=now))
        return content

    def _release(self, actor, report_id, owner):
        with self.engine.begin() as conn:
            conn.execute(update(requisitions).filter_by(tenant_id=actor.tenant_id, report_id=report_id, owner=owner)
                .values(owner=None, busy_until=None))

    @staticmethod
    def validate_quantity(report, quantity, reason):
        data = report['dataReport']
        candidates = data.get('supplyDemand', {}).get('candidates', [])
        constraints = data.get('forecast', {}).get('constraints', {})
        if (report.get('sourceNature') != 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'
                or report.get('completeness') == 'BLOCKED' or not candidates
                or data.get('existingPurchases', {}).get('policyVersion') != POLICY
                or not constraints.get('wholeCartonRequired')
                or any(i['severity'] == 'BLOCK' for i in data.get('quality', []))):
            raise TaskError('REQUISITION_SOURCE_NOT_ELIGIBLE', 422)
        if type(quantity) is not int or not 1 <= quantity <= 100000 or not isinstance(reason, str) or len(reason) > 1000:
            raise TaskError('INVALID_REQUISITION_FIELDS', 422)
        moq, multiple = Decimal(constraints['moq']), Decimal(constraints['orderMultiple'])
        if not moq.is_finite() or not multiple.is_finite() or moq <= 0 or multiple <= 0 or quantity < moq or Decimal(quantity) % multiple:
            raise TaskError('MOQ_OR_CARTON_VIOLATION', 422)
        original = candidates[0]['quantity']
        if Decimal(original) != quantity and not reason.strip():
            raise TaskError('ADJUSTMENT_REASON_REQUIRED', 422)
        return original

    @staticmethod
    def _facts(report):
        d = report['dataReport']
        supply = deepcopy(d['supplyDemand'])
        for candidate in supply['candidates']:
            candidate.pop('candidateId', None)
            candidate.pop('constraintRefs', None)
            candidate['evaluation'].pop('snapshotRef', None)
            candidate['evaluation'].pop('scenario', None)
            candidate['evaluation'].pop('metricResultRef', None)
        if supply.get('baseline'):
            supply['baseline'].pop('snapshotRef', None)
            supply['baseline'].pop('scenario', None)
            supply['baseline'].pop('metricResultRef', None)
        return dict(supplyDemand=supply, constraints=d['forecast']['constraints'],
            monitoring=d['scenarioSupplement']['monitoring'], purchases=d['existingPurchases'])

    def _prepare(self, actor, report, mapping, client, operation, quantity, reason):
        service = self
        class Context:
            def check(self):
                service._authorize_operation(actor, mapping.scope, mapping)
        context = Context()
        captures, receipt = collect_owned(client.reader, mapping, context, 'rq-'+operation[:32],
            formal_purchases=True, purchase_proofs=verified_purchase_proofs(self.engine, mapping.scope))
        projection, verified = observed(captures, mapping, receipt)
        normalized = normalize_online(captures, mapping, receipt, verified)
        fresh = OnlineS01Handler.rules_result(capture_online(projection, receipt, verified, normalized))
        current = dict(sourceNature=fresh.sourceNature, completeness=fresh.completeness, dataReport=fresh.dataReport)
        if current['completeness'] == 'BLOCKED' or 'forecast' not in current['dataReport']:
            raise TaskError('ANALYSIS_CHANGED_REANALYZE', 409)
        if self._facts(current) != self._facts(report):
            raise TaskError('ANALYSIS_CHANGED_REANALYZE', 409)
        self.validate_quantity(current, quantity, reason)
        quote, supplier = captures['quotes']['rows'][0], captures['supplier']['rows'][0]
        price = Decimal(str(quote['unit_price']))
        minimum = Decimal(str(quote['minimum_amount']))
        currency = quote.get('currency')
        if (not price.is_finite() or not 0 < price <= 1000000 or not minimum.is_finite()
                or price * quantity < minimum or currency not in {'USD', 'CNY', 'EUR', 'GBP'}):
            raise TaskError('QUOTE_AMOUNT_OR_CURRENCY_UNCONFIRMED', 422)
        amount = price * quantity
        if amount != amount.quantize(Decimal('.01')):
            raise TaskError('CURRENCY_PRECISION_UNCONFIRMED', 422)
        number = 'S01-RQ-' + operation[:32]
        payload = dict(order_sn=number, supplier_id=int(mapping.monitor.supplierId), supplier_name=supplier['name'],
            warehouse_name=mapping.warehouseName, order_time=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            purchase_currency=currency, amount=float(amount), purchase_user='S01-Human-Confirmed', source_plan_no=operation,
            remark='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP;SALES_REPLENISHMENT;'+mapping.monitor.datasetId,
            item_list=[dict(sku=mapping.sku, product_id=int(mapping.monitor.productId), quantity=quantity,
                unit_price=float(price), amount=float(amount))])
        return dict(payload=payload, erpNumber=number, revalidatedAt=receipt['completedAt'],
            revalidationDigest=fingerprint(dict(receipt=receipt, normalization=normalized)))

    @staticmethod
    def _matches(row, c, mapping):
        p = c['payload']
        lines = row.get('item_list')
        if (type(row.get('id')) is not int or row['id'] <= 0 or str(row.get('tenant_id')) != mapping.sourceTenant
                or row.get('order_sn') != p['order_sn'] or row.get('source_plan_no') != p['source_plan_no']
                or str(row.get('supplier_id')) != str(p['supplier_id']) or row.get('warehouse_name') != p['warehouse_name']
                or row.get('purchase_currency') != p['purchase_currency'] or row.get('remark') != p['remark']
                or not isinstance(lines, list) or len(lines) != 1):
            raise TaskError('ERP_REQUISITION_READBACK_MISMATCH')
        line, expected = lines[0], p['item_list'][0]
        try:
            if (line.get('sku') != expected['sku'] or type(line.get('quantity')) is not int
                    or line['quantity'] != expected['quantity']
                    or any(Decimal(str(line.get(k))) != Decimal(str(expected[k])) for k in ('unit_price', 'amount'))
                    or Decimal(str(row.get('amount'))) != Decimal(str(p['amount']))):
                raise ValueError()
        except (ArithmeticError, ValueError, TypeError):
            raise TaskError('ERP_REQUISITION_READBACK_MISMATCH') from None
        return row

    def confirm(self, actor, report_id, command_key, quantity, reason, trace_id):
        if not isinstance(command_key, str) or not 1 <= len(command_key) <= 128:
            raise TaskError('INVALID_COMMAND_KEY', 422)
        report = self._source(actor, report_id)
        scope = report['scope']
        self._authorize(actor, scope)
        mapping = self._mapping(scope, report)
        if mapping is None or mapping.monitor is None:
            raise TaskError('MONITOR_SCOPE_NOT_ACTIVE', 409)
        fp = fingerprint(dict(quantity=quantity, reason=reason))
        owner = uuid4().hex
        # Serialize on G01 principal locks and the report's operation row. No network under these locks.
        try:
            with self.engine.begin() as conn:
                self.tasks.access.authorize(conn, actor, 's01:requisition', scope)
                row = self._row(conn, actor, report_id, lock=True)
                now = conn.scalar(select(func.utc_timestamp(6)))
                if row:
                    if row['fingerprint'] != fp or row['principal_id'] != actor.principal_id:
                        raise TaskError('REQUISITION_COMMAND_CONFLICT')
                    if row['state'] in {'SUBMITTED', 'BLOCKED'} or row['busy_until'] and row['busy_until'] > now:
                        return self.view(row)
                    content, operation, state = deepcopy(row['content']), row['operation_id'], row['state']
                else:
                    original = self.validate_quantity(report, quantity, reason)
                    observed_at = datetime.fromisoformat(report['dataReport']['acquisition']['completedAt'])
                    if not timedelta(0) <= datetime.now(timezone.utc) - observed_at <= timedelta(hours=24):
                        raise TaskError('SOURCE_REPORT_EXPIRED', 409)
                    operation = fingerprint(dict(tenant=actor.tenant_id, report=report_id))
                    state = 'PREPARING'
                    content = dict(scope=scope, datasetId=mapping.monitor.datasetId, scopeVersion=mapping.monitor.scopeVersion,
                        importBatchId=mapping.monitor.importBatchId, purpose='SALES_REPLENISHMENT',
                        aiQuantity=original, finalQuantity=quantity, adjustmentReason=reason,
                        sourceSnapshot=report['snapshotRef'], errorCode=None)
                    content.update(self._confirmation_metadata(report, mapping))
                    conn.execute(requisitions.insert().values(tenant_id=actor.tenant_id, report_id=report_id,
                        operation_id=operation, principal_id=actor.principal_id, command_key=command_key,
                        fingerprint=fp, state=state, content=content, created_at=now, updated_at=now))
                    self.tasks.audit.record(conn, tenant_id=actor.tenant_id, principal_id=actor.principal_id,
                        task_id=report_id, action='S01_REQUISITION_CONFIRMED', trace_id=trace_id,
                        details=dict(operationId=operation, sourceSnapshot=report['snapshotRef'], aiQuantity=original,
                                     finalQuantity=quantity, adjustmentReason=reason))
                conn.execute(update(requisitions).filter_by(tenant_id=actor.tenant_id, report_id=report_id)
                    .values(owner=owner, busy_until=now+timedelta(seconds=300)))
        except IntegrityError:
            raise TaskError('REQUISITION_COMMAND_CONFLICT') from None
        try:
            def check():
                self._authorize_operation(actor, scope, mapping)
            client = self.client_factory(operation, check)
            if state == 'PREPARING':
                prepared = self._prepare(actor, report, mapping, client, operation, quantity, reason)
                content = self._save(actor, report_id, owner, 'CREATING', prepared)
                state = 'CREATING'
                # Before first creation, look up this operation's deterministic key.
                found = client.find_requisition(content['erpNumber'])
                if found.total != 0:
                    raise TaskError('ERP_REQUISITION_PREEXISTING_KEY')
                check()
                try:
                    client.create_requisition(content['payload'])
                except ERPError as error:
                    # A rejected or lost response never authorizes a second create.
                    content = self._save(actor, report_id, owner, 'CREATE_UNKNOWN', dict(errorCode='CREATE_RESULT_UNKNOWN',
                        createRejectionStatus=error.status if error.code == 'ERP_WRITE_REJECTED' else None))
            if state in {'CREATING', 'CREATE_UNKNOWN'}:
                found = client.find_requisition(content['erpNumber'])
                if not found.complete or found.total != 1:
                    rejected = content.get('createRejectionStatus') if found.complete and found.total == 0 else None
                    self._save(actor, report_id, owner, 'BLOCKED' if rejected else 'CREATE_UNKNOWN',
                        dict(errorCode=f'ERP_CREATE_REJECTED_HTTP_{rejected}' if rejected else 'CREATE_RESULT_UNKNOWN'))
                    return self.read(actor, report_id)
                erp = self._matches(found.records[0], content, mapping)
                content = self._save(actor, report_id, owner, 'CREATED', dict(erpId=str(erp['id']), erpStatus=erp.get('status_text'), errorCode=None))
                state = 'CREATED'
            if state in {'CREATED', 'SUBMITTING', 'SUBMIT_UNKNOWN'}:
                erp = self._matches(client.read_requisition(content['erpId']), content, mapping)
                if erp.get('status_text') == '待提交':
                    check()
                    self._save(actor, report_id, owner, 'SUBMITTING')
                    state = 'SUBMITTING'
                    rejected = None
                    try:
                        client.submit_requisition(content['erpId'])
                    except ERPError as error:
                        rejected = error.status if error.code == 'ERP_WRITE_REJECTED' else None
                        self._save(actor, report_id, owner, 'SUBMIT_UNKNOWN', dict(errorCode='SUBMIT_RESULT_UNKNOWN'))
                    # Independent GET, never a write receipt used as final evidence.
                    erp = self._matches(client.read_requisition(content['erpId']), content, mapping)
                if erp.get('status_text') == '待提交':
                    self._save(actor, report_id, owner, 'BLOCKED' if rejected else 'SUBMIT_UNKNOWN',
                        dict(errorCode=f'ERP_SUBMIT_REJECTED_HTTP_{rejected}' if rejected else 'SUBMIT_RESULT_UNKNOWN'))
                    return self.read(actor, report_id)
                if erp.get('status_text') != '待审核':
                    raise TaskError('ERP_REQUISITION_STATE_UNCONFIRMED')
                verified_at = datetime.now(timezone.utc).isoformat()
                self._save(actor, report_id, owner, 'SUBMITTED', dict(erpStatus=erp['status_text'], verifiedAt=verified_at, errorCode=None))
                with self.engine.begin() as conn:
                    self.tasks.audit.record(conn, tenant_id=actor.tenant_id, principal_id=actor.principal_id,
                        task_id=report_id, action='S01_REQUISITION_SUBMITTED', trace_id=trace_id,
                        details=dict(operationId=operation, erpId=str(erp['id']), erpStatus=erp['status_text'], verifiedAt=verified_at))
        except TaskError as exc:
            self._save(actor, report_id, owner, 'BLOCKED', dict(errorCode=exc.code))
        except Exception as exc:
            # Preserve the durable phase. Worker/process/network retry can only reconcile it.
            unknown = 'SUBMIT_UNKNOWN' if state in {'CREATED', 'SUBMITTING', 'SUBMIT_UNKNOWN'} else 'CREATE_UNKNOWN' if state in {'CREATING', 'CREATE_UNKNOWN'} else 'PREPARING'
            self._save(actor, report_id, owner, unknown, dict(errorCode=exc.code if isinstance(exc, ERPError) else 'REQUISITION_STEP_UNCONFIRMED'))
        finally:
            self._release(actor, report_id, owner)
        return self.read(actor, report_id)
