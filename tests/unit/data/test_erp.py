"""All transport responses here are OFFLINE fixtures, never live source evidence."""
import json
import ssl
import pytest
from commerce_hub.adapters.erp import ERPConfig,TeachingERPReader,ERPError,https_transport

class Transport:
    def __init__(self,*responses):self.responses=list(responses);self.calls=[]
    def __call__(self,*args):
        self.calls.append(args)
        value=self.responses.pop(0)
        if isinstance(value,Exception):raise value
        return value[0],json.dumps(value[1]).encode()

def reader(transport,**options):
    return TeachingERPReader(ERPConfig(access_token="OFFLINE_TOKEN_DO_NOT_LOG",**options),transport=transport,sleeper=lambda _:None)

@pytest.mark.parametrize("method,path",[("POST","/api/v1/purchase-orders"),("DELETE","/api/v1/inventory"),("GET","https://evil.invalid"),("GET","/api/v1/products/../workflows"),("PUT","/api/v1/products")])
def test_mutation_or_unknown_destination_is_denied_before_authentication(method,path):
    transport=Transport();r=TeachingERPReader(ERPConfig(username="OFFLINE_USER",password="OFFLINE_PASSWORD"),transport=transport)
    with pytest.raises(ERPError,match="NOT_ALLOWLISTED"):r.read(path,method=method)
    assert not transport.calls and r.requests==0

@pytest.mark.parametrize("url",["http://47.107.76.124/lingxing-erp","https://evil.invalid/lingxing-erp","https://47.107.76.124/lingxing-erp?x=1","https://47.107.76.124/lingxing-erp/"])
def test_teaching_only_destination_is_exact(url):
    with pytest.raises(ERPError,match="CONFIGURATION_REJECTED"):ERPConfig(base_url=url)

def test_tls_exception_is_connection_local_and_never_follows_redirect(monkeypatch):
    seen=[]
    class Response:
        status=302
        def read(self,_):return b'{}'
    class Connection:
        def __init__(self,host,timeout,context):seen.append((host,context))
        def request(self,*a,**k):pass
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr("commerce_hub.adapters.erp.http.client.HTTPSConnection",Connection)
    r=TeachingERPReader(ERPConfig(access_token="OFFLINE"),sleeper=lambda _:None)
    with pytest.raises(ERPError,match="REDIRECT_REJECTED"):r.read("/api/v1/products")
    assert len(seen)==1 and seen[0][0]=="47.107.76.124" and seen[0][1].verify_mode==ssl.CERT_NONE
    assert ssl.create_default_context().verify_mode==ssl.CERT_REQUIRED

def test_auth_secret_and_token_never_enter_events_or_configuration_repr():
    t=Transport((200,{"data":{"access_token":"OFFLINE_TOKEN_DO_NOT_LOG"}}),(200,{"items":[],"total":0}))
    r=TeachingERPReader(ERPConfig(username="OFFLINE_USER",password="OFFLINE_PASSWORD"),transport=t,sleeper=lambda _:None)
    assert r.read("/api/v1/products").complete
    public=json.dumps(r.events)+repr(r.config)
    assert all(x not in public for x in ["OFFLINE_USER","OFFLINE_PASSWORD","OFFLINE_TOKEN_DO_NOT_LOG"])
    assert t.calls[1][2]["Authorization"]=="Bearer OFFLINE_TOKEN_DO_NOT_LOG"
    assert "responseFingerprint" not in r.events[0]

@pytest.mark.parametrize("result,code",[(503,"ERP_503"),(401,"ERP_AUTH_REJECTED"),(403,"ERP_AUTH_REJECTED"),(302,"ERP_REDIRECT_REJECTED")])
def test_http_failure_never_becomes_an_empty_success_or_fixture(result,code):
    t=Transport((result,{"message":"PRIVATE_BODY"}),(result,{"message":"PRIVATE_BODY"}));r=reader(t)
    with pytest.raises(ERPError,match=code) as e:r.read("/api/v1/products")
    assert "PRIVATE_BODY" not in str(e.value)
    assert len(t.calls)==(2 if result==503 else 1)

