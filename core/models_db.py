"""
core/models_db.py
SQLAlchemy ORM models for persistent storage.

Tables:
  users              — User accounts for JWT authentication (Phase 3)
  refresh_tokens     — JWT refresh token tracking (Phase 3)
  schedule_runs      — One row per optimization run
  job_records        — One row per job in a run
  operation_records  — One row per machine operation in a run
  machine_health     — Sensor telemetry + failure probability per machine (Phase 4)
  maintenance_alerts — Predicted failure alerts with severity + resolution (Phase 4)
"""
import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Float, DateTime, Boolean, ForeignKey, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


# ---------------------------------------------------------------------------
# Authentication models (Phase 3)
# ---------------------------------------------------------------------------

class User(Base):
    """User account for authentication."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )

    # Relationships
    schedule_runs: Mapped[List["ScheduleRun"]] = relationship(
        "ScheduleRun", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Tracks issued refresh tokens for revocation support."""
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


# ---------------------------------------------------------------------------
# Scheduling models
# ---------------------------------------------------------------------------

class ScheduleRun(Base):
    """Top-level record for a single optimization run."""
    __tablename__ = "schedule_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    algorithm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    makespan: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_tardiness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_flow_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    on_time_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chart_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    excel_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Phase 3: User ownership (nullable for backward compat with existing anonymous runs)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    # Phase 3: Rescheduling lineage
    parent_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("schedule_runs.id"), nullable=True
    )
    trigger_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default="initial"
    )  # "initial", "breakdown", "rush_order"

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="schedule_runs")
    parent_run: Mapped[Optional["ScheduleRun"]] = relationship(
        "ScheduleRun", remote_side="ScheduleRun.id", uselist=False
    )
    jobs: Mapped[List["JobRecord"]] = relationship(
        "JobRecord", back_populates="run", cascade="all, delete-orphan"
    )
    operations: Mapped[List["OperationRecord"]] = relationship(
        "OperationRecord", back_populates="run", cascade="all, delete-orphan"
    )


class JobRecord(Base):
    """Per-job summary metrics for a schedule run."""
    __tablename__ = "job_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedule_runs.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completion_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tardiness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    run: Mapped["ScheduleRun"] = relationship("ScheduleRun", back_populates="jobs")


class OperationRecord(Base):
    """Per-operation scheduling data for a schedule run."""
    __tablename__ = "operation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedule_runs.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(50), nullable=False)
    op_index: Mapped[int] = mapped_column(Integer, nullable=False)
    machine_id: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)

    run: Mapped["ScheduleRun"] = relationship("ScheduleRun", back_populates="operations")


# ---------------------------------------------------------------------------
# Phase 4: Predictive Maintenance models
# ---------------------------------------------------------------------------

class MachineHealth(Base):
    """Time-series sensor telemetry and failure probability for a machine."""
    __tablename__ = "machine_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    machine_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now(), index=True
    )
    temperature: Mapped[float] = mapped_column(Float, nullable=False)       # °C
    vibration: Mapped[float] = mapped_column(Float, nullable=False)         # mm/s RMS
    load_pct: Mapped[float] = mapped_column(Float, nullable=False)          # 0-100 %
    failure_probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 0-1
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # raw IF score


class MaintenanceAlert(Base):
    """Predicted maintenance alert generated by the anomaly detector."""
    __tablename__ = "maintenance_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    machine_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, server_default=func.now()
    )
    predicted_failure_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="low")  # low/medium/high/critical
    failure_probability: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
