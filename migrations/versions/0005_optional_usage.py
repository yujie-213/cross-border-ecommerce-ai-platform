"""Provider-neutral token facts with optional charges; preserve every legacy value."""
from alembic import op
import sqlalchemy as sa
from commerce_hub.infrastructure.database import MigrationError

revision = "0005_optional_usage"
down_revision = "0004_reports"
branch_labels = None
depends_on = None


def upgrade():
    # Only nullable relaxations and additive columns. No historical backfill/price inference.
    for name, kind in (("tokens", sa.Integer()), ("cost", sa.Numeric(20, 8)),
                       ("currency", sa.String(8)), ("pricing_version", sa.String(64))):
        op.alter_column("g02_usage_facts", name, existing_type=kind, nullable=True)
    for name in ("input_tokens", "output_tokens", "cached_input_tokens", "uncached_input_tokens"):
        op.add_column("g02_usage_facts", sa.Column(name, sa.Integer(), nullable=True))


def downgrade():
    raise MigrationError("Destructive downgrade requires separate authorization; no usage was removed")
