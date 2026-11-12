"""Real isolated MySQL storage tests. None of these tests uses SQLite."""
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from commerce_hub.infrastructure.database import (
    Database, MigrationError, REQUIRED_TABLES, SCHEMA_REVISION, migrate, migration_config,
)

pytestmark = pytest.mark.mysql


def test_explicit_migration_head_and_repeat_upgrade(database, mysql_settings):
    assert database.schema_ready()
    assert migrate(mysql_settings) == SCHEMA_REVISION
    assert database.schema_ready()
    with database.engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all() == [SCHEMA_REVISION]
        assert REQUIRED_TABLES <= set(inspect(connection).get_table_names())
        count = connection.execute(text("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                                         "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME <> 'alembic_version' "
                                         "AND (ENGINE <> 'InnoDB' OR TABLE_COLLATION <> 'utf8mb4_bin')")).scalar_one()
        assert count == 0


def test_one_frozen_migration_chain():
    script = ScriptDirectory.from_config(migration_config())
    assert script.get_heads() == [SCHEMA_REVISION]
    assert [revision.revision for revision in script.walk_revisions()] == [SCHEMA_REVISION, "0003_delivery_version", "0002_actor_refs", "0001_foundation"]
    source = Path(script.get_revision("0001_foundation").path).read_text(encoding="utf-8")
    assert "from commerce_hub.orchestration.tables" not in source
    assert "metadata.create_all" not in source


def test_other_database_target_is_refused_before_connection(mysql_settings, monkeypatch):
    calls = []
    monkeypatch.setattr("commerce_hub.infrastructure.database.pymysql.connect", lambda **_: calls.append(True))
    denied = mysql_settings.model_copy(update={"db_name": "not_authorized_fixture"})
    with pytest.raises(MigrationError, match="outside the authorized"):
        migrate(denied)
    assert calls == []


def test_engine_construction_never_connects_or_migrates(mysql_settings, monkeypatch):
    calls = []
    monkeypatch.setattr("commerce_hub.infrastructure.database.pymysql.connect", lambda **_: calls.append(True))
    instance = Database(mysql_settings)
    instance.close()
    assert calls == []


def test_destructive_downgrade_guard_does_not_execute_sql(database):
    # Import the frozen revision to exercise refusal without asking Alembic to run DROP.
    revision = ScriptDirectory.from_config(migration_config()).get_revision(SCHEMA_REVISION).module
    with pytest.raises(MigrationError, match="requires separate authorization"):
        revision.downgrade()
    assert database.schema_ready()


def test_actual_server_is_mysql_utc_read_committed(database):
    with database.engine.connect() as connection:
        version = connection.execute(text("SELECT VERSION()")).scalar_one()
        assert version.startswith("8.") or version.startswith("9.")
        assert "maria" not in version.lower()
        assert connection.execute(text("SELECT @@session.time_zone")).scalar_one() == "+00:00"
        assert connection.execute(text("SELECT @@session.transaction_isolation")).scalar_one() == "READ-COMMITTED"


def test_exact_types_unique_tenant_key_and_real_rollback(database):
    # Temporary table belongs only to this test connection. No preexisting table is touched.
    name = "_a03_owned_" + uuid4().hex
    created = False
    with database.engine.connect() as connection:
        try:
            connection.execute(text(f"CREATE TEMPORARY TABLE `{name}` (tenant VARCHAR(64) NOT NULL, id BIGINT NOT NULL, "
                                    "quantity DECIMAL(30,8) NOT NULL, utc_at DATETIME(6) NOT NULL, "
                                    "PRIMARY KEY(tenant,id)) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_bin"))
            created = True
            connection.commit()
            quantity = Decimal("12345678901234567890.12345678")
            instant = datetime(2026, 11, 12, 4, 5, 6, 123456)
            insert = text(f"INSERT INTO `{name}` (tenant,id,quantity,utc_at) VALUES (:tenant,:id,:quantity,:at)")
            with connection.begin():
                connection.execute(insert, {"tenant": "fixture-a", "id": 1, "quantity": quantity, "at": instant})
                connection.execute(insert, {"tenant": "fixture-b", "id": 1, "quantity": quantity, "at": instant})
            values = connection.execute(text(f"SELECT quantity,utc_at FROM `{name}` ORDER BY tenant")).all()
            assert values == [(quantity, instant), (quantity, instant)]
            connection.rollback()
            with pytest.raises(IntegrityError):
                with connection.begin():
                    connection.execute(insert, {"tenant": "fixture-a", "id": 1, "quantity": quantity, "at": instant})
            with pytest.raises(RuntimeError, match="fixture rollback"):
                with connection.begin():
                    connection.execute(insert, {"tenant": "fixture-a", "id": 2, "quantity": quantity, "at": instant})
                    raise RuntimeError("fixture rollback")
            assert connection.execute(text(f"SELECT COUNT(*) FROM `{name}` WHERE id=2")).scalar_one() == 0
        finally:
            connection.rollback()
            if created:
                connection.execute(text(f"DROP TEMPORARY TABLE `{name}`"))
                connection.commit()
