"""Opt-in real MySQL fixtures. Never clear shared tables or expose credential values."""
import os

import pytest


@pytest.fixture(scope="session")
def mysql_settings():
    if os.environ.get("COMMERCE_RUN_MYSQL_TESTS") != "1":
        pytest.skip("Real MySQL tests require COMMERCE_RUN_MYSQL_TESTS=1")
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import AUTHORIZED_TEST_DATABASE
    settings = load_settings()
    if settings.db_name != AUTHORIZED_TEST_DATABASE:
        pytest.fail("Configured database is outside the authorized isolated test target", pytrace=False)
    return settings


@pytest.fixture(scope="session")
def database(mysql_settings):
    from commerce_hub.infrastructure.database import Database, MigrationError, migrate
    try:
        migrate(mysql_settings)
    except MigrationError:
        pytest.fail("Authorized isolated database migration failed safely", pytrace=False)
    instance = Database(mysql_settings)
    yield instance
    instance.close()
