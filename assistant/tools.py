# assistant/tools.py
"""
Phase 5: Assistant tool functions.

Each tool queries the database or system state and returns a structured dict.
The agent calls these tools to answer user questions.
"""
from __future__ import annotations

import json
from typing import Any


def get_latest_run() -> dict[str, Any]:
    """Fetch the most recent completed schedule run."""
    from core.database import SessionLocal
    from core.models_db import ScheduleRun

    db = SessionLocal()
    try:
        run = (
            db.query(ScheduleRun)
            .filter(ScheduleRun.status == "complete")
            .order_by(ScheduleRun.created_at.desc())
            .first()
        )
        if not run:
            return {"error": "No completed runs found."}
        return {
            "task_id": run.task_id,
            "algorithm": run.algorithm,
            "makespan": run.makespan,
            "total_tardiness": run.total_tardiness,
            "avg_flow_time": run.avg_flow_time,
            "on_time_percent": run.on_time_percent,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "file_name": run.file_name,
        }
    finally:
        db.close()


def get_run_by_id(task_id: str) -> dict[str, Any]:
    """Fetch a specific schedule run by task ID."""
    from core.database import SessionLocal
    from core.models_db import ScheduleRun

    db = SessionLocal()
    try:
        run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
        if not run:
            return {"error": f"No run found with task_id '{task_id}'."}
        return {
            "task_id": run.task_id,
            "status": run.status,
            "algorithm": run.algorithm,
            "makespan": run.makespan,
            "total_tardiness": run.total_tardiness,
            "avg_flow_time": run.avg_flow_time,
            "on_time_percent": run.on_time_percent,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
    finally:
        db.close()


def list_recent_runs(limit: int = 5) -> dict[str, Any]:
    """List the N most recent schedule runs."""
    from core.database import SessionLocal
    from core.models_db import ScheduleRun

    db = SessionLocal()
    try:
        runs = (
            db.query(ScheduleRun)
            .order_by(ScheduleRun.created_at.desc())
            .limit(min(limit, 20))
            .all()
        )
        return {
            "runs": [
                {
                    "task_id": r.task_id,
                    "status": r.status,
                    "algorithm": r.algorithm,
                    "makespan": r.makespan,
                    "total_tardiness": r.total_tardiness,
                    "on_time_percent": r.on_time_percent,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in runs
            ],
            "count": len(runs),
        }
    finally:
        db.close()


def get_machine_utilization(task_id: str | None = None) -> dict[str, Any]:
    """
    Get machine utilization data.
    If task_id is provided, returns utilization for that run.
    Otherwise returns the latest run's utilization.
    """
    from core.database import SessionLocal
    from core.models_db import ScheduleRun

    db = SessionLocal()
    try:
        if task_id:
            run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
        else:
            run = (
                db.query(ScheduleRun)
                .filter(ScheduleRun.status == "complete")
                .order_by(ScheduleRun.created_at.desc())
                .first()
            )
        if not run or not run.result_json:
            return {"error": "No utilization data found."}
        result = json.loads(run.result_json)
        utilization = result.get("utilization", [])
        return {
            "task_id": run.task_id,
            "utilization": utilization,
            "lowest": min(utilization, key=lambda u: u.get("utilization", 1), default=None),
            "highest": max(utilization, key=lambda u: u.get("utilization", 0), default=None),
        }
    finally:
        db.close()


def get_late_jobs(task_id: str | None = None) -> dict[str, Any]:
    """Return jobs that were late (tardiness > 0) in a given or latest run."""
    from core.database import SessionLocal
    from core.models_db import JobRecord, ScheduleRun

    db = SessionLocal()
    try:
        if task_id:
            run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
        else:
            run = (
                db.query(ScheduleRun)
                .filter(ScheduleRun.status == "complete")
                .order_by(ScheduleRun.created_at.desc())
                .first()
            )
        if not run:
            return {"error": "No completed run found."}

        late_jobs = (
            db.query(JobRecord)
            .filter(JobRecord.run_id == run.id, JobRecord.tardiness > 0)
            .all()
        )
        return {
            "task_id": run.task_id,
            "late_jobs": [
                {
                    "job_id": j.job_id,
                    "due_date": j.due_date,
                    "completion_time": j.completion_time,
                    "tardiness": j.tardiness,
                }
                for j in late_jobs
            ],
            "count": len(late_jobs),
        }
    finally:
        db.close()


def get_maintenance_alerts(resolved: bool = False) -> dict[str, Any]:
    """Get active (or resolved) maintenance alerts."""
    from core.database import SessionLocal
    from core.models_db import MaintenanceAlert

    db = SessionLocal()
    try:
        alerts = (
            db.query(MaintenanceAlert)
            .filter(MaintenanceAlert.resolved == resolved)
            .order_by(MaintenanceAlert.created_at.desc())
            .limit(10)
            .all()
        )
        return {
            "alerts": [
                {
                    "id": a.id,
                    "machine_id": a.machine_id,
                    "severity": a.severity,
                    "failure_probability": a.failure_probability,
                    "recommended_action": a.recommended_action,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in alerts
            ],
            "count": len(alerts),
        }
    finally:
        db.close()


def get_algorithm_comparison() -> dict[str, Any]:
    """Compare average metrics across algorithms from historical runs."""
    from core.database import SessionLocal
    from core.models_db import ScheduleRun
    from sqlalchemy import func

    db = SessionLocal()
    try:
        rows = (
            db.query(
                ScheduleRun.algorithm,
                func.count(ScheduleRun.id).label("run_count"),
                func.avg(ScheduleRun.makespan).label("avg_makespan"),
                func.avg(ScheduleRun.total_tardiness).label("avg_tardiness"),
                func.avg(ScheduleRun.on_time_percent).label("avg_on_time"),
                func.min(ScheduleRun.makespan).label("best_makespan"),
            )
            .filter(ScheduleRun.status == "complete", ScheduleRun.algorithm != None)
            .group_by(ScheduleRun.algorithm)
            .all()
        )
        return {
            "comparison": [
                {
                    "algorithm": r.algorithm,
                    "run_count": r.run_count,
                    "avg_makespan": round(r.avg_makespan or 0, 1),
                    "avg_tardiness": round(r.avg_tardiness or 0, 1),
                    "avg_on_time_percent": round(r.avg_on_time or 0, 1),
                    "best_makespan": round(r.best_makespan or 0, 1),
                }
                for r in rows
            ]
        }
    finally:
        db.close()


def get_system_stats() -> dict[str, Any]:
    """Get high-level system statistics."""
    from core.database import SessionLocal
    from core.models_db import ScheduleRun, MaintenanceAlert

    db = SessionLocal()
    try:
        total = db.query(ScheduleRun).count()
        complete = db.query(ScheduleRun).filter(ScheduleRun.status == "complete").count()
        errors = db.query(ScheduleRun).filter(ScheduleRun.status == "error").count()
        active_alerts = db.query(MaintenanceAlert).filter(MaintenanceAlert.resolved == False).count()
        return {
            "total_runs": total,
            "completed_runs": complete,
            "failed_runs": errors,
            "active_maintenance_alerts": active_alerts,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, callable] = {
    "get_latest_run": get_latest_run,
    "get_run_by_id": get_run_by_id,
    "list_recent_runs": list_recent_runs,
    "get_machine_utilization": get_machine_utilization,
    "get_late_jobs": get_late_jobs,
    "get_maintenance_alerts": get_maintenance_alerts,
    "get_algorithm_comparison": get_algorithm_comparison,
    "get_system_stats": get_system_stats,
}
