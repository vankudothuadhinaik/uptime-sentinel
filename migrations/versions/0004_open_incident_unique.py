"""Allow at most one open incident per monitor."""

import sqlalchemy as sa
from alembic import op

revision = "0004_open_incident_unique"
down_revision = "0003_lease_tokens"
branch_labels = None
depends_on = None


def upgrade():
    # Existing data must be clean before applying this index. Keep the migration
    # fail-closed rather than silently resolving or deleting incident history.
    op.create_index(
        "uq_incidents_one_open_per_monitor",
        "incidents",
        ["monitor_id"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
        sqlite_where=sa.text("resolved_at IS NULL"),
    )


def downgrade():
    op.drop_index("uq_incidents_one_open_per_monitor", table_name="incidents")
