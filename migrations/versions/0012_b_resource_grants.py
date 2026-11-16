"""Add B-only grants without changing existing accounts or S01 grants."""
from alembic import op
from commerce_hub.governance.access.tables import b_resource_grants
from commerce_hub.infrastructure.database import MigrationError

revision = '0012_b_resource_grants'
down_revision = '0011_local_admin'
branch_labels = None
depends_on = None


def upgrade():
    b_resource_grants.create(op.get_bind())


def downgrade():
    raise MigrationError('Destructive downgrade requires separate authorization')
