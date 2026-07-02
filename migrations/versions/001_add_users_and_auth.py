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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # ── Create users table ────────────────────────────────────────────────
    if "users" not in tables:
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
    if "refresh_tokens" not in tables:
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
    if "schedule_runs" in tables:
        columns = [c["name"] for c in inspector.get_columns("schedule_runs")]
        if "user_id" not in columns:
            op.add_column(
                "schedule_runs",
                sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            )
        if "parent_run_id" not in columns:
            op.add_column(
                "schedule_runs",
                sa.Column(
                    "parent_run_id",
                    sa.Integer(),
                    sa.ForeignKey("schedule_runs.id"),
                    nullable=True,
                ),
            )
        if "trigger_type" not in columns:
            op.add_column(
                "schedule_runs",
                sa.Column("trigger_type", sa.String(20), nullable=True, server_default="initial"),
            )
    else:
        # Create schedule_runs and its dependent tables if they don't exist
        op.create_table(
            "schedule_runs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("task_id", sa.String(36), nullable=False, unique=True, index=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, default="pending"),
            sa.Column("algorithm", sa.String(20), nullable=True),
            sa.Column("file_name", sa.String(255), nullable=True),
            sa.Column("makespan", sa.Float(), nullable=True),
            sa.Column("total_tardiness", sa.Float(), nullable=True),
            sa.Column("avg_flow_time", sa.Float(), nullable=True),
            sa.Column("on_time_percent", sa.Float(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("chart_url", sa.String(255), nullable=True),
            sa.Column("excel_url", sa.String(255), nullable=True),
            sa.Column("result_json", sa.Text(), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("parent_run_id", sa.Integer(), sa.ForeignKey("schedule_runs.id"), nullable=True),
            sa.Column("trigger_type", sa.String(20), nullable=True, server_default="initial"),
        )
        op.create_table(
            "job_records",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.Integer(), sa.ForeignKey("schedule_runs.id"), nullable=False),
            sa.Column("job_id", sa.String(50), nullable=False),
            sa.Column("due_date", sa.Float(), nullable=True),
            sa.Column("completion_time", sa.Float(), nullable=True),
            sa.Column("tardiness", sa.Float(), nullable=True),
        )
        op.create_table(
            "operation_records",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.Integer(), sa.ForeignKey("schedule_runs.id"), nullable=False),
            sa.Column("job_id", sa.String(50), nullable=False),
            sa.Column("op_index", sa.Integer(), nullable=False),
            sa.Column("machine_id", sa.String(50), nullable=False),
            sa.Column("start_time", sa.Float(), nullable=False),
            sa.Column("end_time", sa.Float(), nullable=False),
        )

    # ── Seed default admin user ───────────────────────────────────────────
    # Password: admin123 (bcrypt hash)
    admin_exists = False
    if "users" in tables:
        result = conn.execute(sa.text("SELECT 1 FROM users WHERE username = 'admin'")).first()
        if result:
            admin_exists = True

    if not admin_exists:
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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "schedule_runs" in tables:
        columns = [c["name"] for c in inspector.get_columns("schedule_runs")]
        if "trigger_type" in columns:
            op.drop_column("schedule_runs", "trigger_type")
        if "parent_run_id" in columns:
            op.drop_column("schedule_runs", "parent_run_id")
        if "user_id" in columns:
            op.drop_column("schedule_runs", "user_id")

    if "refresh_tokens" in tables:
        op.drop_table("refresh_tokens")
    if "users" in tables:
        op.drop_table("users")

