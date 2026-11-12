"""Bind durable delivery references to their owner version; additive, no data removal."""
from alembic import op
import sqlalchemy as sa
from commerce_hub.infrastructure.database import MigrationError

revision = "0003_delivery_version"
down_revision = "0002_actor_refs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("i01_work_items", sa.Column("owner_version", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    raise MigrationError("Destructive downgrade requires separate authorization; no columns were removed")
