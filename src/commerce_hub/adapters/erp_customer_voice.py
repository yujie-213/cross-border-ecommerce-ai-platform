"""One explicit internal handling mutation. Never sends a customer message."""
from dataclasses import replace
import json
import time

from .erp import AUTH_PATH, ERPError, TeachingERPReader, https_transport


class TeachingVoiceClient:
    def __init__(self, config, *, transport=https_transport, sleeper=time.sleep):
        self.config, self.transport, self.sleeper = config, transport, sleeper
        self.token = config.access_token
        self._reader = None

    def _post(self, path, payload, *, auth=False):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if not auth: headers['Authorization'] = 'Bearer ' + self.token
        self.sleeper(self.config.interval)
        try:
            status, raw = self.transport('POST', path, headers,
                json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(), self.config)
        except Exception:
            raise ERPError('ERP_SEND_UNKNOWN') from None
        if status not in {200, 201}:
            raise ERPError('ERP_WRITE_REJECTED' if 400 <= status < 500 else 'ERP_SEND_UNKNOWN', status)
        try:
            value = json.loads(raw)
            if not isinstance(value, dict) or ('code' in value and value['code'] not in {0, '0', 200, '200'}):
                raise ValueError()
            return value
        except (ValueError, TypeError):
            raise ERPError('ERP_SEND_UNKNOWN') from None

    @property
    def reader(self):
        if not self.token:
            if not self.config.username or not self.config.password: raise ERPError('ERP_CREDENTIALS_MISSING')
            value = self._post(AUTH_PATH, dict(appId=self.config.username, appSecret=self.config.password), auth=True)
            token = value.get('data', {}).get('access_token')
            if not isinstance(token, str) or not 1 <= len(token) <= 8192 or '\r' in token or '\n' in token:
                raise ERPError('ERP_AUTH_ENVELOPE_REJECTED')
            self.token = token
        if self._reader is None:
            self._reader = TeachingERPReader(replace(self.config, access_token=self.token), transport=self.transport, sleeper=self.sleeper)
        return self._reader

    def history(self, kind, record_id, store_id):
        self._identity(kind, record_id)
        return self.reader.read('/api/v1/customer-voice', dict(kind=kind, record_id=record_id,
            store_id=store_id, history='1'), page_size=50, max_pages=5).records

    @staticmethod
    def _identity(kind, record_id):
        if kind not in {'reviews', 'feedback'} or not str(record_id).isdigit() or not 0 < int(record_id) < 10**20:
            raise ERPError('ERP_VOICE_PAYLOAD_REJECTED')

    def append(self, kind, record_id, version, note, key):
        self._identity(kind, record_id)
        if type(version) is not int or version < 0 or not isinstance(note, str) or not 1 <= len(note) <= 2000 or not isinstance(key, str) or not 1 <= len(key) <= 100:
            raise ERPError('ERP_VOICE_PAYLOAD_REJECTED')
        self.reader  # Authenticate before the sole mutation.
        return self._post('/api/v1/customer-voice', dict(kind=kind, record_id=int(record_id),
            expected_version=version, handling_status='resolved', note=note, request_key=key))
