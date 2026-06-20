# api/schemas.py
"""
Pydantic v2 schemas for all ShopFloorScheduler API contracts.

These models are used for:
- Request validation (FastAPI automatically returns HTTP 422 on failure)
- Response serialization (type-safe JSON output)
- Swagger / OpenAPI auto-documentation (/docs)

All schemas use strict typing and include field-level documentation
so the auto-generated /docs UI is fully self-explanatory.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Sub-schemas (nested)
# ---------------------------------------------------------------------------

class OperationSchema(BaseModel):
    """A single manufacturing operation: one step of a job on one machine."""

    machine_id: int = Field(..., description="ID of the machine that performs this operation.", ge=1)
    processing_time: int = Field(..., description="Time units required to complete this operation.", ge=1)

    model_config = {"json_schema_extra": {"example": {"machine_id": 2, "processing_time": 15}}}


class JobSchema(BaseModel):
    """A production job consisting of one or more sequential operations."""

    job_id: int = Field(..., description="Unique job identifier.", ge=1)
    due_date: int = Field(..., description="Latest acceptable completion time (time units).", ge=0)
    priority: int = Field(..., description="Scheduling priority weight (higher = more important).", ge=1)
    operations: list[OperationSchema] = Field(..., description="Ordered list of operations for this job.")


class MachineSchema(BaseModel):
    """A shop floor machine with optional maintenance windows."""

    machine_id: int = Field(..., description="Unique machine identifier.", ge=1)
    unavailable_periods: list[tuple[int, int]] = Field(
        default_factory=list,
        description="List of (start, end) time tuples when the machine is under maintenance.",
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ScheduleRequest(BaseModel):
    """
    Configuration parameters for a schedule optimization run.
    Submitted as multipart/form-data alongside the Excel file upload.
    """

    setup_time: int = Field(
        default=2,
        ge=0,
        le=60,
        description="Time units required when switching between different jobs on the same machine.",
    )
    algorithm: str = Field(
        default="GA",
        description="Primary algorithm to run. One of: GA, FCFS, SPT, EDD, WSPT.",
    )
    pop_size: int = Field(
        default=30,
        ge=5,
        le=500,
        description="GA: Number of individuals in the population per generation.",
    )
    generations: int = Field(
        default=50,
        ge=5,
        le=2000,
        description="GA: Number of evolution generations to run.",
    )
    mutation_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="GA: Probability (0–1) that a chromosome undergoes swap mutation.",
    )
    tournament_size: int = Field(
        default=3,
        ge=2,
        le=20,
        description="GA: Number of individuals that compete in each selection tournament.",
    )
    w_makespan: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="GA multi-objective weight for makespan (w_makespan + w_tardiness should = 1.0).",
    )
    w_tardiness: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="GA multi-objective weight for tardiness.",
    )

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        allowed = {"GA", "FCFS", "SPT", "EDD", "WSPT"}
        if v.upper() not in allowed:
            raise ValueError(f"algorithm must be one of {allowed}")
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "setup_time": 2,
                "algorithm": "GA",
                "pop_size": 30,
                "generations": 50,
                "mutation_rate": 0.1,
                "tournament_size": 3,
                "w_makespan": 0.6,
                "w_tardiness": 0.4,
            }
        }
    }


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ScheduledOperationSchema(BaseModel):
    """A single scheduled operation entry in a completed schedule."""

    job_id: int
    op_index: int
    machine_id: int
    start_time: int
    end_time: int


class UtilizationSchema(BaseModel):
    """Per-machine utilization metrics."""

    machine_id: int
    utilization: float = Field(..., description="Fraction of makespan during which machine was busy (0–1).")


class ScheduleResultData(BaseModel):
    """Full result payload for a completed schedule run."""

    makespan: int = Field(..., description="Total time from start to finish of all operations.")
    total_tardiness: int = Field(..., description="Sum of per-job tardiness (0 if all on time).")
    avg_flow_time: float = Field(..., description="Average job completion time.")
    on_time_percent: float = Field(..., description="Percentage of jobs completed by their due date.")
    algorithm: str = Field(..., description="Algorithm used for this run.")
    chart_url: Optional[str] = Field(None, description="URL to the Gantt chart PNG.")
    excel_url: Optional[str] = Field(None, description="URL to download the Excel report.")
    schedule: list[ScheduledOperationSchema] = Field(
        default_factory=list,
        description="Full operation-level schedule.",
    )
    utilization: list[UtilizationSchema] = Field(
        default_factory=list,
        description="Per-machine utilization breakdown.",
    )


class ScheduleStatusResponse(BaseModel):
    """
    Response for GET /api/schedule/status/{task_id}.
    Clients should poll this endpoint until state == 'complete' or 'error'.
    """

    task_id: str
    state: str = Field(..., description="One of: pending, processing, complete, error.")
    message: str = Field(default="", description="Human-readable status message.")
    result: Optional[ScheduleResultData] = Field(
        None,
        description="Populated only when state == 'complete'.",
    )


class UploadResponse(BaseModel):
    """Response returned immediately after a successful file upload."""

    task_id: str = Field(..., description="Unique ID to track this optimization run.")
    message: str = Field(default="Schedule optimization started.")
    status_url: str = Field(..., description="URL to poll for status updates.")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="ok")
    version: str = Field(default="1.0.0")
