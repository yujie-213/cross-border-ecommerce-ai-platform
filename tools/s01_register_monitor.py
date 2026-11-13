"""Explicitly verify and register an owner-approved private ERP membership file.

No ERP mutations, models, broad discovery, migration or implicit activation.
The mapping records real IDs and import evidence; names never grant membership.
"""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-live', action='store_true')
    parser.add_argument('--mappings', type=Path)
    args = parser.parse_args()
    if not args.execute_live:
        print('NOT_RUN: explicit --execute-live required; no network or database mutation')
        return
    root = Path(__file__).resolve().parents[1]
    if args.mappings is None or not args.mappings.resolve().is_relative_to((root/'data/private').resolve()):
        raise ValueError('PRIVATE_APPROVED_MAPPING_REQUIRED')
    os.environ.update(COMMERCE_ENVIRONMENT='test', COMMERCE_MODEL_PROVIDER='mock', COMMERCE_MODEL_NETWORK_ENABLED='false')
    from dotenv import dotenv_values
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database, assert_migration_target
    from commerce_hub.adapters.erp import ERPConfig, TeachingERPReader, https_transport, AUTH_PATH
    from commerce_hub.data.sync.online import OnlineMapping, collect
    from commerce_hub.data.projection.online import observed, normalize_online
    from commerce_hub.data.projection.monitor import MonitorRegistry
    from commerce_hub.data.quality.online import capture_online, calculation_snapshot
    mappings = [OnlineMapping.model_validate(m).validate_scope() for m in json.loads(args.mappings.read_text(encoding='utf-8'))]
    if not mappings or any(m.monitor is None for m in mappings): raise ValueError('OWNED_MONITOR_BINDINGS_REQUIRED')
    values = dotenv_values(root/'.env.erp', interpolate=False)
    private = root/'data/private/s01-monitor-registration'/uuid4().hex
    private.mkdir(parents=True)
    class Context:
        def check(self): pass
    for index, mapping in enumerate(mappings):
        serial = [0]
        folder = private/str(index); folder.mkdir()
        def transport(method, target, headers, body, config):
            status, raw = https_transport(method, target, headers, body, config)
            if not target.startswith(AUTH_PATH):
                serial[0] += 1; (folder/f'response-{serial[0]:03}.json').write_bytes(raw)
            return status, raw
        reader = TeachingERPReader(ERPConfig(username=values.get('ERP_USERNAME') or '',
            password=values.get('ERP_PASSWORD') or '', access_token=values.get('ERP_ACCESS_TOKEN') or '',
            max_requests=100), transport=transport)
        captures, receipt = collect(reader, mapping, Context(), uuid4().hex)
        projection, verified = observed(captures, mapping, receipt)
        normalization = normalize_online(captures, mapping, receipt, verified)
        asset = capture_online(projection, receipt, verified, normalization)
        (folder/'verification.json').write_text(json.dumps(dict(captures=captures, asset=asset),ensure_ascii=False,indent=2),encoding='utf-8')
        if not verified or not calculation_snapshot(asset).calculation_allowed:
            raise ValueError('MONITOR_INDEPENDENT_READBACK_OR_INPUT_VERIFICATION_FAILED')
    settings = load_settings(); assert_migration_target(settings); database = Database(settings)
    try:
        if not database.schema_ready(): raise ValueError('EXPLICIT_MIGRATION_REQUIRED')
        registry = MonitorRegistry(database.engine, mappings[0].scope['tenantId'])
        digest = registry.activate([m.model_dump(mode='json') for m in mappings], 'owner-authorized-operator')
        (private/'registration.json').write_text(json.dumps(dict(contentDigest=digest,
            activeMembers=len(mappings),scopeVersion=mappings[0].monitor.scopeVersion)),encoding='utf-8')
        print('PASS: independently verified version registered; private receipt saved')
    finally: database.close()


if __name__ == '__main__': main()
