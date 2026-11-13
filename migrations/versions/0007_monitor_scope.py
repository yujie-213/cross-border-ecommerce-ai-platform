"""Versioned D02 owned monitoring membership; no ERP database access."""
from alembic import op
from commerce_hub.data.projection.monitor import monitor_scopes
from commerce_hub.infrastructure.database import MigrationError
revision = '0007_monitor_scope'
down_revision = '0006_online_inputs'
branch_labels = None
depends_on = None

def upgrade(): monitor_scopes.create(op.get_bind())
def downgrade(): raise MigrationError('Destructive downgrade requires separate authorization')
