"""A new machine can open local history without claiming ERP connectivity."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize('database_ready', [True, False])
def test_missing_erp_warns_but_keeps_database_validation(tmp_path, monkeypatch, capsys, database_ready):
    path = Path(__file__).resolve().parents[2] / 'tools/local_platform.py'
    spec = importlib.util.spec_from_file_location('local_launcher', path)
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    (tmp_path / '.env').touch()
    monkeypatch.setattr(launcher, 'ROOT', tmp_path)
    monkeypatch.setattr(launcher, 'available', Mock())
    monkeypatch.setattr('commerce_hub.bootstrap.s01_v2.erp_config', lambda: SimpleNamespace(access_token='', username='', password=''))
    monkeypatch.setattr('commerce_hub.infrastructure.database.assert_migration_target', Mock())
    db = Mock()
    db.check.return_value = database_ready
    db.schema_ready.return_value = True
    monkeypatch.setattr('commerce_hub.infrastructure.database.Database', lambda _: db)
    monkeypatch.setattr('commerce_hub.governance.access.AccessControl', Mock())
    admin = Mock()
    admin.initialized.return_value = True
    monkeypatch.setattr('commerce_hub.governance.access.local.LocalAdmin', lambda *args: admin)
    settings = SimpleNamespace(auth_issuer='local', auth_audience='local', auth_signing_key=Mock(), local_app_tenant='local')
    config = dict(modelEnabled=False, apiPort=8765, webPort=5173)
    if database_ready:
        launcher.preflight(settings, config)
        assert launcher.available.call_count == 2
    else:
        with pytest.raises(ValueError, match='DATABASE_UNAVAILABLE'):
            launcher.preflight(settings, config)
        launcher.available.assert_not_called()
    assert 'ERP 未配置' in capsys.readouterr().out
    db.close.assert_called_once()
