"""Versioned aggregates: logical child records remain within their immutable version.

Ownership, CAS, command uniqueness and asset references have SQL constraints. No
other scenario imports these tables; S01 consumes only the public risk port.
"""
from sqlalchemy import Column, ForeignKeyConstraint, Index, Integer, JSON, MetaData, String, Table
from sqlalchemy.dialects.mysql import DATETIME

metadata = MetaData()
OPTIONS = dict(mysql_engine='InnoDB', mysql_charset='utf8mb4', mysql_collate='utf8mb4_bin')
assets = Table('b_assets', metadata,
    Column('tenant_id', String(64), primary_key=True),
    Column('kind', String(24), primary_key=True), Column('id', String(64), primary_key=True),
    Column('workspace', String(64), nullable=False), Column('scope', JSON, nullable=False),
    Column('revision', Integer, nullable=False), Column('state', String(32), nullable=False),
    Column('body', JSON, nullable=False), Column('created_by', String(64), nullable=False),
    Column('created_at', DATETIME(fsp=6), nullable=False), Column('updated_at', DATETIME(fsp=6), nullable=False), **OPTIONS)
Index('ix_b_workspace_kind_state', assets.c.tenant_id, assets.c.workspace, assets.c.kind, assets.c.state)
versions = Table('b_asset_versions', metadata,
    Column('tenant_id', String(64), primary_key=True), Column('kind', String(24), primary_key=True),
    Column('id', String(64), primary_key=True), Column('version', Integer, primary_key=True),
    Column('body', JSON, nullable=False), Column('content_hash', String(64), nullable=False),
    Column('actor', String(64), nullable=False), Column('created_at', DATETIME(fsp=6), nullable=False),
    ForeignKeyConstraint(['tenant_id', 'kind', 'id'], ['b_assets.tenant_id', 'b_assets.kind', 'b_assets.id'], name='fk_b_version_asset'), **OPTIONS)
commands = Table('b_commands', metadata,
    Column('tenant_id', String(64), primary_key=True), Column('actor', String(64), primary_key=True),
    Column('command_key', String(128), primary_key=True), Column('fingerprint', String(64), nullable=False),
    Column('result', JSON, nullable=False), **OPTIONS)
chunks = Table('b_import_chunks', metadata,
    Column('tenant_id', String(64), primary_key=True), Column('dataset_id', String(64), primary_key=True),
    Column('chunk_no', Integer, primary_key=True), Column('content_hash', String(64), nullable=False),
    Column('records', JSON, nullable=False), **OPTIONS)
manifests = Table('d03_b_manifests', metadata,
    Column('tenant_id', String(64), primary_key=True), Column('snapshot_id', String(64), primary_key=True),
    Column('scope', JSON, nullable=False), Column('body', JSON, nullable=False),
    Column('content_hash', String(64), nullable=False), **OPTIONS)
steps = Table('b_step_results', metadata,
    Column('tenant_id', String(64), primary_key=True), Column('task_id', String(64), primary_key=True),
    Column('step', String(32), primary_key=True), Column('input_hash', String(64), nullable=False),
    Column('result', JSON, nullable=False), **OPTIONS)