def test_timeout_retry_and_request_budget_are_shared_not_reset():
    t=Transport(TimeoutError(),TimeoutError());r=reader(t,max_requests=2)
    with pytest.raises(ERPError,match="ERP_TIMEOUT"):r.read("/api/v1/products")
    assert r.requests==2
    with pytest.raises(ERPError,match="BUDGET_EXHAUSTED"):r.read("/api/v1/products")
    assert len(t.calls)==2

def test_bounded_retry_retains_failure_then_reads_real_transport_response():
    t=Transport((503,{}),(200,{"items":[{"id":1,"quantity":None}],"total":1}));r=reader(t)
    result=r.read("/api/v1/products")
    assert result.records[0]["quantity"] is None and r.requests==2
    assert [x["httpStatus"] for x in r.events]==[503,200]

def test_complete_pages_preserve_unknown_and_charge_all_requests():
    t=Transport((200,{"items":[{"id":1,"quantity":None}],"total":2}),(200,{"items":[{"id":2,"quantity":0}],"total":2}))
    r=reader(t);b=r.read("/api/v1/products",page_size=1)
    assert b.complete and b.pages==2 and b.records[0]["quantity"] is None and b.records[1]["quantity"]==0
    assert "offset=1" in t.calls[1][1]

@pytest.mark.parametrize("second,code",[({"items":[],"total":2},"PAGINATION_INCOMPLETE"),({"items":[{"id":2}],"total":3},"PAGINATION_DRIFT"),({"items":[{"id":1}],"total":2},"REPEATED_PAGE"),({"items":[{"id":1,"changed":True}],"total":2},"DUPLICATE_RECORD")])
def test_incomplete_or_unstable_pagination_fails_closed(second,code):
    r=reader(Transport((200,{"items":[{"id":1}],"total":2}),(200,second)))
    with pytest.raises(ERPError,match=code):r.read("/api/v1/products",page_size=1)

def test_bounded_discovery_is_explicitly_incomplete_and_read_does_not_silently_use_it():
    t=Transport((200,{"items":[{"id":1}],"total":9}),(200,{"items":[{"id":1}],"total":9}));r=reader(t)
    assert r.discover("/api/v1/inventory",page_size=1).complete is False
    with pytest.raises(ERPError,match="LIMIT_REACHED"):r.read("/api/v1/inventory",page_size=1,max_pages=1)

@pytest.mark.parametrize("envelope,code",[({"items":None,"total":0},"INVALID_PAGE"),({"items":[],"total":None},"INVALID_PAGE"),({"items":[{}],"total":0},"PAGINATION_INCOMPLETE"),({"items":[],"total":False},"INVALID_PAGE")])
def test_invalid_page_is_not_zero(envelope,code):
    with pytest.raises(ERPError,match=code):reader(Transport((200,envelope))).read("/api/v1/products")

def test_confirmed_read_only_post_uses_json_body_and_rejects_business_failure():
    t=Transport((200,{"code":0,"data":[],"total":0}));r=reader(t)
    assert r.read("/erp/sc/data/mws/orders",{"sid":1},method="POST").complete
    assert t.calls[0][0]=="POST" and json.loads(t.calls[0][3])["sid"]==1
    with pytest.raises(ERPError,match="BUSINESS_ERROR"):
        reader(Transport((200,{"code":1,"data":[],"total":0}))).read("/erp/sc/data/mws/orders",method="POST")


def test_d01_source_port_keeps_complete_batch_and_unknowns():
    from commerce_hub.data.sync import read_pages
    from commerce_hub.data.sync.teaching import TeachingReadSource
    r=reader(Transport((200,{"items":[{"id":1,"quantity":None}],"total":1})))
    source=TeachingReadSource(r,"/api/v1/products",{})
    assert read_pages(source)==({"id":1,"quantity":None},) and source.batch.complete


def test_d01_does_not_add_a_second_retry_or_switch_source_on_503():
    from commerce_hub.data.sync import read_pages,SourceFailure
    from commerce_hub.data.sync.teaching import TeachingReadSource
    t=Transport((503,{}),(503,{}));r=reader(t)
    with pytest.raises(SourceFailure,match="ERP_503"):
        read_pages(TeachingReadSource(r,"/api/v1/products",{}))
    assert len(t.calls)==2
