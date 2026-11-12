from sqlalchemy import MetaData, Table, Column, String, Integer, Index
from sqlalchemy.dialects.mysql import DATETIME

metadata = MetaData()
work_items = Table("i01_work_items", metadata,
    Column("tenant_id", String(64), primary_key=True), Column("work_id", String(64), primary_key=True),
    Column("owner_id", String(64), nullable=False), Column("kind", String(64), nullable=False),
    Column("owner_version", Integer, nullable=False, default=1),
    Column("state", String(24), nullable=False), Column("run_after", DATETIME(fsp=6), nullable=False),
    Column("attempt", Integer, nullable=False), Column("max_attempts", Integer, nullable=False),
    Column("lease_token", String(64)), Column("lease_expires", DATETIME(fsp=6)),
    Index("ix_i01_claim", "state", "run_after", "kind"), Index("ix_i01_expiry", "state", "lease_expires"),
    mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin")
