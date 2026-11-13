"""D03 manifest store for V2 acquisition identity."""
from alembic import op
from commerce_hub.data.quality.v2_store import manifests
from commerce_hub.infrastructure.database import MigrationError
revision='0010_s01_v2_manifests'
down_revision='0009_s01_v2'
branch_labels=None
depends_on=None
def upgrade():manifests.create(op.get_bind())
def downgrade():raise MigrationError('Destructive downgrade requires separate authorization')
