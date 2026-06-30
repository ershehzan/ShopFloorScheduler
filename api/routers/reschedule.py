# api/routers/reschedule.py
"""
Dynamic rescheduling router — handle machine breakdowns and rush orders.

Routes:
  POST /api/reschedule/breakdown   — Report machine breakdown, trigger rescheduling
  POST /api/reschedule/rush-order  — Inject a rush job into an existing schedule
"""
import copy
import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import (
    BreakdownRequest,
    RushOrderRequest,
    UploadResponse,
)
from core.database import get_db
from core.models_db import ScheduleRun, JobRecord, OperationRecord
from core.security import get_optional_user
from core.logger import logger
from models import Job, Operation, Machine

router = APIRouter(prefix="/api/reschedule", tags=["Rescheduling"])


def _reconstruct_jobs_machines(run: ScheduleRun, db: Session):
    """
    Reconstruct Job and Machine objects from a completed schedule run.

    Since we store operations in the DB but not the original job/machine definitions,
    we reconstruct from the stored data. The original file is also re-parsed if available.
    """
    from data_loader import load_data_from_excel

    # Try to reload from the original file
    if run.file_name:
        upload_path = os.path.join("uploads", f"{run.task_id}.xlsx")
        if os.path.exists(upload_path):
            machines, jobs = load_data_from_excel(upload_path)
            return jobs, machines

    raise HTTPException(
        status_code=404,
        detail="Original data file not found. Cannot reschedule.",
    )


def _get_schedule_from_run(run: ScheduleRun, db: Session) -> list:
    """Extract the raw schedule list from a completed run's result_json."""
    if not run.result_json:
        raise HTTPException(status_code=404, detail="No result data found for this run.")

    try:
        data = json.loads(run.result_json)
        schedule = [
            (op["job_id"], op["op_index"], op["machine_id"], op["start_time"], op["end_time"])
            for op in data.get("schedule", [])
        ]
        return schedule
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse schedule data: {e}")


# ---------------------------------------------------------------------------
# POST /api/reschedule/breakdown
# ---------------------------------------------------------------------------

