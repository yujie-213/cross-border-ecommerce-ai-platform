"""Synthetic ERP boundary for engineering tests. Never a live ERP acceptance claim."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.contracts import fingerprint
from tests.unit.data.test_owned import owned_case


class FixtureERP:
    def __init__(self, scope=None):
        m, captures, _ = owned_case()
        if scope:
            m = m.model_copy(update={'scope': scope})
        self.mapping, self.captures = m, captures
        now = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).date()
        for i, sale in enumerate(captures['sales']['rows']):
            sale['order_time'] = (now-timedelta(days=7-i)).isoformat()+' 12:00:00'
        q = captures['quotes']['rows'][0]
        q.update(currency='USD', valid_from='2020-01-01', valid_to='2099-12-31')
        captures['supplier']['rows'][0]['name'] = 'Synthetic Supplier'
        self.formal = []
        self.requisition = None
        self.calls, self.creates, self.submits = [], 0, 0
        self.create_fault, self.submit_fault, self.read_fault = None, None, False
        self.on_create = None

    @property
    def reader(self):
        return self

    @property
    def events(self):
        return [dict(method=x[0], path=x[1]) for x in self.calls]

    def read(self, path, params, **_):
        self.calls.append(('GET', path, params))
        name = path.split('/')[-1]
        if name == 'purchase-orders':
            assert 'ids' not in params, 'New P3 must never read registered pending/draft IDs'
            state = params['q']
            values = [r for r in self.formal if r['status_text'] == state]
        elif name == 'ledger':
            values = self.captures['ledger-'+str(params['record_id'])]['rows']
        else:
            key = {'products':'product','store-authorizations':'store','warehouses':'warehouse','listings':'listing',
                'inventory':'inventory','sales-orders':'sales','supplier-quotes':'quotes'}[name]
            values = self.captures[key]['rows']
        return SimpleNamespace(records=deepcopy(values), complete=True, total=len(values))

    def detail(self, resource, record_id):
        self.calls.append(('GET', resource, str(record_id)))
        key = 'workflow-'+str(record_id) if resource == 'sales-workflow' else 'supplier'
        return deepcopy(self.captures[key]['rows'][0])

    def find_requisition(self, number):
        self.calls.append(('GET', 'find-requisition', number))
        if self.read_fault:
            raise ERPError('ERP_TIMEOUT')
        rows = [deepcopy(self.requisition)] if self.requisition and self.requisition['order_sn'] == number else []
        return SimpleNamespace(records=rows, complete=True, total=len(rows))

    def read_requisition(self, erp_id):
        self.calls.append(('GET', 'read-requisition', str(erp_id)))
        if self.read_fault:
            raise ERPError('ERP_TIMEOUT')
        assert self.requisition and str(self.requisition['id']) == str(erp_id)
        return deepcopy(self.requisition)

    def create_requisition(self, payload):
        self.creates += 1
        self.calls.append(('POST', 'create-requisition', payload['order_sn']))
        if self.create_fault == 'rejected':
            raise ERPError('ERP_WRITE_REJECTED', 400)
        if self.create_fault != 'not-sent':
            self.requisition = dict(deepcopy(payload), id=91, tenant_id=int(self.mapping.sourceTenant), status_text='待提交', received_qty=0)
        if self.on_create:
            self.on_create()
        if self.create_fault:
            raise ERPError('ERP_SEND_UNKNOWN')
        return deepcopy(self.requisition)

    def submit_requisition(self, erp_id):
        self.submits += 1
        self.calls.append(('POST', 'submit-requisition', str(erp_id)))
        if self.submit_fault == 'rejected':
            raise ERPError('ERP_WRITE_REJECTED', 409)
        if self.submit_fault != 'not-sent':
            self.requisition['status_text'] = '待审核'
        if self.submit_fault:
            raise ERPError('ERP_SEND_UNKNOWN')
        return dict(code=0, data=deepcopy(self.requisition))


class FixtureRegistry:
    def __init__(self, mapping): self.mapping, self.active = mapping, True
    def mappings(self): return [self.mapping] if self.active else []
    def require_scope(self, scope):
        if not self.active or scope != self.mapping.scope:
            raise ValueError('MONITOR_SCOPE_NOT_ACTIVE')
    def require(self, m):
        assert self.active and m == self.mapping
