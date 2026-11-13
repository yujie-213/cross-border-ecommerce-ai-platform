"""One local administrator credential per configured local deployment tenant."""
from alembic import op
from commerce_hub.governance.access.local import admins
from commerce_hub.infrastructure.database import MigrationError
revision='0011_local_admin'
down_revision='0010_s01_v2_manifests'
branch_labels=None
depends_on=None
def upgrade():admins.create(op.get_bind())
def downgrade():raise MigrationError('Destructive downgrade requires separate authorization')
