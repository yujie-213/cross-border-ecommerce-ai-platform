"""B versioned domain assets, import chunks and D03 manifests, no S01 backfill."""
from alembic import op
from commerce_hub.scenarios.after_sales.tables import metadata
from commerce_hub.infrastructure.database import MigrationError

revision = '0013_b_workflows'
down_revision = '0012_b_resource_grants'
branch_labels = depends_on = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    raise MigrationError('Destructive downgrade requires separate authorization')
