"""G01-owned tables. Migrations compose this metadata; other modules use AccessControl."""
from sqlalchemy import BigInteger, Boolean, Column, ForeignKeyConstraint, JSON, MetaData, String, Table
from sqlalchemy.dialects.mysql import DATETIME

metadata = MetaData()

principals = Table(
    "g01_principals", metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("principal_id", String(64), primary_key=True),
    Column("active", Boolean, nullable=False),
    Column("revision", BigInteger, nullable=False),
    mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
)

grants = Table(
    "g01_grants", metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("principal_id", String(64), primary_key=True),
    Column("action", String(64), primary_key=True),
    Column("scope", JSON, nullable=False),
    ForeignKeyConstraint(["tenant_id", "principal_id"],
                         ["g01_principals.tenant_id", "g01_principals.principal_id"], name="fk_g01_grant_principal"),
    mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
)

sessions = Table(
    "g01_sessions", metadata,
    Column("tenant_id", String(64), primary_key=True),
    Column("principal_id", String(64), primary_key=True),
    Column("token_id", String(64), primary_key=True),
    Column("active", Boolean, nullable=False),
    Column("expires_at", DATETIME(fsp=6), nullable=False),
    ForeignKeyConstraint(["tenant_id", "principal_id"],
                         ["g01_principals.tenant_id", "g01_principals.principal_id"], name="fk_g01_session_principal"),
    mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
)
