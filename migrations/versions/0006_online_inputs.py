"""Only new D01 acquisition and D03 immutable assets; existing rows are untouched."""
from alembic import op
from commerce_hub.data.sync.online_store import acquisitions
from commerce_hub.data.quality.online_store import snapshots
from commerce_hub.infrastructure.database import MigrationError

revision = '0006_online_inputs'
down_revision = '0005_optional_usage'
branch_labels = None
depends_on = None

def upgrade():
    for table in (acquisitions, snapshots):
        table.create(op.get_bind())

def downgrade():
    raise MigrationError('Destructive downgrade requires separate authorization')
