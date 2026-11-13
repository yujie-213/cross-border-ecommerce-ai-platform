"""Loopback-only production frontend and fixed-target same-origin API proxy."""
import asyncio,http.client,os
from pathlib import Path
from fastapi import FastAPI,Request
from starlette.responses import Response,FileResponse
from starlette.staticfiles import StaticFiles

ROOT=Path(__file__).resolve().parents[4]


def forward(method,path,body,headers):
    conn=http.client.HTTPConnection('127.0.0.1',int(os.environ['COMMERCE_LOCAL_API_PORT']),timeout=100)
    try:
        conn.request(method,path,body,headers)
        response=conn.getresponse();data=response.read()
        safe=[(k.lower().encode(),v.encode('latin-1')) for k,v in response.getheaders() if k.lower() not in {'connection','transfer-encoding','content-length','server','date'}]
        return response.status,data,safe
    finally:conn.close()


def create_app():
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    @app.api_route('/api/{path:path}',methods=['GET','POST','DELETE','PUT','PATCH','HEAD','OPTIONS'])
    async def proxy(path:str,request:Request):
        try:length=int(request.headers.get('content-length','0'))
        except ValueError:return Response(status_code=400)
        if length<0:return Response(status_code=400)
        if length>1048576:return Response(status_code=413)
        body=bytearray()
        async for part in request.stream():
            body.extend(part)
            if len(body)>1048576:return Response(status_code=413)
        body=bytes(body)
        headers={k:v for k,v in request.headers.items() if k.lower() in {'accept','content-type','cookie','x-csrf-token','origin','idempotency-key','authorization'}}
        target='/api/'+path+('?' + request.url.query if request.url.query else '')
        try:status,data,raw=await asyncio.to_thread(forward,request.method,target,body,headers)
        except (OSError,http.client.HTTPException,TimeoutError):return Response('{"code":"LOCAL_API_UNAVAILABLE"}',status_code=503,media_type='application/json')
        response=Response(data,status_code=status);response.raw_headers=raw+[(b'cache-control',b'no-store')]
        return response
    @app.get('/health/frontend')
    def health():return dict(status='ready',service='commerce-local-frontend')
    dist=ROOT/'frontend/dist'
    app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
    @app.get('/{path:path}')
    def index(path:str):
        if path not in {'','index.html'}:return Response(status_code=404)
        return FileResponse(dist/'index.html',headers={'Cache-Control':'no-store'})
    return app
