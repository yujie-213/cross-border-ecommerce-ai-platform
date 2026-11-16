"""python -m commerce_hub.entrypoints.grant_after_sales --config PATH [--apply]."""
import argparse
import json
from pathlib import Path

from commerce_hub.bootstrap.local_platform import configure, runtime
from commerce_hub.governance.access.b_admin import grant_after_sales
from commerce_hub.governance.observability.service import Audit
from commerce_hub.infrastructure.database import Database, assert_migration_target


def main():
    parser = argparse.ArgumentParser(description='Explicit B-only local administrator grants; default dry-run')
    parser.add_argument('--config', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    database = None
    try:
        config = json.loads(Path(args.config).read_text(encoding='utf-8'))
        local = runtime()  # Never creates or resets runtime/account/session configuration.
        settings = configure(local)
        assert_migration_target(settings)
        database = Database(settings)
        result = grant_after_sales(database.engine, Audit(), installation_id=local['installationId'],
            tenant_id=settings.local_app_tenant, configuration=config, dry_run=not args.apply)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception:
        print('B_GRANT_COMMAND_FAILED: inspect configuration, migration and current B grants; no account reset performed')
        return 1
    finally:
        if database:
            database.close()


if __name__ == '__main__':
    raise SystemExit(main())
