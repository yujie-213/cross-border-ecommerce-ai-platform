"""Password login is explicit and remains inside G01's current-policy boundary."""
from urllib.parse import urlsplit
from fastapi import Request,Depends
from pydantic import BaseModel,ConfigDict,Field,SecretStr
from starlette.responses import JSONResponse
from commerce_hub.governance.access.local import LocalAdmin
from commerce_hub.governance.access.service import AccessDenied
from commerce_hub.scenarios.s01_v2.handler import collection_scope
from commerce_hub.bootstrap.logging import trace_id
from sqlalchemy.exc import SQLAlchemyError


def secure_cookie(settings):
    if not settings.local_admin_enabled:return True
    origin=urlsplit(settings.browser_origin)
    if origin.scheme=='http' and origin.hostname not in {'localhost','127.0.0.1','::1'}:raise AccessDenied('CSRF_REJECTED')
    return origin.scheme=='https'


class Login(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username:str=Field(min_length=1,max_length=64)
    password:SecretStr=Field(min_length=1,max_length=256)


def admin(request):
    settings=request.app.state.settings
    if not settings.local_admin_enabled or request.app.state.tasks is None:raise AccessDenied('UNAUTHENTICATED')
    return LocalAdmin(request.app.state.tasks.access,settings.local_app_tenant,collection_scope(settings.local_app_tenant),settings.local_session_seconds)


def register_local_auth(app,principal):
    @app.get('/api/v1/auth/config')
    def config(request:Request):
        settings=request.app.state.settings
        return dict(mode='PASSWORD' if settings.local_admin_enabled else 'TRUSTED_BEARER',sessionSeconds=settings.local_session_seconds if settings.local_admin_enabled else 900)

    @app.post('/api/v1/auth/login')
    def login(body:Login,request:Request):
        settings=request.app.state.settings
        if request.headers.get('origin')!=settings.browser_origin:raise AccessDenied('CSRF_REJECTED')
        service=admin(request)
        try:token,expires=service.login(body.username,body.password.get_secret_value())
        except SQLAlchemyError:raise AccessDenied('AUTH_BACKEND_UNAVAILABLE') from None
        actor=service.access.authenticate(token)
        # Revoke an existing session on successful login; failed/foreign cookies cannot block recovery.
        previous=request.cookies.get('commerce_session')
        with service.engine.begin() as c:
            if previous:
                try:
                    old=service.access.authenticate(previous)
                    if old.tenant_id==actor.tenant_id and old.principal_id==actor.principal_id:service.access.revoke_token(c,old)
                except AccessDenied:pass
            request.app.state.tasks.audit.record(c,tenant_id=actor.tenant_id,principal_id=actor.principal_id,task_id=None,action='LOCAL_ADMIN_LOGIN',trace_id=trace_id.get(),details={})
        response=JSONResponse(dict(principalRef=dict(tenantId=actor.tenant_id,principalId=actor.principal_id),expiresAt=expires))
        response.set_cookie('commerce_session',token,httponly=True,secure=secure_cookie(settings),samesite='strict',max_age=service.seconds)
        response.set_cookie('commerce_csrf',service.access.issue_csrf(actor),secure=secure_cookie(settings),samesite='strict',max_age=service.seconds)
        return response

    @app.get('/api/v1/session')
    def current(request:Request,actor=Depends(principal)):
        return dict(principalRef=dict(tenantId=actor.tenant_id,principalId=actor.principal_id))
