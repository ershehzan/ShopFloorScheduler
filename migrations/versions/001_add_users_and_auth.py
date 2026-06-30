"""Phase 3: Add users, refresh_tokens, and extend schedule_runs

Revision ID: 001
Revises: None (initial migration)
Create Date: 2026-06-30

Creates:
  - users table (JWT authentication)
  - refresh_tokens table (token revocation tracking)
  - Adds user_id, parent_run_id, trigger_type columns to schedule_runs
  - Seeds default admin user (admin@shopfloor.local / admin123)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create users table ────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    # ── Create refresh_tokens table ───────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("token", sa.String(500), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    # ── Extend schedule_runs ──────────────────────────────────────────────
    # Add user ownership (nullable for existing anonymous runs)
    op.add_column(
        "schedule_runs",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    # Add rescheduling lineage
    op.add_column(
        "schedule_runs",
        sa.Column(
            "parent_run_id",
            sa.Integer(),
            sa.ForeignKey("schedule_runs.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "schedule_runs",
        sa.Column("trigger_type", sa.String(20), nullable=True, server_default="initial"),
    )

    # ── Seed default admin user ───────────────────────────────────────────
    # Password: admin123 (bcrypt hash)
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd.hash("admin123")

    op.execute(
        sa.text(
            "INSERT INTO users (email, username, hashed_password, is_active, is_admin) "
            "VALUES (:email, :username, :hashed_password, :is_active, :is_admin)"
        ).bindparams(
            email="admin@shopfloor.local",
            username="admin",
            hashed_password=hashed,
            is_active=True,
            is_admin=True,
        )
    )


def downgrade() -> None:
    op.drop_column("schedule_runs", "trigger_type")
    op.drop_column("schedule_runs", "parent_run_id")
    op.drop_column("schedule_runs", "user_id")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
