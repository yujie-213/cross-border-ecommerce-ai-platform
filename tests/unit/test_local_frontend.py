"""Proxy/unit fixtures; the real three-process browser test is separate."""
from fastapi.testclient import TestClient
import pytest
import commerce_hub.entrypoints.http.local_frontend as frontend

@pytest.fixture
def front(tmp_path,monkeypatch):
    dist=tmp_path/'frontend/dist';(dist/'assets').mkdir(parents=True);(dist/'index.html').write_text('<h1>fixture</h1>');(dist/'assets/app.js').write_text('fixture')
    monkeypatch.setattr(frontend,'ROOT',tmp_path)
    with TestClient(frontend.create_app()) as client:yield client

def test_only_built_frontend_files_are_served(front):
    assert front.get('/').status_code==200 and front.get('/assets/app.js').status_code==200
    for path in ['/data/private/local-platform/runtime.json','/.env','/api_key','/unknown']:
        assert front.get(path).status_code==404

def test_same_origin_proxy_preserves_distinct_cookie_headers_and_csrf(front,monkeypatch):
    seen=[]
    def forward(method,path,body,headers):
        seen.append((method,path,headers));return 200,b'{}',[(b'set-cookie',b'commerce_session=fixture; HttpOnly; SameSite=strict'),(b'set-cookie',b'commerce_csrf=fixture; SameSite=strict')]
    monkeypatch.setattr(frontend,'forward',forward)
    response=front.post('/api/v1/auth/login',json={},headers={'Origin':'http://localhost:5173','X-CSRF-Token':'fixture','X-Untrusted-Header':'not-forwarded'})
    assert len(response.headers.get_list('set-cookie'))==2
    assert seen[0][0:2]==('POST','/api/v1/auth/login') and seen[0][2]['x-csrf-token']=='fixture' and 'x-untrusted-header' not in seen[0][2]

def test_proxy_bounds_payload_and_reports_backend_failure(front,monkeypatch):
    def unavailable(*args):raise ConnectionRefusedError()
    monkeypatch.setattr(frontend,'forward',unavailable)
    assert front.post('/api/v1/auth/login',content=b'x'*1048577).status_code==413
    assert front.post('/api/v1/auth/login',headers={'Content-Length':'invalid'}).status_code==400
    response=front.get('/api/v1/session');assert response.status_code==503 and response.json()['code']=='LOCAL_API_UNAVAILABLE'
