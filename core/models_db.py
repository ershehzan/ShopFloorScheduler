"""
core/models_db.py
SQLAlchemy ORM models for persistent storage.

Tables:
  schedule_runs      — One row per optimization run
  job_records        — One row per job in a run
  operation_records  — One row per machine operation in a run
"""
import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Integer, Float, DateTime, ForeignKey, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


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

    # Relationships
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
