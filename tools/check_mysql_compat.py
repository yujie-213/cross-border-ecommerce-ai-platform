"""Authorized A-01 MySQL probe. Never prints configuration, exceptions, or credentials."""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

from dotenv import dotenv_values
import pymysql
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
DATABASE = "s01_a01_test_20261112"


def run() -> tuple[dict, int]:
    # Even driver/SQLAlchemy diagnostics must not accidentally stringify connection arguments.
    logging.disable(logging.CRITICAL)
    result = {"scope": "REAL_MYSQL_ISOLATED_ENGINEERING_COMPATIBILITY", "database": DATABASE,
              "checks": [], "status": "FAIL", "stage": "configuration", "cleanup": "NOT_RUN",
              "erpCalls": 0, "modelCalls": 0, "otherDatabasesModified": False}
    engine = None
    table = "_a01_compat_" + uuid4().hex
    created_table = False
    connection = None
    args = {}

    def record(name, passed, detail=None):
        result["checks"].append({"check": name, "result": "PASS" if passed else "FAIL", "detail": detail})
        if not passed:
            raise AssertionError("COMPATIBILITY_ASSERTION_FAILED")

    try:
        values = dotenv_values(ROOT / ".env", interpolate=False)
        def config(name, default=None):
            return os.environ.get("S01_TEST_DB_" + name, values.get("S01_TEST_DB_" + name, default))

        if config("NAME") != DATABASE:
            result["errorCode"] = "AUTHORIZED_TEST_DATABASE_MISMATCH"
            return result, 1
        if not all(config(k) for k in ["HOST", "USER", "PASSWORD"]):
            result["errorCode"] = "MISSING_AUTHORIZED_CONNECTION"
            return result, 1
        args = dict(host=config("HOST"), port=int(config("PORT", "3306")), user=config("USER"),
                    password=config("PASSWORD"), connect_timeout=int(config("CONNECT_TIMEOUT_SECONDS", "5")),
                    read_timeout=5, write_timeout=5, charset="utf8mb4", autocommit=True)
        ca = config("SSL_CA")
        if ca:
            args.update(ssl_ca=ca, ssl_verify_cert=True, ssl_verify_identity=True)
        elif args["host"] not in ["localhost", "127.0.0.1", "::1"]:
            result["errorCode"] = "REMOTE_DATABASE_REQUIRES_TRUSTED_CA"
            return result, 1
        result["stage"] = "authorized_connection"
        connection = pymysql.connect(**args)
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            result["serverVersion"] = version if re.fullmatch(r"[0-9A-Za-z.+_-]{1,80}", version) else "UNRECOGNIZED"
            record("real_authorized_connection", True)
            result["stage"] = "server_version"
            record("mysql_version_supports_required_locking", bool(re.match(r"^(8|9)\.", version)) and "maria" not in version.lower())
            cursor.execute("SELECT SUPPORT FROM INFORMATION_SCHEMA.ENGINES WHERE ENGINE='InnoDB'")
            record("innodb_supported", cursor.fetchone()[0] in ["YES", "DEFAULT"])
            result["stage"] = "create_authorized_test_database"
            cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=%s", (DATABASE,))
            existed = cursor.fetchone() is not None
            if not existed:
                cursor.execute(f"CREATE DATABASE `{DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_bin")
            result["databaseCreatedThisRun"] = not existed
        connection.close()
        connection = None
        result["stage"] = "sqlalchemy_driver_connection"
        db_args = dict(args, database=DATABASE, autocommit=False)
        engine = create_engine("mysql+pymysql://", creator=lambda: pymysql.connect(**db_args),
                               isolation_level="READ COMMITTED", hide_parameters=True, pool_pre_ping=True)

        @event.listens_for(engine, "connect")
        def set_session(dbapi_connection, _):
            with dbapi_connection.cursor() as cursor:
                cursor.execute("SET SESSION time_zone = '+00:00'")

        with engine.connect() as conn:
            record("driver_and_selected_database", conn.execute(text("SELECT DATABASE()")).scalar_one() == DATABASE)
            record("session_utc", conn.execute(text("SELECT @@session.time_zone")).scalar_one() == "+00:00")
            record("read_committed", conn.execute(text("SELECT @@session.transaction_isolation")).scalar_one() == "READ-COMMITTED")
        result["stage"] = "owned_fixture_table"
        with engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE `{table}` (tenant_id VARCHAR(64) NOT NULL, id BIGINT NOT NULL, "
                              "qty DECIMAL(30,8) NOT NULL, utc_at DATETIME(6) NOT NULL, label VARCHAR(64) NOT NULL, "
                              "lease BIGINT NOT NULL DEFAULT 1, PRIMARY KEY(tenant_id,id)) "
                              "ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_bin"))
        created_table = True
        quantity = Decimal("12345678901234567890.12345678")
        instant = datetime(2026, 11, 12, 2, 30, 45, 123456)
        insert = text(f"INSERT INTO `{table}` (tenant_id,id,qty,utc_at,label) VALUES (:tenant,:id,:qty,:at,:label)")
        row = dict(tenant="tenant-fixture-a", id=1, qty=quantity, at=instant, label="补货🧪")
        with engine.begin() as conn:
            conn.execute(insert, row)
            conn.execute(insert, dict(row, id=2))
            conn.execute(insert, dict(row, tenant="tenant-fixture-b"))
        with engine.connect() as conn:
            value = conn.execute(text(f"SELECT qty,utc_at,label FROM `{table}` WHERE tenant_id=:tenant AND id=1"), row).one()
            record("decimal_exact_roundtrip", isinstance(value[0], Decimal) and value[0] == quantity)
            record("utc_microseconds_roundtrip", value[1] == instant)
            record("utf8mb4_roundtrip", value[2] == "补货🧪")
            record("tenant_composite_key", conn.execute(text(f"SELECT COUNT(*) FROM `{table}` WHERE id=1")).scalar_one() == 2)
        result["stage"] = "unique_constraint"
        try:
            with engine.begin() as conn:
                conn.execute(insert, row)
        except IntegrityError as exc:
            record("unique_constraint", exc.orig.args[0] == 1062)
        else:
            record("unique_constraint", False)
        result["stage"] = "transaction_rollback"
        class FixtureRollback(Exception):
            pass
        try:
            with engine.begin() as conn:
                conn.execute(insert, dict(row, id=3))
                raise FixtureRollback()
        except FixtureRollback:
            pass
        with engine.connect() as conn:
            record("short_transaction_rollback", conn.execute(text(f"SELECT COUNT(*) FROM `{table}` WHERE id=3")).scalar_one() == 0)
        result["stage"] = "two_connection_skip_locked"
        with engine.connect() as first, engine.connect() as second:
            with first.begin(), second.begin():
                first.execute(text(f"SELECT id FROM `{table}` WHERE tenant_id='tenant-fixture-a' AND id=1 FOR UPDATE")).all()
                available = second.execute(text(f"SELECT id FROM `{table}` WHERE tenant_id='tenant-fixture-a' ORDER BY id FOR UPDATE SKIP LOCKED")).scalars().all()
                record("two_connection_skip_locked", available == [2])
        result["stage"] = "conditional_update"
        with engine.begin() as conn:
            update = text(f"UPDATE `{table}` SET lease=lease+1 WHERE tenant_id='tenant-fixture-a' AND id=1 AND lease=:lease")
            record("current_fence_updates", conn.execute(update, {"lease": 1}).rowcount == 1)
            record("stale_fence_rejected", conn.execute(update, {"lease": 1}).rowcount == 0)
        result["versions"] = {p: importlib.metadata.version(p) for p in ["SQLAlchemy", "PyMySQL", "alembic", "cryptography"]}
        result["python"] = sys.version.split()[0]
        result["stage"] = "complete"
        result["status"] = "PASS"
    except Exception as exc:
        # Only an integer DB error number is allowed out; str/repr/traceback can contain credentials.
        original = getattr(exc, "orig", exc)
        error_number = original.args[0] if original.args and isinstance(original.args[0], int) else None
        result["errorCode"] = "AUTH_OR_PRIVILEGE_DENIED" if error_number in [1044, 1045, 1142, 1227] else "COMPATIBILITY_CHECK_FAILED"
        result["mysqlErrorNumber"] = error_number
    finally:
        if connection is not None:
            connection.close()
        if engine is not None:
            if created_table:
                try:
                    # Only the randomly named table created by this invocation is removed.
                    with engine.begin() as conn:
                        conn.execute(text(f"DROP TABLE `{table}`"))
                    result["cleanup"] = "OWNED_FIXTURE_TABLE_REMOVED"
                except Exception:
                    result["cleanup"] = "FAIL_OWNED_FIXTURE_REMAINS"
                    result["status"] = "FAIL"
            engine.dispose()
    return result, 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parsed = parser.parse_args()
    report, code = run()
    safe_json = json.dumps(report, ensure_ascii=False, indent=2)
    if parsed.output:
        parsed.output.parent.mkdir(parents=True, exist_ok=True)
        parsed.output.write_text(safe_json + "\n", encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(safe_json)
    raise SystemExit(code)
