"""003_phase4_machine_health_and_alerts.py
Alembic migration for Phase 4: Predictive Maintenance tables.

Creates:
  - machine_health     : Sensor telemetry time-series per machine
  - maintenance_alerts : Predicted failure alerts

Revision ID: 003
Revises: 002
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── machine_health ──────────────────────────────────────────────────────
    op.create_table(
        "machine_health",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("machine_id", sa.String(50), nullable=False, index=True),
        sa.Column(
            "timestamp",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("vibration", sa.Float(), nullable=False),
        sa.Column("load_pct", sa.Float(), nullable=False),
        sa.Column("failure_probability", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
    )
    op.create_index("ix_machine_health_machine_id", "machine_health", ["machine_id"])
    op.create_index("ix_machine_health_timestamp", "machine_health", ["timestamp"])

    # ── maintenance_alerts ──────────────────────────────────────────────────
    op.create_table(
        "maintenance_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("machine_id", sa.String(50), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column("predicted_failure_at", sa.DateTime(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="low"),
        sa.Column("failure_probability", sa.Float(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_maintenance_alerts_machine_id", "maintenance_alerts", ["machine_id"])


def downgrade() -> None:
    op.drop_index("ix_maintenance_alerts_machine_id", table_name="maintenance_alerts")
    op.drop_table("maintenance_alerts")

    op.drop_index("ix_machine_health_timestamp", table_name="machine_health")
    op.drop_index("ix_machine_health_machine_id", table_name="machine_health")
    op.drop_table("machine_health")
