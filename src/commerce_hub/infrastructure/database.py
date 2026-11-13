"""Explicit MySQL connection/migration boundary; startup never migrates."""
from __future__ import annotations

from pathlib import Path

import pymysql
from sqlalchemy import create_engine, event, inspect, text

from commerce_hub.bootstrap.settings import Settings

SCHEMA_REVISION = "0006_online_inputs"
AUTHORIZED_TEST_DATABASE = "s01_a01_test_20261112"
ROOT = Path(__file__).resolve().parents[3]
REQUIRED_TABLES = frozenset({
    "g01_principals", "g01_grants", "g01_sessions", "g02_audit_events", "g02_usage_facts",
    "o01_tasks", "o01_commands", "o01_budgets", "o01_budget_attempts", "i01_work_items", "o01_reports",
    "d01_online_acquisitions", "d03_online_snapshots",
})


class MigrationError(RuntimeError):
    """Safe migration failure without credentials, statements or driver messages."""


def assert_migration_target(settings: Settings) -> None:
    if settings.db_name != AUTHORIZED_TEST_DATABASE:
        raise MigrationError("Migration target is outside the authorized test database")


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_engine(
            "mysql+pymysql://", creator=lambda: pymysql.connect(**settings.connection_kwargs()),
            isolation_level="READ COMMITTED", hide_parameters=True, pool_pre_ping=True,
            pool_size=6, max_overflow=4, pool_timeout=5, pool_recycle=300,
        )

        @event.listens_for(self.engine, "connect")
        def set_session(connection, _):
            with connection.cursor() as cursor:
                cursor.execute("SET SESSION time_zone = '+00:00'")

    def check(self) -> bool:
        try:
            with self.engine.connect() as connection:
                return connection.execute(text("SELECT 1")).scalar_one() == 1
        except Exception:
            return False

    def schema_ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                versions = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
                schema = inspect(connection)
                if versions != [SCHEMA_REVISION] or not REQUIRED_TABLES <= set(schema.get_table_names()):
                    return False
                return ({"principal_revision", "token_id"} <= {column["name"] for column in schema.get_columns("o01_tasks")}
                        and "owner_version" in {column["name"] for column in schema.get_columns("i01_work_items")}
                        and {"input_tokens", "output_tokens", "cached_input_tokens", "uncached_input_tokens"}
                        <= {column["name"] for column in schema.get_columns("g02_usage_facts")})
        except Exception:
            return False

    def close(self) -> None:
        self.engine.dispose()


def migration_config(connection=None):
    from alembic.config import Config
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def migrate(settings: Settings) -> str:
    """Explicit, forward-only upgrade of the currently authorized isolated database."""
    from alembic import command
    assert_migration_target(settings)
    database = Database(settings)
    try:
        with database.engine.connect() as connection:
            config = migration_config(connection)
            command.upgrade(config, "head")
        if not database.schema_ready():
            raise MigrationError("Migration head verification failed")
        return SCHEMA_REVISION
    except MigrationError:
        raise
    except Exception:
        raise MigrationError("Migration failed; inspect authorized schema with a database administrator") from None
    finally:
        database.close()


if __name__ == "__main__":
    from commerce_hub.bootstrap.settings import ConfigurationError, load_settings
    try:
        revision = migrate(load_settings())
        print("Migration complete: " + revision)
    except (MigrationError, ConfigurationError):
        print("Migration failed safely; no credentials or driver details logged")
        raise SystemExit(1)
