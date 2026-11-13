"""S01 durable human-confirmed teaching requisition operation."""
from alembic import op
from commerce_hub.scenarios.s01_backend.requisition_store import requisitions
from commerce_hub.infrastructure.database import MigrationError

revision = '0008_s01_requisition'
down_revision = '0007_monitor_scope'
branch_labels = None
depends_on = None


def upgrade():
    requisitions.create(op.get_bind())


def downgrade():
    raise MigrationError('Destructive downgrade requires separate authorization')
