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
        allowed = {"GA", "FCFS", "SPT", "EDD", "WSPT", "RL"}
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


# ---------------------------------------------------------------------------
# Authentication schemas (Phase 3)
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: str = Field(..., description="User email address.", min_length=5, max_length=255)
    username: str = Field(..., description="Display name.", min_length=3, max_length=100)
    password: str = Field(..., description="Account password.", min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format.")
        return v.lower().strip()


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: str = Field(..., description="User email address.")
    password: str = Field(..., description="Account password.")


class TokenResponse(BaseModel):
    """JWT token pair returned on successful login/refresh."""

    access_token: str = Field(..., description="Short-lived JWT access token (30 min).")
    refresh_token: str = Field(..., description="Long-lived JWT refresh token (7 days).")
    token_type: str = Field(default="bearer")


class RefreshRequest(BaseModel):
    """Request body for token refresh or logout."""

    refresh_token: str = Field(..., description="The refresh token to exchange or revoke.")


class UserProfile(BaseModel):
    """Current user profile response."""

    id: int
    email: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: str


# ---------------------------------------------------------------------------
# Analytics schemas (Phase 3)
# ---------------------------------------------------------------------------

class AnalyticsSummary(BaseModel):
    """Aggregate KPIs across all completed runs."""

    total_runs: int = Field(..., description="Total number of completed schedule runs.")
    avg_makespan: float = Field(..., description="Average makespan across completed runs.")
    avg_tardiness: float = Field(..., description="Average total tardiness.")
    avg_utilization: float = Field(..., description="Average machine utilization (0-1).")
    avg_on_time_percent: float = Field(..., description="Average on-time completion percentage.")
    best_makespan: float = Field(..., description="Best (lowest) makespan achieved.")
    best_algorithm: Optional[str] = Field(None, description="Algorithm that achieved the best makespan.")


class TrendPoint(BaseModel):
    """Single data point in a time-series trend."""

    task_id: str
    created_at: str
    algorithm: Optional[str] = None
    makespan: Optional[float] = None
    total_tardiness: Optional[float] = None
    avg_flow_time: Optional[float] = None
    on_time_percent: Optional[float] = None


class TrendsResponse(BaseModel):
    """Time-series trend data for analytics charts."""

    points: list[TrendPoint] = Field(default_factory=list)
    total: int = 0


class HeatmapCell(BaseModel):
    """Single cell in the utilization heatmap."""

    task_id: str
    machine_id: int
    utilization: float


class HeatmapResponse(BaseModel):
    """Machine utilization heatmap data."""

    cells: list[HeatmapCell] = Field(default_factory=list)
    machines: list[int] = Field(default_factory=list, description="All machine IDs.")
    runs: list[str] = Field(default_factory=list, description="Task IDs of included runs.")


class AlgorithmStats(BaseModel):
    """Aggregate stats for a single algorithm."""

    algorithm: str
    run_count: int
    avg_makespan: float
    avg_tardiness: float
    avg_on_time_percent: float
    best_makespan: float


class AlgorithmComparisonResponse(BaseModel):
    """Side-by-side algorithm performance comparison."""

    algorithms: list[AlgorithmStats] = Field(default_factory=list)


class TardinessDistributionResponse(BaseModel):
    """Histogram data for tardiness distribution."""

    buckets: list[str] = Field(default_factory=list, description="Bucket labels (e.g., '0-5', '5-10').")
    counts: list[int] = Field(default_factory=list, description="Number of jobs in each bucket.")
    total_jobs: int = 0


# ---------------------------------------------------------------------------
# Rescheduling schemas (Phase 3)
# ---------------------------------------------------------------------------

class BreakdownRequest(BaseModel):
    """Request to report a machine breakdown and trigger rescheduling."""

    task_id: str = Field(..., description="Task ID of the original schedule to reschedule.")
    machine_id: int = Field(..., description="ID of the broken machine.", ge=0)
    downtime_start: int = Field(..., description="Start time of the breakdown.", ge=0)
    downtime_end: int = Field(..., description="End time of the breakdown.", ge=1)

    @field_validator("downtime_end")
    @classmethod
    def validate_downtime_range(cls, v: int, info) -> int:
        start = info.data.get("downtime_start", 0)
        if v <= start:
            raise ValueError("downtime_end must be greater than downtime_start.")
        return v


class RushOrderOperation(BaseModel):
    """A single operation in a rush order."""

    machine_id: int = Field(..., ge=0)
    processing_time: int = Field(..., ge=1)


class RushJobSchema(BaseModel):
    """Definition of a rush job to insert."""

    job_id: int = Field(..., ge=1)
    operations: list[RushOrderOperation] = Field(..., min_length=1)
    due_date: int = Field(..., ge=0)
    priority: int = Field(default=10, ge=1, description="Higher = more urgent.")


class RushOrderRequest(BaseModel):
    """Request to inject a rush order into an existing schedule."""

    task_id: str = Field(..., description="Task ID of the original schedule.")
    rush_job: RushJobSchema = Field(..., description="The rush job to inject.")


# ---------------------------------------------------------------------------
# Comparison schemas (Phase 4 / New Work)
# ---------------------------------------------------------------------------

class ComparisonRunResult(BaseModel):
    """Result summary for a single algorithm run within a comparative analysis."""

    algorithm: str
    makespan: int
    total_tardiness: int
    avg_flow_time: float
    on_time_percent: float
    schedule: list[ScheduledOperationSchema] = Field(default_factory=list)
    utilization: list[UtilizationSchema] = Field(default_factory=list)
    chart_url: Optional[str] = None
    excel_url: Optional[str] = None


class ComparisonResultResponse(BaseModel):
    """Response containing side-by-side results for multiple compared algorithms."""

    task_id: str
    state: str = Field(..., description="One of: pending, processing, complete, error.")
    message: str = Field(default="")
    results: Optional[list[ComparisonRunResult]] = Field(
        None,
        description="Populated with all run results when state == 'complete'.",
    )


# ---------------------------------------------------------------------------
# Phase 4: Predictive Maintenance schemas
# ---------------------------------------------------------------------------

class SensorReadingIn(BaseModel):
    """A single explicit sensor reading for one machine at one timestamp."""

    machine_id: str = Field(..., description="Target machine identifier.")
    timestamp: Optional[str] = Field(None, description="ISO-8601 timestamp; defaults to now.")
    temperature: float = Field(..., ge=0.0, le=200.0, description="Temperature in °C.")
    vibration: float = Field(..., ge=0.0, le=50.0, description="Vibration in mm/s RMS.")
    load_pct: float = Field(..., ge=0.0, le=100.0, description="Machine load percentage (0-100).")


class SensorIngestRequest(BaseModel):
    """
    Request body for POST /api/maintenance/ingest.

    Either supply explicit readings OR set auto_generate=true.
    """

    auto_generate: bool = Field(
        default=False,
        description="When true, auto-generates synthetic readings for machine_ids.",
    )
    machine_ids: Optional[list[str]] = Field(
        None,
        description="Machine IDs to simulate (used when auto_generate=true).",
    )
    n_readings: Optional[int] = Field(
        None,
        ge=1, le=500,
        description="Number of readings per machine (auto_generate only).",
    )
    readings: Optional[list[SensorReadingIn]] = Field(
        None,
        description="Explicit sensor readings (used when auto_generate=false).",
    )


class MachineHealthOut(BaseModel):
    """Sensor health snapshot for one machine at one point in time."""

    id: int
    machine_id: str
    timestamp: str
    temperature: float
    vibration: float
    load_pct: float
    failure_probability: float = Field(..., description="Predicted failure probability (0-1).")
    anomaly_score: Optional[float] = Field(None, description="Raw Isolation Forest anomaly score.")


class MaintenanceAlertOut(BaseModel):
    """A maintenance alert generated by the anomaly detector."""

    id: int
    machine_id: str
    created_at: str
    predicted_failure_at: Optional[str]
    severity: str = Field(..., description="One of: low, medium, high, critical.")
    failure_probability: float
    recommended_action: Optional[str]
    resolved: bool
    resolved_at: Optional[str]


class MaintenanceForecastItem(BaseModel):
    """Forecast data for a single machine."""

    machine_id: str
    failure_probability: float
    severity: str
    predicted_failure_at: Optional[str]
    recommended_action: Optional[str]
    unavailability_windows: list[tuple[float, float]] = Field(
        default_factory=list,
        description="Scheduler-compatible (start, end) time-unit windows.",
    )


class MaintenanceForecastOut(BaseModel):
    """Maintenance forecast response: per-machine failure predictions + unavailability windows."""

    windows: dict[str, MaintenanceForecastItem]
    generated_at: str


# ---------------------------------------------------------------------------
# Phase 4: Reinforcement Learning schemas
# ---------------------------------------------------------------------------

class RLTrainRequest(BaseModel):
    """Request body for POST /api/rl/train."""

    episodes: int = Field(default=500, ge=10, le=10000, description="Number of training episodes.")
    learning_rate: float = Field(default=0.1, ge=0.001, le=1.0, description="Q-learning alpha.")
    discount_factor: float = Field(default=0.95, ge=0.0, le=1.0, description="Q-learning gamma.")
    epsilon: float = Field(default=1.0, ge=0.0, le=1.0, description="Initial exploration rate.")
    epsilon_decay: float = Field(default=0.995, ge=0.9, le=1.0, description="Epsilon decay per episode.")
    epsilon_min: float = Field(default=0.05, ge=0.0, le=0.5, description="Minimum exploration rate.")
    lambda_tardiness: float = Field(default=0.5, ge=0.0, le=5.0, description="Tardiness penalty weight.")
    model_name: Optional[str] = Field(None, description="Optional label for saved model.")


class RLTrainStatusOut(BaseModel):
    """Status response for an RL training run."""

    training_id: str
    status: str = Field(..., description="One of: running, complete, error.")
    episodes_done: int
    total_episodes: int
    current_reward: Optional[float] = None
    best_reward: Optional[float] = None
    message: str = Field(default="")
    model_path: Optional[str] = Field(None, description="Path to saved model (when complete).")


class RLModelOut(BaseModel):
    """A saved RL model entry."""

    model_id: str
    model_name: Optional[str]
    created_at: str
    episodes_trained: int
    best_reward: Optional[float]
    file_path: str


# ---------------------------------------------------------------------------
# Phase 4: Digital Twin schemas
# ---------------------------------------------------------------------------

class TwinStartRequest(BaseModel):
    """Request to start a digital twin simulation session."""

    task_id: str = Field(..., description="Completed schedule run task_id to simulate.")
    speed_factor: float = Field(
        default=10.0,
        ge=0.1, le=1000.0,
        description="Simulation speed multiplier. 10 = 10× real-time.",
    )
    inject_failures: bool = Field(
        default=True,
        description="If true, the twin will inject random disruptions based on ML predictions.",
    )


class TwinSessionOut(BaseModel):
    """A digital twin session."""

    session_id: str
    task_id: str
    status: str = Field(..., description="One of: running, paused, complete, error.")
    speed_factor: float
    created_at: str
    ws_url: str = Field(..., description="WebSocket URL to subscribe to simulation events.")


class TwinInjectRequest(BaseModel):
    """Inject a disruption into an active twin session."""

    disruption_type: str = Field(
        ...,
        description="Type of disruption: 'breakdown' or 'rush_order'.",
    )
    machine_id: Optional[str] = Field(None, description="Target machine (for breakdown).")
    at_time: Optional[float] = Field(None, ge=0.0, description="Virtual time to inject breakdown.")
    rush_job: Optional[dict] = Field(None, description="Rush job spec (for rush_order type).")
