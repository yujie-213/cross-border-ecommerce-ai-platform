"""Compatibility name for the single connection factory; never migrates at startup."""
import pymysql  # Connection-failure injection compatibility for boundary tests.
import logging
from commerce_hub.infrastructure.database import Database


class DatabaseReadiness(Database):
    def check(self):
        available = super().check()
        if not available:
            logging.getLogger("commerce_hub").warning("", extra={"event": "database_unavailable"})
        return available
