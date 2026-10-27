"""add fenced lease ownership tokens"""

import sqlalchemy as sa
from alembic import op

revision = "0003_lease_tokens"
down_revision = "0002_scheduler_leases"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("monitors", sa.Column("lease_token", sa.String(length=64), nullable=True))
    op.create_index("ix_monitors_lease_token", "monitors", ["lease_token"])


def downgrade():
    op.drop_index("ix_monitors_lease_token", table_name="monitors")
    op.drop_column("monitors", "lease_token")
