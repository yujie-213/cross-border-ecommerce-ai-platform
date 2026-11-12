"""O01 immutable engineering reports; additive and forward only."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME
from commerce_hub.infrastructure.database import MigrationError

revision = "0004_reports"
down_revision = "0003_delivery_version"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("o01_reports",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(64), primary_key=True),
        sa.Column("report_id", sa.String(64), nullable=False),
        sa.Column("plan_version", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id", "task_id"], ["o01_tasks.tenant_id", "o01_tasks.task_id"], name="fk_report_task"),
        sa.UniqueConstraint("tenant_id", "report_id", name="uq_report_id"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin")


def downgrade():
    raise MigrationError("Destructive downgrade requires separate authorization; no reports were removed")
