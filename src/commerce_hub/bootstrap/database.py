"""A-02 readiness connection only. No repositories, migrations, tables or worker."""
import logging

import pymysql
from sqlalchemy import create_engine, event, text

from commerce_hub.bootstrap.settings import Settings


class DatabaseReadiness:
    def __init__(self, settings: Settings):
        # A credential-free URL prevents an exception from rendering a connection URL.
        self.engine = create_engine("mysql+pymysql://", creator=lambda: pymysql.connect(**settings.connection_kwargs()),
                                    isolation_level="READ COMMITTED", hide_parameters=True, pool_pre_ping=True,
                                    pool_size=2, max_overflow=0, pool_timeout=5, pool_recycle=300)

        @event.listens_for(self.engine, "connect")
        def set_timezone(connection, _):
            with connection.cursor() as cursor:
                cursor.execute("SET SESSION time_zone = '+00:00'")

    def check(self) -> bool:
        try:
            with self.engine.connect() as connection:
                return connection.execute(text("SELECT 1")).scalar_one() == 1
        except Exception:
            # No exception, URL, SQL parameters, credentials or server message reaches logs/API.
            logging.getLogger("commerce_hub").warning("", extra={"event": "database_unavailable"})
            return False

    def close(self) -> None:
        self.engine.dispose()
