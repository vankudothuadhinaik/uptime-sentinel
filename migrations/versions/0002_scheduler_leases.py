"""add due timestamps and worker leases"""

import sqlalchemy as sa
from alembic import op

revision = "0002_scheduler_leases"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("monitors", sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("monitors", sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_monitors_next_check_at", "monitors", ["next_check_at"])
    op.create_index("ix_monitors_lease_until", "monitors", ["lease_until"])


def downgrade():
    op.drop_index("ix_monitors_lease_until", table_name="monitors")
    op.drop_index("ix_monitors_next_check_at", table_name="monitors")
    op.drop_column("monitors", "lease_until")
    op.drop_column("monitors", "next_check_at")