@router.post(
    "/breakdown",
    response_model=UploadResponse,
    status_code=202,
    summary="Report machine breakdown and trigger rescheduling",
)
def reschedule_breakdown(
    body: BreakdownRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    from scheduler.rescheduler import reschedule_after_breakdown
    from scheduler.metrics import build_full_metrics
    from visualization import create_gantt_chart
    from exporter import export_to_excel

    # Find the original run
    original_run = db.query(ScheduleRun).filter(
        ScheduleRun.task_id == body.task_id,
        ScheduleRun.status == "complete",
    ).first()

    if not original_run:
        raise HTTPException(status_code=404, detail=f"Completed run '{body.task_id}' not found.")

    # Reconstruct data
    original_schedule = _get_schedule_from_run(original_run, db)
    jobs, machines = _reconstruct_jobs_machines(original_run, db)

    # Run rescheduling
    new_schedule = reschedule_after_breakdown(
        original_schedule=original_schedule,
        broken_machine_id=body.machine_id,
        downtime_start=body.downtime_start,
        downtime_end=body.downtime_end,
        jobs=jobs,
        machines=machines,
        setup_time=2,  # Use default setup time
    )

    # Compute metrics
    metrics = build_full_metrics(new_schedule, jobs, machines)

    # Create new task ID for the rescheduled run
    new_task_id = str(uuid.uuid4())

    # Generate Gantt chart
    chart_filename = f"gantt_{new_task_id}.png"
    chart_path = os.path.join("static", chart_filename)
    chart_url = None
    try:
        create_gantt_chart(new_schedule, "Rescheduled (Breakdown)", chart_path)
        chart_url = f"/static/{chart_filename}"
    except Exception as e:
        logger.warning("Rescheduling: Gantt chart failed: {}", e)

    # Export Excel
    excel_filename = f"schedule_{new_task_id}.xlsx"
    excel_path = os.path.join("output", excel_filename)
    excel_url = None
    try:
        export_to_excel(new_schedule, jobs, excel_path)
        excel_url = f"/api/schedule/download/{excel_filename}"
    except Exception as e:
        logger.warning("Rescheduling: Excel export failed: {}", e)

    # Build result
    schedule_list = [
        {"job_id": op[0], "op_index": op[1], "machine_id": op[2],
         "start_time": op[3], "end_time": op[4]}
        for op in new_schedule
    ]
    utilization_list = [
        {"machine_id": m_id, "utilization": util}
        for m_id, util in metrics.get("utilization", {}).items()
    ]
    result = {
        "makespan": metrics.get("makespan", 0),
        "total_tardiness": metrics.get("total_tardiness", 0),
        "avg_flow_time": metrics.get("avg_flow_time", 0.0),
        "on_time_percent": metrics.get("on_time_percent", 0.0),
        "algorithm": original_run.algorithm or "FCFS",
        "chart_url": chart_url,
        "excel_url": excel_url,
        "schedule": schedule_list,
        "utilization": utilization_list,
    }

    # Persist to DB
    new_run = ScheduleRun(
        task_id=new_task_id,
        status="complete",
        algorithm=original_run.algorithm,
        file_name=original_run.file_name,
        makespan=result["makespan"],
        total_tardiness=result["total_tardiness"],
        avg_flow_time=result["avg_flow_time"],
        on_time_percent=result["on_time_percent"],
        chart_url=chart_url,
        excel_url=excel_url,
        result_json=json.dumps(result),
        user_id=current_user.id if current_user else original_run.user_id,
        parent_run_id=original_run.id,
        trigger_type="breakdown",
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    # Persist operations
    for op in schedule_list:
        db.add(OperationRecord(
            run_id=new_run.id,
            job_id=op["job_id"],
            op_index=op["op_index"],
            machine_id=op["machine_id"],
            start_time=op["start_time"],
            end_time=op["end_time"],
        ))
    db.commit()

    logger.info(
        "Rescheduled after breakdown: new_task_id={}, makespan={}",
        new_task_id, result["makespan"],
    )

    return UploadResponse(
        task_id=new_task_id,
        message=f"Rescheduled after machine {body.machine_id} breakdown.",
        status_url=f"/api/schedule/status/{new_task_id}",
    )


# ---------------------------------------------------------------------------
# POST /api/reschedule/rush-order
# ---------------------------------------------------------------------------

@router.post(
    "/rush-order",
    response_model=UploadResponse,
    status_code=202,
    summary="Inject a rush job into an existing schedule",
)
def reschedule_rush_order(
    body: RushOrderRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    from scheduler.rescheduler import insert_rush_order
    from scheduler.metrics import build_full_metrics
    from visualization import create_gantt_chart
    from exporter import export_to_excel

    # Find the original run
    original_run = db.query(ScheduleRun).filter(
        ScheduleRun.task_id == body.task_id,
        ScheduleRun.status == "complete",
    ).first()

    if not original_run:
        raise HTTPException(status_code=404, detail=f"Completed run '{body.task_id}' not found.")

    # Reconstruct data
    original_schedule = _get_schedule_from_run(original_run, db)
    jobs, machines = _reconstruct_jobs_machines(original_run, db)

    # Convert rush job schema to domain model
    rush_job = Job(
        job_id=body.rush_job.job_id,
        operations=[
            Operation(op.machine_id, op.processing_time)
            for op in body.rush_job.operations
        ],
        due_date=body.rush_job.due_date,
        priority=body.rush_job.priority,
    )

    # Run rescheduling
    new_schedule = insert_rush_order(
        original_schedule=original_schedule,
        rush_job=rush_job,
        jobs=jobs,
        machines=machines,
        setup_time=2,
        current_time=0,  # Assume all work is future
    )

    # Include the rush job in the jobs list for metrics
    all_jobs = jobs + [rush_job]
    metrics = build_full_metrics(new_schedule, all_jobs, machines)

    new_task_id = str(uuid.uuid4())

    # Gantt + Excel
    chart_filename = f"gantt_{new_task_id}.png"
    chart_path = os.path.join("static", chart_filename)
    chart_url = None
    try:
        create_gantt_chart(new_schedule, "Rescheduled (Rush Order)", chart_path)
        chart_url = f"/static/{chart_filename}"
    except Exception as e:
        logger.warning("Rush order: Gantt chart failed: {}", e)

    excel_filename = f"schedule_{new_task_id}.xlsx"
    excel_path = os.path.join("output", excel_filename)
    excel_url = None
    try:
        export_to_excel(new_schedule, all_jobs, excel_path)
        excel_url = f"/api/schedule/download/{excel_filename}"
    except Exception as e:
        logger.warning("Rush order: Excel export failed: {}", e)

    schedule_list = [
        {"job_id": op[0], "op_index": op[1], "machine_id": op[2],
         "start_time": op[3], "end_time": op[4]}
        for op in new_schedule
    ]
    utilization_list = [
        {"machine_id": m_id, "utilization": util}
        for m_id, util in metrics.get("utilization", {}).items()
    ]
    result = {
        "makespan": metrics.get("makespan", 0),
        "total_tardiness": metrics.get("total_tardiness", 0),
        "avg_flow_time": metrics.get("avg_flow_time", 0.0),
        "on_time_percent": metrics.get("on_time_percent", 0.0),
        "algorithm": original_run.algorithm or "FCFS",
        "chart_url": chart_url,
        "excel_url": excel_url,
        "schedule": schedule_list,
        "utilization": utilization_list,
    }

    # Persist
    new_run = ScheduleRun(
        task_id=new_task_id,
        status="complete",
        algorithm=original_run.algorithm,
        file_name=original_run.file_name,
        makespan=result["makespan"],
        total_tardiness=result["total_tardiness"],
        avg_flow_time=result["avg_flow_time"],
        on_time_percent=result["on_time_percent"],
        chart_url=chart_url,
        excel_url=excel_url,
        result_json=json.dumps(result),
        user_id=current_user.id if current_user else original_run.user_id,
        parent_run_id=original_run.id,
        trigger_type="rush_order",
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    for op in schedule_list:
        db.add(OperationRecord(
            run_id=new_run.id,
            job_id=op["job_id"],
            op_index=op["op_index"],
            machine_id=op["machine_id"],
            start_time=op["start_time"],
            end_time=op["end_time"],
        ))
    db.commit()

    logger.info(
        "Rush order inserted: new_task_id={}, makespan={}",
        new_task_id, result["makespan"],
    )

    return UploadResponse(
        task_id=new_task_id,
        message=f"Rush order (Job {body.rush_job.job_id}) inserted.",
        status_url=f"/api/schedule/status/{new_task_id}",
    )
