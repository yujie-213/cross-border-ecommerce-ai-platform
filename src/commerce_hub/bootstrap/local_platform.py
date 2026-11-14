"""Persistent local teaching composition. No fixture accounts, lifetime timer or startup business IO."""
from pathlib import Path
import json,os,secrets,sys
from uuid import uuid4
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[3]
PRIVATE=ROOT/'data/private/local-platform'


def runtime(create=False):
    path=PRIVATE/'runtime.json'
    if not path.exists():
        if not create:raise ValueError('LOCAL_CONFIGURATION_MISSING')
        PRIVATE.mkdir(parents=True,exist_ok=True)
        values=dotenv_values(ROOT/'.env',interpolate=False)
        config=dict(version=1,installationId=uuid4().hex,signingKey=secrets.token_urlsafe(64),apiPort=8765,webPort=5173,sessionSeconds=28800,
            modelEnabled=bool(values.get('COMMERCE_MODEL_API_KEY')),requisitionEnabled=True)
        with path.open('x',encoding='utf-8') as f:json.dump(config,f)
    config=json.loads(path.read_text(encoding='utf-8'))
    if (config.get('version')!=1 or not isinstance(config.get('signingKey'),str) or len(config['signingKey'])<64
        or not isinstance(config.get('installationId'),str) or len(config['installationId'])!=32
        or any(type(config.get(k)) is not int or not 1024<=config[k]<=65535 for k in ['apiPort','webPort'])
        or config['apiPort']==config['webPort'] or type(config.get('sessionSeconds')) is not int or not 300<=config['sessionSeconds']<=86400
        or any(type(config.get(k)) is not bool for k in ['modelEnabled','requisitionEnabled'])):raise ValueError('LOCAL_CONFIGURATION_INVALID')
    return config


def configure(config=None):
    config=config or runtime()
    os.environ.update(COMMERCE_ENVIRONMENT='test',COMMERCE_LOCAL_ADMIN_ENABLED='true',COMMERCE_LOCAL_SESSION_SECONDS=str(config['sessionSeconds']),
        COMMERCE_AUTH_ISSUER='commerce-local-'+config['installationId'],COMMERCE_AUTH_AUDIENCE='commerce-local-browser',COMMERCE_AUTH_SIGNING_KEY=config['signingKey'],
        COMMERCE_BROWSER_ORIGIN='http://localhost:'+str(config['webPort']),COMMERCE_LOCAL_API_PORT=str(config['apiPort']),
        COMMERCE_S01_V2_ENABLED='true',COMMERCE_S01_V2_APP_TENANT='s01-v2-teaching-local',COMMERCE_S01_V2_SOURCE_TENANT='1',
        COMMERCE_S01_V2_MODEL_ENABLED=str(config['modelEnabled']).lower(),COMMERCE_S01_V2_REQUISITION_ENABLED=str(config['requisitionEnabled']).lower(),
        COMMERCE_S01_V2_MODEL_AUTHORIZATION=config.get('modelAuthorization','s01-local-daily-use-20261115'),
        COMMERCE_MODEL_PROVIDER='deepseek' if config['modelEnabled'] else 'mock',COMMERCE_MODEL_NETWORK_ENABLED=str(config['modelEnabled']).lower(),
        COMMERCE_MODEL_MAX_OUTPUT_TOKENS='1024',COMMERCE_MODEL_MAX_CONCURRENT='1',COMMERCE_MODEL_TIMEOUT_SECONDS='30',COMMERCE_TASK_DEADLINE_SECONDS='600')
    from commerce_hub.bootstrap.settings import load_settings
    return load_settings()


def create_app():
    from commerce_hub.bootstrap.s01_v2 import registry
    from commerce_hub.entrypoints.http.app import create_app as factory
    settings=configure()
    return factory(settings,registry(settings))


if __name__=='__main__':
    if sys.argv[1:]!=['worker']:raise SystemExit('Explicit worker command required')
    from commerce_hub.bootstrap.s01_v2 import registry
    from commerce_hub.entrypoints.worker.__main__ import run
    settings=configure();raise SystemExit(run(settings,registry(settings)))
