"""Browser recovery must not require waiting for an invalid HttpOnly cookie to expire."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import jwt
import pytest

from commerce_hub.entrypoints.http.app import create_app
from tests.integration.http.test_task_api import http_fixture

pytestmark = pytest.mark.mysql


@pytest.mark.parametrize('mode', ['expired', 'conflicting_bearer'])
def test_unauthenticated_browser_cookie_is_expired_and_reconnect_requires_valid_bearer(http_fixture, mode):
    settings, registry, token, scope, claims, key = http_fixture
    with TestClient(create_app(settings, registry), base_url='https://testserver') as client:
        invalid = jwt.encode(dict(claims, exp=int(datetime.now(timezone.utc).timestamp()) - 1), key, algorithm='HS256')
        client.cookies.set('commerce_session', invalid, domain='testserver.local', path='/')
        client.cookies.set('commerce_csrf', 'stale-csrf', domain='testserver.local', path='/')
        response = (client.post('/api/v1/session', headers={'Authorization': 'Bearer ' + token}) if mode == 'conflicting_bearer'
            else client.get('/api/v1/analysis-tasks/not-a-task'))
        assert response.status_code == 401
        headers = response.headers.get_list('set-cookie')
        for name in ['commerce_session', 'commerce_csrf']:
            value = next((h for h in headers if h.startswith(name + '=')), '')
            assert 'Max-Age=0' in value and 'Secure' in value and 'SameSite=strict' in value
        assert token not in response.text and invalid not in response.text
        # No anonymous fallback: clearing the cookie cannot authenticate a caller.
        assert client.post('/api/v1/session').status_code == 401
        reconnected = client.post('/api/v1/session', headers={'Authorization': 'Bearer ' + token})
        assert reconnected.status_code == 200
        assert reconnected.json()['principalRef']['tenantId'] == scope['tenantId']
