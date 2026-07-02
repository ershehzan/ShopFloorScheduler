"""
api/routers/history.py
TASK-15: Schedule history API endpoint.

Routes:
  GET /api/history   — Paginated list of all schedule runs
"""
from typing import Optional, List
import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from core.models_db import ScheduleRun
from core.logger import logger
from core.security import get_current_user

router = APIRouter(prefix="/api/history", tags=["History"])


# ── Response Schemas ──────────────────────────────────────────────────────────

class ScheduleRunSummary(BaseModel):
    task_id: str
    created_at: datetime.datetime
    status: str
    algorithm: Optional[str]
    file_name: Optional[str]
    makespan: Optional[float]
    total_tardiness: Optional[float]
    avg_flow_time: Optional[float]
    on_time_percent: Optional[float]

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    items: List[ScheduleRunSummary]
    total: int
    page: int
    page_size: int
    pages: int


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=HistoryResponse,
    summary="Get paginated list of schedule runs",
    description=(
        "Returns a paginated, optionally-filtered list of all schedule runs. "
        "Filter by algorithm name or status. Sorted by created_at descending."
    ),
)
def get_history(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Results per page"),
    algorithm: Optional[str] = Query(default=None, description="Filter by algorithm (e.g. GA, FCFS)"),
    status: Optional[str] = Query(default=None, description="Filter by status (pending, processing, complete, error)"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> HistoryResponse:
    query = db.query(ScheduleRun)

    # Authenticated non-admin users see only their own runs
    if current_user and not current_user.is_admin:
        query = query.filter(ScheduleRun.user_id == current_user.id)

    if algorithm:
        query = query.filter(ScheduleRun.algorithm == algorithm.upper())

    if status:
        query = query.filter(ScheduleRun.status == status.lower())

    total = query.count()
    pages = max(1, -(-total // page_size))  # ceiling division

    if page > pages and total > 0:
        raise HTTPException(status_code=404, detail=f"Page {page} exceeds total pages ({pages}).")

    runs = (
        query
        .order_by(ScheduleRun.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    logger.info("History query: page={}, page_size={}, total={}", page, page_size, total)

    return HistoryResponse(
        items=[ScheduleRunSummary.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
