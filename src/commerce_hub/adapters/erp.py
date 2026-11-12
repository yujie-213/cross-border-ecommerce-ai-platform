"""TEACHING_ERP_ONLY bounded read transport. Never use for production ERP."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import http.client
import json
import ssl
import time
from urllib.parse import urlencode

BASE_URL = "https://47.107.76.124/lingxing-erp"
READ_GET = frozenset({"/healthz", *["/api/v1/" + name for name in (
    "products", "warehouses", "store-authorizations", "listings", "inventory", "sales-orders",
    "purchase-orders", "supplier-deliveries", "inbound-orders", "supplier-quotes",
    "customer-tickets", "customer-voice", "replenishment")]})
# Local OpenAPI descriptions explicitly declare these three POSTs as read-only queries.
READ_POST = frozenset({"/erp/sc/data/mws/orders",
    "/erp/sc/routing/data/local_inventory/purchaseOrderList",
    "/erp/sc/routing/data/local_inventory/inventoryDetails"})
AUTH_PATH = "/api/auth-server/oauth/access-token"


class ERPError(RuntimeError):
    def __init__(self, code, status=None):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True)
class ERPConfig:
    base_url: str = BASE_URL
    username: str = field(default="", repr=False)
    password: str = field(default="", repr=False)
    access_token: str = field(default="", repr=False)
    timeout: float = 8
    max_requests: int = 60
    interval: float = .35

    def __post_init__(self):
        if (self.base_url != BASE_URL or not 0 < self.timeout <= 15
            or type(self.max_requests) is not int or not 1 <= self.max_requests <= 100
            or not .1 <= self.interval <= 2):
            raise ERPError("TEACHING_ERP_CONFIGURATION_REJECTED")


@dataclass(frozen=True)
class ReadBatch:
    records: tuple = field(repr=False)
    complete: bool
    pages: int
    total: int | None
    observed_at: str
    fingerprint: str


def https_transport(method, path, headers, body, config):
    # Context is local to this exact teacher host; no global TLS override or redirects.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    connection = http.client.HTTPSConnection("47.107.76.124", timeout=config.timeout, context=context)
    try:
        connection.request(method, "/lingxing-erp" + path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ERPError("ERP_RESPONSE_LIMIT")
        return response.status, raw
    finally:
        connection.close()


class TeachingERPReader:
    def __init__(self, config, *, transport=https_transport, sleeper=time.sleep):
        self.config, self.transport, self.sleeper = config, transport, sleeper
        self._token, self.requests = config.access_token, 0
        self.events = []

    def _request(self, method, path, values=None, *, authentication=False):
        if (authentication and (method != "POST" or path != AUTH_PATH)
            or not authentication and not (method == "GET" and path in READ_GET or method == "POST" and path in READ_POST)):
            raise ERPError("ERP_OPERATION_NOT_ALLOWLISTED")
        values = dict(values or {})
        if not authentication and any(any(s in key.lower() for s in ["token", "secret", "password", "url"]) for key in values):
            raise ERPError("ERP_UNSAFE_PARAMETERS")
        if len(json.dumps(values)) > 8192:
            raise ERPError("ERP_PARAMETER_LIMIT")
        if self.requests >= self.config.max_requests:
            raise ERPError("ERP_REQUEST_BUDGET_EXHAUSTED")
        self.requests += 1
        self.sleeper(self.config.interval)
        headers = {"Accept": "application/json"}
        if self._token and not authentication:
            headers["Authorization"] = "Bearer " + self._token
        body = None
        target = path
        if method == "POST":
            body = json.dumps(values).encode()
            headers["Content-Type"] = "application/json"
        elif values:
            target += "?" + urlencode(values, doseq=True)
        event = dict(method=method, path=path, parameterNames=sorted(values),
            observedAt=datetime.now(timezone.utc).isoformat(), teachingERPOnly=True, tlsVerification=False)
        try:
            status, raw = self.transport(method, target, headers, body, self.config)
        except ERPError:
            raise
        except TimeoutError:
            event.update(code="ERP_TIMEOUT")
            raise ERPError("ERP_TIMEOUT") from None
        except Exception:
            event.update(code="ERP_TRANSPORT_FAILURE")
            raise ERPError("ERP_TRANSPORT_FAILURE") from None
        finally:
            self.events.append(event)
        event["httpStatus"] = status
        if not authentication:
            event["responseFingerprint"] = hashlib.sha256(raw).hexdigest()
        if status != 200:
            code = "ERP_REDIRECT_REJECTED" if 300 <= status < 400 else "ERP_503" if status == 503 else "ERP_AUTH_REJECTED" if status in {401,403} else "ERP_HTTP_ERROR"
            event["code"] = code
            raise ERPError(code, status)
        try:
            result = json.loads(raw)
        except (ValueError, TypeError, UnicodeError):
            raise ERPError("ERP_INVALID_JSON") from None
        if not isinstance(result, dict):
            raise ERPError("ERP_INVALID_ENVELOPE")
        if not authentication:
            event["responseFingerprint"] = hashlib.sha256(raw).hexdigest()
        return result

    def _read_request(self, method, path, values):
        # One bounded retry for a known read-only operation; the same request budget is charged.
        for attempt in range(2):
            try:
                return self._request(method,path,values)
            except ERPError as error:
                if attempt or error.code not in {"ERP_503", "ERP_TIMEOUT"}:
                    raise
                self.sleeper(1)

    def authenticate(self):
        if self._token:
            return
        if not self.config.username or not self.config.password:
            raise ERPError("ERP_CREDENTIALS_MISSING")
        result = self._request("POST", AUTH_PATH,
            dict(appId=self.config.username, appSecret=self.config.password), authentication=True)
        data = result.get("data")
        token = data.get("access_token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not 1 <= len(token) <= 8192 or "\r" in token or "\n" in token:
            raise ERPError("ERP_AUTH_ENVELOPE_REJECTED")
        self._token = token

    def health(self):
        return self._request("GET", "/healthz")

    def discover(self, path, parameters=None, *, page_size=20):
        """Bounded candidate discovery. Incomplete results are never calculation inputs."""
        if path not in READ_GET - {"/healthz"} or type(page_size) is not int or not 1 <= page_size <= 20:
            raise ERPError("ERP_DISCOVERY_REJECTED")
        params = dict(parameters or {})
        if set(params) & {"offset", "limit", "view"}:
            raise ERPError("ERP_PAGINATION_IS_SERVER_CONTROLLED")
        self.authenticate()
        query = dict(params, offset=0, limit=page_size)
        if path in {"/api/v1/inventory", "/api/v1/sales-orders"}:
            query["view"] = "full"
        result = self._read_request("GET", path, query)
        items, total = result.get("items"), result.get("total")
        if (not isinstance(items,list) or any(not isinstance(x,dict) for x in items)
            or type(total) is not int or total < len(items) or len(items)>page_size):
            raise ERPError("ERP_INVALID_PAGE")
        text = json.dumps(items,sort_keys=True,ensure_ascii=False,default=str)
        return ReadBatch(tuple(items),len(items)==total,1,total,datetime.now(timezone.utc).isoformat(),hashlib.sha256(text.encode()).hexdigest())

    def read(self, path, parameters=None, *, method="GET", page_size=20, max_pages=5):
        if (type(page_size) is not int or not 1 <= page_size <= 50
            or type(max_pages) is not int or not 1 <= max_pages <= 5):
            raise ERPError("ERP_PAGINATION_LIMIT")
        # Reject mutations before authentication or any network request.
        if not (method == "GET" and path in READ_GET - {"/healthz"} or method == "POST" and path in READ_POST):
            raise ERPError("ERP_OPERATION_NOT_ALLOWLISTED")
        params = dict(parameters or {})
        if set(params) & {"offset", "limit", "length", "view"}:
            raise ERPError("ERP_PAGINATION_IS_SERVER_CONTROLLED")
        self.authenticate()
        rows, total, signatures, record_ids = [], None, set(), set()
        for page in range(max_pages):
            query = dict(params, offset=len(rows), **({"limit":page_size, "view":"full"} if method == "GET" and path in {"/api/v1/inventory","/api/v1/sales-orders"} else {"limit":page_size} if method == "GET" else {"length":page_size}))
            result = self._read_request(method, path, query)
            if method == "GET":
                items, count = result.get("items"), result.get("total")
            else:
                if result.get("code") not in {0, "0", 200, "200"}:
                    raise ERPError("ERP_BUSINESS_ERROR")
                data = result.get("data")
                items = data if isinstance(data, list) else data.get("list") if isinstance(data, dict) else None
                count = result.get("total", data.get("total") if isinstance(data, dict) else None)
            if (not isinstance(items,list) or any(not isinstance(x,dict) for x in items)
                or type(count) is not int or count < 0 or len(items) > page_size):
                raise ERPError("ERP_INVALID_PAGE")
            if total is not None and total != count:
                raise ERPError("ERP_PAGINATION_DRIFT")
            total = count
            signature = hashlib.sha256(json.dumps(items,sort_keys=True).encode()).hexdigest()
            if items and signature in signatures:
                raise ERPError("ERP_REPEATED_PAGE")
            signatures.add(signature)
            for item in items:
                key = json.dumps(["id", item["id"]] if item.get("id") is not None else ["row",item],sort_keys=True)
                if key in record_ids:
                    raise ERPError("ERP_DUPLICATE_RECORD")
                record_ids.add(key)
            rows.extend(items)
            if len(rows) > total or not items and len(rows) < total:
                raise ERPError("ERP_PAGINATION_INCOMPLETE")
            if len(rows) == total:
                text = json.dumps(rows,sort_keys=True,ensure_ascii=False,default=str)
                return ReadBatch(tuple(rows), True, page+1, total, datetime.now(timezone.utc).isoformat(),hashlib.sha256(text.encode()).hexdigest())
        raise ERPError("ERP_PAGINATION_LIMIT_REACHED")
