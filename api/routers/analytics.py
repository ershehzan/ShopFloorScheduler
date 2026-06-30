# api/routers/analytics.py
"""
Analytics router — aggregate KPIs, trends, heatmaps, and comparisons.

Routes:
  GET /api/analytics/summary                — Aggregate KPIs across all runs
  GET /api/analytics/trends                 — Time-series metrics over N runs
  GET /api/analytics/utilization-heatmap    — Per-machine utilization grid
  GET /api/analytics/algorithm-comparison   — Side-by-side algorithm stats
  GET /api/analytics/tardiness-distribution — Histogram of per-job tardiness
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.schemas import (
    AnalyticsSummary,
    TrendPoint,
    TrendsResponse,
    HeatmapCell,
    HeatmapResponse,
    AlgorithmStats,
    AlgorithmComparisonResponse,
    TardinessDistributionResponse,
)
from core.database import get_db
from core.models_db import ScheduleRun, JobRecord
from core.security import get_optional_user
from core.logger import logger

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# GET /api/analytics/summary
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Aggregate KPIs across all completed runs",
)
def get_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    query = db.query(ScheduleRun).filter(ScheduleRun.status == "complete")

    # Non-admin authenticated users see only their own data
    if current_user and not current_user.is_admin:
        query = query.filter(ScheduleRun.user_id == current_user.id)

    runs = query.all()
    total = len(runs)

    if total == 0:
        return AnalyticsSummary(
            total_runs=0,
            avg_makespan=0.0,
            avg_tardiness=0.0,
            avg_utilization=0.0,
            avg_on_time_percent=0.0,
            best_makespan=0.0,
            best_algorithm=None,
        )

    makespans = [r.makespan for r in runs if r.makespan is not None]
    tardinesses = [r.total_tardiness for r in runs if r.total_tardiness is not None]
    on_times = [r.on_time_percent for r in runs if r.on_time_percent is not None]

    # Calculate average utilization from result_json
    all_utils = []
    for r in runs:
        if r.result_json:
            try:
                data = json.loads(r.result_json)
                for u in data.get("utilization", []):
                    all_utils.append(u.get("utilization", 0))
            except (json.JSONDecodeError, KeyError):
                pass

    best_run = min(runs, key=lambda r: r.makespan or float("inf"))

    return AnalyticsSummary(
        total_runs=total,
        avg_makespan=round(sum(makespans) / len(makespans), 1) if makespans else 0.0,
        avg_tardiness=round(sum(tardinesses) / len(tardinesses), 1) if tardinesses else 0.0,
        avg_utilization=round(sum(all_utils) / len(all_utils), 4) if all_utils else 0.0,
        avg_on_time_percent=round(sum(on_times) / len(on_times), 1) if on_times else 0.0,
        best_makespan=best_run.makespan or 0.0,
        best_algorithm=best_run.algorithm,
    )


# ---------------------------------------------------------------------------
# GET /api/analytics/trends
# ---------------------------------------------------------------------------

@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Time-series metrics over recent runs",
)
def get_trends(
    limit: int = Query(default=20, ge=1, le=200, description="Number of recent runs to include"),
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    query = db.query(ScheduleRun).filter(ScheduleRun.status == "complete")

    if current_user and not current_user.is_admin:
        query = query.filter(ScheduleRun.user_id == current_user.id)

    runs = (
        query
        .order_by(ScheduleRun.created_at.desc())
        .limit(limit)
        .all()
    )

    # Reverse so oldest first (chronological order for charts)
    runs.reverse()

    points = [
        TrendPoint(
            task_id=r.task_id,
            created_at=r.created_at.isoformat() if r.created_at else "",
            algorithm=r.algorithm,
            makespan=r.makespan,
            total_tardiness=r.total_tardiness,
            avg_flow_time=r.avg_flow_time,
            on_time_percent=r.on_time_percent,
        )
        for r in runs
    ]

    return TrendsResponse(points=points, total=len(points))


# ---------------------------------------------------------------------------
# GET /api/analytics/utilization-heatmap
# ---------------------------------------------------------------------------

@router.get(
    "/utilization-heatmap",
    response_model=HeatmapResponse,
    summary="Per-machine utilization across recent runs",
)
def get_utilization_heatmap(
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent runs"),
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    query = db.query(ScheduleRun).filter(ScheduleRun.status == "complete")

    if current_user and not current_user.is_admin:
        query = query.filter(ScheduleRun.user_id == current_user.id)

    runs = (
        query
        .order_by(ScheduleRun.created_at.desc())
        .limit(limit)
        .all()
    )

    cells = []
    machine_ids_set = set()
    task_ids = []

    for r in reversed(runs):  # Chronological order
        task_ids.append(r.task_id)
        if r.result_json:
            try:
                data = json.loads(r.result_json)
                for u in data.get("utilization", []):
                    mid = u.get("machine_id")
                    util = u.get("utilization", 0)
                    if mid is not None:
                        cells.append(HeatmapCell(
                            task_id=r.task_id,
                            machine_id=mid,
                            utilization=round(util, 4),
                        ))
                        machine_ids_set.add(mid)
            except (json.JSONDecodeError, KeyError):
                pass

    return HeatmapResponse(
        cells=cells,
        machines=sorted(machine_ids_set),
        runs=task_ids,
    )


# ---------------------------------------------------------------------------
# GET /api/analytics/algorithm-comparison
# ---------------------------------------------------------------------------

@router.get(
    "/algorithm-comparison",
    response_model=AlgorithmComparisonResponse,
    summary="Side-by-side algorithm performance comparison",
)
def get_algorithm_comparison(
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    query = db.query(ScheduleRun).filter(
        ScheduleRun.status == "complete",
        ScheduleRun.algorithm.isnot(None),
    )

    if current_user and not current_user.is_admin:
        query = query.filter(ScheduleRun.user_id == current_user.id)

    runs = query.all()

    # Group by algorithm
    algo_groups: dict[str, list[ScheduleRun]] = {}
    for r in runs:
        algo = r.algorithm or "UNKNOWN"
        if algo not in algo_groups:
            algo_groups[algo] = []
        algo_groups[algo].append(r)

    algorithms = []
    for algo, group in sorted(algo_groups.items()):
        makespans = [r.makespan for r in group if r.makespan is not None]
        tardinesses = [r.total_tardiness for r in group if r.total_tardiness is not None]
        on_times = [r.on_time_percent for r in group if r.on_time_percent is not None]

        algorithms.append(AlgorithmStats(
            algorithm=algo,
            run_count=len(group),
            avg_makespan=round(sum(makespans) / len(makespans), 1) if makespans else 0.0,
            avg_tardiness=round(sum(tardinesses) / len(tardinesses), 1) if tardinesses else 0.0,
            avg_on_time_percent=round(sum(on_times) / len(on_times), 1) if on_times else 0.0,
            best_makespan=min(makespans) if makespans else 0.0,
        ))

    return AlgorithmComparisonResponse(algorithms=algorithms)


# ---------------------------------------------------------------------------
# GET /api/analytics/tardiness-distribution
# ---------------------------------------------------------------------------

@router.get(
    "/tardiness-distribution",
    response_model=TardinessDistributionResponse,
    summary="Histogram of per-job tardiness values",
)
def get_tardiness_distribution(
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent runs to analyze"),
    bucket_size: int = Query(default=5, ge=1, le=50, description="Width of each histogram bucket"),
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    query = db.query(ScheduleRun).filter(ScheduleRun.status == "complete")

    if current_user and not current_user.is_admin:
        query = query.filter(ScheduleRun.user_id == current_user.id)

    run_ids = [
        r.id for r in query.order_by(ScheduleRun.created_at.desc()).limit(limit).all()
    ]

    if not run_ids:
        return TardinessDistributionResponse(buckets=[], counts=[], total_jobs=0)

    # Get all job records from these runs
    jobs = (
        db.query(JobRecord)
        .filter(JobRecord.run_id.in_(run_ids))
        .all()
    )

    if not jobs:
        return TardinessDistributionResponse(buckets=[], counts=[], total_jobs=0)

    tardiness_values = [j.tardiness or 0.0 for j in jobs]
    max_tard = max(tardiness_values) if tardiness_values else 0

    # Build histogram buckets
    num_buckets = max(1, int(max_tard // bucket_size) + 1)
    # Cap at 20 buckets for readability
    num_buckets = min(num_buckets, 20)

    buckets = []
    counts = []
    for i in range(num_buckets):
        low = i * bucket_size
        high = (i + 1) * bucket_size
        label = f"{low}-{high}"
        count = sum(1 for t in tardiness_values if low <= t < high)
        buckets.append(label)
        counts.append(count)

    # Overflow bucket for anything beyond the last
    overflow_low = num_buckets * bucket_size
    overflow_count = sum(1 for t in tardiness_values if t >= overflow_low)
    if overflow_count > 0:
        buckets.append(f"{overflow_low}+")
        counts.append(overflow_count)

    return TardinessDistributionResponse(
        buckets=buckets,
        counts=counts,
        total_jobs=len(tardiness_values),
    )
