from sqlalchemy import MetaData, Table, Column, String, Integer, Numeric, JSON
from sqlalchemy.dialects.mysql import DATETIME

metadata = MetaData()
audit_events = Table("g02_audit_events", metadata,
    Column("tenant_id", String(64), primary_key=True), Column("event_id", String(64), primary_key=True),
    Column("task_id", String(64)), Column("principal_id", String(64), nullable=False),
    Column("action", String(64), nullable=False), Column("code", String(64), nullable=False),
    Column("occurred_at", DATETIME(fsp=6), nullable=False), Column("trace_id", String(32), nullable=False),
    Column("details", JSON, nullable=False),
    mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin")
usage_facts = Table("g02_usage_facts", metadata,
    Column("tenant_id", String(64), primary_key=True), Column("task_id", String(64), primary_key=True),
    Column("attempt_id", String(64), primary_key=True), Column("usage_ref", String(64), nullable=False),
    Column("tokens", Integer, nullable=False), Column("cost", Numeric(20,8), nullable=False),
    Column("currency", String(8), nullable=False), Column("pricing_version", String(64), nullable=False),
    mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin")
