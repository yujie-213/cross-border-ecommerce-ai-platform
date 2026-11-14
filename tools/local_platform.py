"""Windows daily launcher: managed API/Worker/frontend, explicit initialization, no business IO."""
from pathlib import Path
import argparse,getpass,hashlib,json,msvcrt,os,shutil,socket,subprocess,sys,time,webbrowser
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'data/private/local-platform'
sys.path.insert(0,str(ROOT/'src'))
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')


def write(path,value):
    temp=path.with_suffix('.part');temp.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');temp.replace(path)


def scope_lock():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    f=(PRIVATE/'instance.lock').open('a+b');f.seek(0)
    try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:f.close();return None
    if os.fstat(f.fileno()).st_size==0:f.write(b'0');f.flush()
    return f


def available(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        try:sock.bind(('127.0.0.1',port))
        except OSError:raise ValueError('PORT_OCCUPIED:'+str(port)) from None


def preflight(settings,config):
    from commerce_hub.infrastructure.database import Database,assert_migration_target
    from commerce_hub.governance.access import AccessControl
    from commerce_hub.governance.access.local import LocalAdmin
    from commerce_hub.scenarios.s01_v2.handler import collection_scope
    from commerce_hub.bootstrap.s01_v2 import erp_config
    assert_migration_target(settings)
    if not (ROOT/'.env').is_file():raise ValueError('DATABASE_CONFIGURATION_MISSING')
    erp=erp_config()
    if not (erp.access_token or erp.username and erp.password):
        print('ERP 未配置：可登录查看本地历史；新分析需要真实 ERP 凭据，不使用模拟数据。',flush=True)
    if config['modelEnabled'] and not settings.model_api_key.get_secret_value():raise ValueError('MODEL_CONFIGURATION_MISSING')
    db=Database(settings)
    try:
        if not db.check():raise ValueError('DATABASE_UNAVAILABLE')
        if not db.schema_ready():raise ValueError('EXPLICIT_MIGRATION_REQUIRED')
        access=AccessControl(db.engine,settings.auth_issuer,settings.auth_audience,settings.auth_signing_key.get_secret_value())
        if not LocalAdmin(access,settings.local_app_tenant,collection_scope(settings.local_app_tenant)).initialized():raise ValueError('ADMIN_NOT_INITIALIZED')
    finally:db.close()
    available(config['apiPort']);available(config['webPort'])


def frontend(job):
    candidates=[ROOT/'frontend/package.json',ROOT/'frontend/package-lock.json',ROOT/'frontend/index.html']+sorted((ROOT/'frontend/src').rglob('*'))+sorted((ROOT/'frontend').glob('vite.config.*'))
    digest=hashlib.sha256(b''.join(p.relative_to(ROOT).as_posix().encode()+p.read_bytes() for p in candidates if p.is_file())).hexdigest()
    marker=PRIVATE/'frontend-build.json';index=ROOT/'frontend/dist/index.html'
    if marker.exists() and index.exists():
        saved=json.loads(marker.read_text(encoding='utf-8'))
        if saved.get('sourceDigest')==digest and saved.get('indexDigest')==hashlib.sha256(index.read_bytes()).hexdigest():return
    npm=shutil.which('npm.cmd');node=shutil.which('node.exe')
    if not npm or not node:raise ValueError('NODE_NPM_REQUIRED')
    if not (ROOT/'frontend/node_modules/.bin/vite.cmd').is_file():raise ValueError('FRONTEND_DEPENDENCIES_MISSING')
    print('正在检查并构建前端，请稍候…',flush=True)
    with (PRIVATE/'build.log').open('wb') as log:
        child=job.spawn([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',npm,'run','build'],cwd=ROOT/'frontend',stdout=log,stderr=subprocess.STDOUT)
        if child.wait(timeout=180)!=0:raise ValueError('FRONTEND_BUILD_FAILED')
    write(marker,dict(sourceDigest=digest,indexDigest=hashlib.sha256(index.read_bytes()).hexdigest()))


def ready(url,child):
    import httpx
    with httpx.Client(trust_env=False,timeout=2) as client:
        until=time.monotonic()+25
        while time.monotonic()<until:
            if child.poll() is not None:raise ValueError('MANAGED_SERVICE_STOPPED')
            try:
                if client.get(url).status_code==200:return
            except httpx.TransportError:pass
            time.sleep(.1)
    raise ValueError('SERVICE_READINESS_TIMEOUT')


def start(open_browser=True):
    from commerce_hub.bootstrap.local_platform import runtime,configure
    from commerce_hub.infrastructure.windows_job import Job
    config=runtime();url='http://localhost:'+str(config['webPort'])
    lock=scope_lock()
    if lock is None:
        print('平台已启动或正在启动；未创建重复进程。',flush=True)
        if open_browser:webbrowser.open(url)
        return
    job=None;logs=[];state=PRIVATE/'running.json';identity=uuid4().hex
    try:
        settings=configure(config);preflight(settings,config)
        job=Job();frontend(job)
        def spawn(name,args):
            log=(PRIVATE/(name+'.log')).open('ab');logs.append(log)
            return job.spawn(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy())
        api=spawn('api',[sys.executable,'-m','uvicorn','commerce_hub.bootstrap.local_platform:create_app','--factory','--host','127.0.0.1','--port',str(config['apiPort']),'--no-access-log','--no-server-header'])
        ready('http://127.0.0.1:'+str(config['apiPort'])+'/health/ready',api)
        worker=spawn('worker',[sys.executable,'-m','commerce_hub.bootstrap.local_platform','worker'])
        front=spawn('frontend',[sys.executable,'-m','uvicorn','commerce_hub.entrypoints.http.local_frontend:create_app','--factory','--host','127.0.0.1','--port',str(config['webPort']),'--no-access-log','--no-server-header'])
        ready('http://127.0.0.1:'+str(config['webPort'])+'/health/frontend',front)
        if worker.poll() is not None:raise ValueError('MANAGED_SERVICE_STOPPED')
        write(state,dict(status='RUNNING',instanceId=identity,workspace=str(ROOT.resolve()),webUrl=url,pids=[api.pid,worker.pid,front.pid],supervisorPid=os.getpid()))
        print('平台已就绪：'+url+'\n请用本地管理员账号登录。持续运行，无自动关闭期限。\n停止：双击 Stop-Platform.cmd，或在本窗口按 Ctrl+C / 关闭本窗口。',flush=True)
        if open_browser:webbrowser.open(url)
        while True:
            if any(child.poll() is not None for child in [api,worker,front]):raise ValueError('MANAGED_SERVICE_STOPPED')
            control=PRIVATE/'control.json'
            if control.exists():
                command=json.loads(control.read_text(encoding='utf-8'))
                if command==dict(instanceId=identity,action='stop'):break
            time.sleep(.2)
    except KeyboardInterrupt:pass
    finally:
        if job:job.close()
        for log in logs:log.close()
        write(state,dict(status='STOPPED',instanceId=identity,workspace=str(ROOT.resolve())))
        lock.close()
        print('本项目管理的进程已关闭；业务记录和其他服务未改动。',flush=True)


def initialize(reset=False):
    from commerce_hub.bootstrap.local_platform import runtime,configure
    from commerce_hub.infrastructure.database import Database,migrate,assert_migration_target
    from commerce_hub.governance.access import AccessControl
    from commerce_hub.governance.access.local import LocalAdmin
    from commerce_hub.scenarios.s01_v2.handler import collection_scope
    config=runtime(create=True);settings=configure(config);assert_migration_target(settings)
    if not reset:migrate(settings) # Explicit Initialize command only; never ordinary start.
    db=Database(settings)
    try:
        if not db.schema_ready():raise ValueError('EXPLICIT_MIGRATION_REQUIRED')
        access=AccessControl(db.engine,settings.auth_issuer,settings.auth_audience,settings.auth_signing_key.get_secret_value())
        admin=LocalAdmin(access,settings.local_app_tenant,collection_scope(settings.local_app_tenant),settings.local_session_seconds)
        if admin.initialized() and not reset:print('管理员已初始化，密码未改动；可直接双击 Start-Platform.cmd。');return
        password=getpass.getpass('管理员新密码（输入不显示）: ')
        again=getpass.getpass('再次输入密码: ')
        if password!=again:raise ValueError('PASSWORD_CONFIRMATION_MISMATCH')
        admin.initialize(password,reset=reset);password=again=''
        print('本地 admin 已'+('重置，旧会话已撤销。' if reset else '初始化。请双击 Start-Platform.cmd。'))
    finally:db.close()


ERRORS={'LOCAL_CONFIGURATION_MISSING':'尚未初始化，请先双击 Initialize-Platform.cmd。','LOCAL_CONFIGURATION_INVALID':'本地私有配置无效，请检查 data/private/local-platform/runtime.json，勿公开其中密钥。',
 'DATABASE_UNAVAILABLE':'数据库不可连接，请核对本机 .env 和 MySQL 服务。','EXPLICIT_MIGRATION_REQUIRED':'数据库迁移未就绪，请显式运行 Initialize-Platform.cmd；启动不会自动迁移。',
 'ADMIN_NOT_INITIALIZED':'尚无本地管理员，请先运行 Initialize-Platform.cmd。','NODE_NPM_REQUIRED':'需要 Node.js/npm，请按 README 安装后重试。','FRONTEND_DEPENDENCIES_MISSING':'前端依赖未安装，请按 README 在 frontend 运行 npm ci。',
 'FRONTEND_BUILD_FAILED':'前端构建未通过，详细工程日志在 data/private/local-platform/build.log。','ERP_CONFIGURATION_MISSING':'缺少本机 .env.erp 凭据；启动不会尝试ERP登录。','MODEL_CONFIGURATION_MISSING':'AI已启用但缺少本机模型配置，请按README配置或关闭本地 modelEnabled。',
 'PASSWORD_CONFIRMATION_MISMATCH':'两次密码不一致，账号未变更。','PASSWORD_LENGTH_INVALID':'密码长度须为6—256个字符。','MANAGED_SERVICE_STOPPED':'项目子服务未能运行；已清理自管进程，私有日志在 data/private/local-platform。','SERVICE_READINESS_TIMEOUT':'服务未就绪；已清理本项目进程，请检查私有日志。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['start','stop','initialize','reset-admin']);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    try:
        if os.name!='nt':raise ValueError('WINDOWS_REQUIRED')
        if sys.version_info[:2]!=(3,13):raise ValueError('PYTHON_313_REQUIRED')
        if args.action=='start':start(not args.no_browser)
        elif args.action=='stop':
            state=PRIVATE/'running.json'
            if not state.exists():print('本项目没有已登记的运行实例。');return
            value=json.loads(state.read_text(encoding='utf-8'))
            if value.get('status')!='RUNNING' or value.get('workspace')!=str(ROOT.resolve()):print('本项目当前未运行。');return
            write(PRIVATE/'control.json',dict(instanceId=value['instanceId'],action='stop'));print('已请求停止本项目实例，不终止其他服务。')
        else:initialize(args.action=='reset-admin')
    except Exception as exc:
        code=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
        message=('端口 '+code.split(':')[1]+' 已被占用；请先核对服务或调整本地端口，不会终止占用者。') if code.startswith('PORT_OCCUPIED:') else ERRORS.get(code,'启动或配置失败，请按README核对Python依赖、数据库和本地配置；没有执行ERP业务操作。')
        print('未能完成：'+message,flush=True);raise SystemExit(1) from None

if __name__=='__main__':main()
