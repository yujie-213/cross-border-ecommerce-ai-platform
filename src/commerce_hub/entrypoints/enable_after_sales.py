"""Explicit local B enablement; preserves administrator credentials, sessions and S01 grants."""
import argparse
from copy import deepcopy
import json

from sqlalchemy import select
from commerce_hub.bootstrap.local_platform import configure,runtime,PRIVATE as PLATFORM_PRIVATE
from commerce_hub.bootstrap.after_sales import PRIVATE
from commerce_hub.governance.access.b_admin import grant_after_sales
from commerce_hub.governance.access.b_resources import B_ACTIONS,B_ACTION_KINDS
from commerce_hub.governance.access.tables import b_resource_grants,principals,sessions,grants
from commerce_hub.governance.access.local import admins
from commerce_hub.governance.observability.service import Audit
from commerce_hub.infrastructure.database import Database,migrate,assert_migration_target
from commerce_hub.scenarios.after_sales.common import SOURCE,SOURCE_TENANT,WORKSPACE,digest


def configuration(tenant):
    resources=[dict(resourceKind=kind,sourceNature=source,sourceTenant=source_tenant,
        resourceIds=[],allowCreate=True,datasetVersions={}) for kind,source,source_tenant in [
            ('CASE',SOURCE,SOURCE_TENANT),('CASE','TEACHING_ERP_OBSERVED','1'),('POLICY',SOURCE,SOURCE_TENANT),('DATASET',SOURCE,SOURCE_TENANT)]]
    return dict(schemaVersion='1.0.0',configurationVersion='b-v1-local-20261116',tenantId=tenant,workspaceId=WORKSPACE,
        grants={action:dict(schemaVersion='1.0.0',tenantId=tenant,workspaceId=WORKSPACE,
            resources=[deepcopy(r) for r in resources if r['resourceKind'] in B_ACTION_KINDS[action]]) for action in B_ACTIONS})


def account_fingerprint(db,tenant):
    with db.engine.connect() as conn:
        data={table.name:[dict(r) for r in conn.execute(select(table).filter_by(tenant_id=tenant).order_by(*table.primary_key.columns)).mappings()] for table in [admins,principals,sessions,grants]}
    return digest(json.loads(json.dumps(data,default=str)))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    local=runtime();settings=configure(local);assert_migration_target(settings)
    if args.apply:migrate(settings)
    db=Database(settings)
    try:
        before=account_fingerprint(db,settings.local_app_tenant)
        config=configuration(settings.local_app_tenant)
        with db.engine.connect() as conn:
            existing=conn.execute(select(b_resource_grants).filter_by(tenant_id=settings.local_app_tenant,workspace_id=WORKSPACE)).mappings().all()
        if existing:
            # An evolved scope is not overwritten by re-running initial setup.
            if (set(r['action'] for r in existing)!=B_ACTIONS or any(not r['active'] or r['configuration_hash']!=digest(config) for r in existing)):
                raise ValueError('B_EXISTING_GRANTS_REQUIRE_EXPLICIT_REVISION')
            result=dict(existing=True,grants=len(existing),dryRun=not args.apply)
        else:
            result=grant_after_sales(db.engine,Audit(),installation_id=local['installationId'],tenant_id=settings.local_app_tenant,
                configuration=config,dry_run=not args.apply)
        if args.apply:
            PRIVATE.mkdir(parents=True,exist_ok=True)
            # Explicit source scope is built from a fresh permitted ERP catalog.
            # Failure leaves teaching workflows usable; no substitute source facts.
            try:
                from commerce_hub.adapters.erp import TeachingERPReader
                from commerce_hub.bootstrap.s01_v2 import erp_config
                batch=TeachingERPReader(erp_config()).read('/api/v1/store-authorizations',page_size=50,max_pages=2)
                if not batch.complete:raise ValueError('ERP_SCOPE_INCOMPLETE')
                stores={r['store_name']:dict(storeId=str(r['id']),sourceTenant=str(r['tenant_id'])) for r in batch.records
                    if str(r.get('tenant_id'))=='1' and r.get('store_name')}
                (PRIVATE/'source-scope.json').write_text(json.dumps(stores,ensure_ascii=False),encoding='utf-8')
                result['sourceStoreCount']=len(stores)
            except Exception:result['sourceStatus']='ERP_SCOPE_NOT_VERIFIED'
            local['afterSalesEnabled']=True
            (PLATFORM_PRIVATE/'runtime.json').write_text(json.dumps(local,ensure_ascii=False),encoding='utf-8')
        after=account_fingerprint(db,settings.local_app_tenant)
        if before!=after:raise ValueError('LEGACY_ACCOUNT_CHANGED')
        print(json.dumps(dict(status='B_ENABLED' if args.apply else 'B_DRY_RUN',legacyAccountUnchanged=True,
            modelNetworkEnabled=False,**result),ensure_ascii=False))
    finally:db.close()


if __name__=='__main__':
    try:main()
    except Exception:
        print('B_ENABLE_FAILED: inspect current B grants and migration; existing password/session unchanged by this command')
        raise SystemExit(1)
