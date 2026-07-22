"""004_phase5_shifts.py
Alembic migration for Phase 5: Shift Scheduling.

Creates:
  - machine_shifts : Named shift windows per machine

Revision ID: 004
Revises: 003
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "machine_shifts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("machine_id", sa.String(50), nullable=False, index=True),
        sa.Column("shift_name", sa.String(50), nullable=False),
        sa.Column("shift_start", sa.Float(), nullable=False),
        sa.Column("shift_end", sa.Float(), nullable=False),
        sa.Column("cycle_length", sa.Float(), nullable=False, server_default="24.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
    )
    op.create_index("ix_machine_shifts_machine_id", "machine_shifts", ["machine_id"])


def downgrade() -> None:
    op.drop_index("ix_machine_shifts_machine_id", table_name="machine_shifts")
    op.drop_table("machine_shifts")
