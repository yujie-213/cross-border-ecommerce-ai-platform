from sqlalchemy import (MetaData, Table, Column, String, Integer, BigInteger, JSON, Numeric,
                        UniqueConstraint, ForeignKeyConstraint)
from sqlalchemy.dialects.mysql import DATETIME

metadata = MetaData()
options = dict(mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin")
tasks = Table("o01_tasks", metadata,
    Column("tenant_id", String(64), primary_key=True), Column("task_id", String(64), primary_key=True),
    Column("principal_id", String(64), nullable=False), Column("principal_revision", Integer, nullable=False, default=0),
    Column("token_id", String(64), nullable=False, default=""), Column("command_key", String(128), nullable=False),
    Column("fingerprint", String(64), nullable=False), Column("scenario_id", String(64), nullable=False),
    Column("scenario_version", String(32), nullable=False), Column("plan_version", Integer, nullable=False),
    Column("scope", JSON, nullable=False), Column("parameters", JSON, nullable=False),
    Column("state", String(24), nullable=False), Column("revision", Integer, nullable=False),
    Column("work_id", String(64), nullable=False), Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("deadline", DATETIME(fsp=6), nullable=False), Column("error_code", String(64)),
    UniqueConstraint("tenant_id", "principal_id", "command_key", name="uq_o01_task_command"), **options)
commands = Table("o01_commands", metadata,
    Column("tenant_id", String(64), primary_key=True), Column("principal_id", String(64), primary_key=True),
    Column("command_key", String(128), primary_key=True), Column("fingerprint", String(64), nullable=False),
    Column("task_id", String(64), nullable=False), Column("revision", Integer, nullable=False), **options)
budgets = Table("o01_budgets", metadata,
    Column("tenant_id", String(64), primary_key=True), Column("task_id", String(64), primary_key=True),
    Column("policy_version", String(64), nullable=False), Column("max_calls", Integer, nullable=False),
    Column("max_tokens", BigInteger, nullable=False), Column("max_cost", Numeric(20,8), nullable=False),
    Column("used_calls", Integer, nullable=False, default=0), Column("used_tokens", BigInteger, nullable=False, default=0),
    Column("used_cost", Numeric(20,8), nullable=False, default=0), Column("reserved_calls", Integer, nullable=False, default=0),
    Column("reserved_tokens", BigInteger, nullable=False, default=0), Column("reserved_cost", Numeric(20,8), nullable=False, default=0),
    ForeignKeyConstraint(["tenant_id", "task_id"], ["o01_tasks.tenant_id", "o01_tasks.task_id"], name="fk_budget_task"), **options)
attempts = Table("o01_budget_attempts", metadata,
    Column("tenant_id", String(64), primary_key=True), Column("task_id", String(64), primary_key=True),
    Column("attempt_id", String(64), primary_key=True), Column("logical_call_id", String(64), nullable=False),
    Column("state", String(24), nullable=False), Column("max_tokens", BigInteger, nullable=False),
    Column("max_cost", Numeric(20,8), nullable=False), Column("actual_tokens", BigInteger),
    Column("actual_cost", Numeric(20,8)), Column("usage_ref", String(64)),
    ForeignKeyConstraint(["tenant_id", "task_id"], ["o01_budgets.tenant_id", "o01_budgets.task_id"], name="fk_attempt_budget"), **options)
