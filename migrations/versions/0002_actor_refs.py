"""Persist revocable actor references, never a JWT or credential.

Existing rows default to revision0/token empty and cannot execute with valid G01 checks.
"""
from alembic import op
import sqlalchemy as sa

from commerce_hub.infrastructure.database import MigrationError

revision = "0002_actor_refs"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("o01_tasks", sa.Column("principal_revision", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("o01_tasks", sa.Column("token_id", sa.String(64), nullable=False, server_default=""))


def downgrade():
    raise MigrationError("Destructive downgrade requires separate authorization; no columns were removed")
