"""initial schema"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_table(
        "monitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("is_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_monitors_owner_id", "monitors", ["owner_id"])
    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "monitor_id",
            sa.Integer(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_up", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("error_category", sa.String(40)),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_check_results_monitor_id", "check_results", ["monitor_id"])
    op.create_index("ix_check_results_checked_at", "check_results", ["checked_at"])
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "monitor_id",
            sa.Integer(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_incidents_monitor_id", "incidents", ["monitor_id"])


def downgrade():
    op.drop_table("incidents")
    op.drop_table("check_results")
    op.drop_table("monitors")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
