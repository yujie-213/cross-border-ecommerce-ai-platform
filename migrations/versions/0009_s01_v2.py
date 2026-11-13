"""Task-scoped catalog acquisition and per-entity progress."""
from alembic import op
from commerce_hub.data.sync.v2_store import acquisitions
from commerce_hub.scenarios.s01_v2.store import items
from commerce_hub.infrastructure.database import MigrationError

revision='0009_s01_v2'
down_revision='0008_s01_requisition'
branch_labels=None
depends_on=None
def upgrade():
    acquisitions.create(op.get_bind());items.create(op.get_bind())
def downgrade():raise MigrationError('Destructive downgrade requires separate authorization')
