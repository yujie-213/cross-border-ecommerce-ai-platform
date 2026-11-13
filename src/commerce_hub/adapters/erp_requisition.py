"""Two authorized teaching mutations only. D01 remains read-only."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import time

from commerce_hub.adapters.erp import ERPConfig, ERPError, TeachingERPReader, AUTH_PATH, https_transport


class TeachingRequisitionClient:
    def __init__(self, config: ERPConfig, *, transport=https_transport, sleeper=time.sleep):
        self.config, self.transport, self.sleeper = config, transport, sleeper
        self._token = config.access_token
        self.events = []
        self._reader = None

    def authenticate(self):
        if self._token:
            return
        if not self.config.username or not self.config.password:
            raise ERPError('ERP_CREDENTIALS_MISSING')
        value = self._send(AUTH_PATH, dict(appId=self.config.username, appSecret=self.config.password), auth=True)
        token = value.get('data', {}).get('access_token')
        if not isinstance(token, str) or not 1 <= len(token) <= 8192 or '\r' in token or '\n' in token:
            raise ERPError('ERP_AUTH_ENVELOPE_REJECTED')
        self._token = token

    @property
    def reader(self):
        self.authenticate()
        if self._reader is None:
            self._reader = TeachingERPReader(replace(self.config, access_token=self._token), transport=self.transport, sleeper=self.sleeper)
        return self._reader

    def _send(self, path, body, *, auth=False):
        # Private transport; the only public mutations below construct their paths.
        if len(self.events) >= 4:
            raise ERPError('ERP_REQUEST_BUDGET_EXHAUSTED')
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if not auth:
            headers['Authorization'] = 'Bearer ' + self._token
        event = dict(method='POST', path=path, observedAt=datetime.now(timezone.utc).isoformat())
        self.events.append(event)
        self.sleeper(self.config.interval)
        try:
            status, raw = self.transport('POST', path, headers, json.dumps(body, ensure_ascii=False, allow_nan=False).encode(), self.config)
        except Exception:
            event['code'] = 'ERP_SEND_UNKNOWN'
            raise ERPError('ERP_SEND_UNKNOWN') from None
        event['httpStatus'] = status
        if not auth:
            event['responseFingerprint'] = hashlib.sha256(raw).hexdigest()
        if status not in {200, 201}:
            raise ERPError('ERP_WRITE_REJECTED' if 400 <= status < 500 else 'ERP_SEND_UNKNOWN', status)
        try:
            value = json.loads(raw)
            if not isinstance(value, dict) or 'code' in value and value['code'] not in {0, '0', 200, '200'}:
                raise ValueError()
            return value
        except (ValueError, TypeError):
            raise ERPError('ERP_SEND_UNKNOWN') from None

    def create_requisition(self, payload):
        allowed = {'order_sn', 'supplier_id', 'supplier_name', 'warehouse_name', 'order_time', 'purchase_currency',
                   'amount', 'purchase_user', 'source_plan_no', 'remark', 'item_list'}
        if (set(payload) != allowed or len(payload['item_list']) != 1
                or set(payload['item_list'][0]) != {'sku', 'product_id', 'quantity', 'unit_price', 'amount'}
                or type(payload['item_list'][0]['quantity']) is not int or not 1 <= payload['item_list'][0]['quantity'] <= 100000):
            raise ERPError('ERP_REQUISITION_PAYLOAD_REJECTED')
        self.authenticate()
        return self._send('/api/v1/purchase-orders', payload)

    def submit_requisition(self, erp_id):
        if not str(erp_id).isdigit() or not 0 < int(erp_id) < 10**20:
            raise ERPError('ERP_REQUISITION_ID_REJECTED')
        self.authenticate()
        return self._send(f'/api/v1/workflows/purchase-orders/{erp_id}/submit', {})

    def find_requisition(self, number):
        return self.reader.read('/api/v1/purchase-orders', dict(field='order_sn', q=number, match='exact'), page_size=2, max_pages=2)

    def read_requisition(self, erp_id):
        return self.reader.detail('purchase-orders', erp_id)
