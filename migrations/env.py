"""Online migrations only, guarded to the explicitly authorized isolated database."""
from alembic import context
from sqlalchemy import text

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.infrastructure.database import (
    AUTHORIZED_TEST_DATABASE, Database, MigrationError, assert_migration_target,
)


def run(connection):
    if connection.execute(text("SELECT DATABASE()")).scalar_one() != AUTHORIZED_TEST_DATABASE:
        raise MigrationError("Migration target is outside the authorized test database")
    connection.commit()
    lock_name = "commerce_hub:migration:" + AUTHORIZED_TEST_DATABASE
    acquired = connection.execute(text("SELECT GET_LOCK(:name, 10)"), {"name": lock_name}).scalar_one()
    connection.commit()
    if acquired != 1:
        raise MigrationError("Migration lock unavailable")
    try:
        context.configure(connection=connection, target_metadata=None, transactional_ddl=False)
        with context.begin_transaction():
            context.run_migrations()
        connection.commit()
    finally:
        if connection.in_transaction():
            connection.rollback()
        connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name})
        connection.commit()


if context.is_offline_mode():
    raise MigrationError("Offline migration is not supported by the guarded test environment")

provided = context.config.attributes.get("connection")
if provided is not None:
    run(provided)
else:
    settings = load_settings()
    assert_migration_target(settings)
    database = Database(settings)
    try:
        with database.engine.connect() as connection:
            run(connection)
    finally:
        database.close()
