# api/routers/schedule.py
"""
Schedule router — core scheduling API endpoints.

Routes:
  POST /api/schedule/upload         — Upload Excel file and start optimization
  GET  /api/schedule/status/{id}    — Poll task status
  GET  /api/schedule/results/{id}   — Get final results (completed tasks only)
  GET  /api/schedule/download/{fn}  — Download generated Excel report

NOTE: Uses in-process background threading (no Redis/Celery required).
      All state is persisted to SQLite via SQLAlchemy — no in-memory cache.
"""
import json
import os
import uuid
import threading

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse

from api.schemas import (
    UploadResponse,
    ScheduleStatusResponse,
    ScheduleResultData,
    ScheduledOperationSchema,
    UtilizationSchema,
)
from core.logger import logger
from core.security import get_optional_user

router = APIRouter(prefix="/api/schedule", tags=["Scheduling"])

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# DB helpers — read/write task state directly in SQLite
# ---------------------------------------------------------------------------

def _update_run_status(task_id: str, status: str, message: str = "", **kwargs):
    """Update a ScheduleRun row in the database."""
    from core.database import SessionLocal
    from core.models_db import ScheduleRun

    db = SessionLocal()
    try:
        run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
        if run:
            run.status = status
            if message:
                run.error_message = message if status == "error" else None
            for key, value in kwargs.items():
                if hasattr(run, key):
                    setattr(run, key, value)
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Task {}: DB status update failed — {}", task_id, str(e))
    finally:
        db.close()


def _get_run(task_id: str):
    """Fetch a ScheduleRun row from the database. Returns None if not found."""
    from core.database import SessionLocal
    from core.models_db import ScheduleRun

    db = SessionLocal()
    try:
        run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
        if not run:
            return None
        # Detach from session by reading all attrs we need
        data = {
            "task_id": run.task_id,
            "status": run.status,
            "error_message": run.error_message,
            "algorithm": run.algorithm,
            "makespan": run.makespan,
            "total_tardiness": run.total_tardiness,
            "avg_flow_time": run.avg_flow_time,
            "on_time_percent": run.on_time_percent,
            "chart_url": run.chart_url,
            "excel_url": run.excel_url,
            "result_json": run.result_json,
        }
        return data
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Background worker — runs scheduling + persists to DB
# ---------------------------------------------------------------------------

def _run_schedule_background(
    task_id: str,
    filepath: str,
    original_filename: str,
    setup_time: int,
    algorithm: str,
    pop_size: int,
    generations: int,
    mutation_rate: float,
    tournament_size: int,
    w_makespan: float,
    w_tardiness: float,
):
    """Run the full scheduling pipeline in a background thread and persist to DB."""
    _update_run_status(task_id, "processing")
    try:
        from data_loader import load_data_from_excel
        from scheduler.engine import ALGORITHM_MAP
        from scheduler.metrics import build_full_metrics
        from visualization import create_gantt_chart
        from exporter import export_to_excel
        from genetic_algorithm import run_genetic_algorithm
        from core.database import SessionLocal
        from core.models_db import ScheduleRun, JobRecord, OperationRecord
        from api.routers.ws import send_task_progress_sync, send_global_notification_sync

        logger.info("Task {}: Loading data from {}", task_id, filepath)
        machines, jobs = load_data_from_excel(filepath)

        logger.info("Task {}: Running {} algorithm", task_id, algorithm)

        if algorithm == "GA":
            # Build WebSocket progress callback
            def _ws_progress(generation, total_generations, best_fitness):
                percent = round((generation / total_generations) * 100, 1)
                send_task_progress_sync(task_id, {
                    "type": "progress",
                    "generation": generation,
                    "total_generations": total_generations,
                    "best_fitness": round(best_fitness, 2),
                    "percent": percent,
                })

            best_schedule = run_genetic_algorithm(
                jobs=jobs,
                machines=machines,
                setup_time=setup_time,
                pop_size=pop_size,
                num_gen=generations,
                mut_rate=mutation_rate,
                tourn_size=tournament_size,
                w_makespan=w_makespan,
                w_tardiness=w_tardiness,
                progress_callback=_ws_progress,
            )
        else:
            fn = ALGORITHM_MAP.get(algorithm)
            if fn is None:
                raise ValueError(f"Unknown algorithm: {algorithm}")
            best_schedule = fn(jobs, machines, setup_time)

        logger.info("Task {}: Computing metrics", task_id)
        metrics = build_full_metrics(best_schedule, jobs, machines)

        # Generate Gantt chart
        chart_filename = f"gantt_{task_id}.png"
        chart_path = os.path.join("static", chart_filename)
        try:
            create_gantt_chart(best_schedule, f"{algorithm} Schedule", chart_path)
            chart_url = f"/static/{chart_filename}"
        except Exception as e:
            logger.warning("Task {}: Gantt chart generation failed: {}", task_id, e)
            chart_url = None

        # Export Excel
        excel_filename = f"schedule_{task_id}.xlsx"
        excel_path = os.path.join(OUTPUT_FOLDER, excel_filename)
        try:
            export_to_excel(best_schedule, jobs, excel_path)
            excel_url = f"/api/schedule/download/{excel_filename}"
        except Exception as e:
            logger.warning("Task {}: Excel export failed: {}", task_id, e)
            excel_url = None

        # Build serializable schedule list
        schedule_list = [
            {
                "job_id": op[0],
                "op_index": op[1],
                "machine_id": op[2],
                "start_time": op[3],
                "end_time": op[4],
            }
            for op in best_schedule
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
            "algorithm": algorithm,
            "chart_url": chart_url,
            "excel_url": excel_url,
            "schedule": schedule_list,
            "utilization": utilization_list,
        }

        # ── Persist everything to SQLite ──────────────────────────────────────
        try:
            db = SessionLocal()
            run_row = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
            if run_row:
                run_row.status = "complete"
                run_row.algorithm = algorithm
                run_row.makespan = result["makespan"]
                run_row.total_tardiness = result["total_tardiness"]
                run_row.avg_flow_time = result["avg_flow_time"]
                run_row.on_time_percent = result["on_time_percent"]
                run_row.chart_url = chart_url
                run_row.excel_url = excel_url
                run_row.result_json = json.dumps(result)

                # Persist operations
                for op in schedule_list:
                    db.add(OperationRecord(
                        run_id=run_row.id,
                        job_id=op["job_id"],
                        op_index=op["op_index"],
                        machine_id=op["machine_id"],
                        start_time=op["start_time"],
                        end_time=op["end_time"],
                    ))

                # Persist job-level summaries (completion time = max end time per job)
                job_completion: dict[str, float] = {}
                for op in schedule_list:
                    jid = op["job_id"]
                    job_completion[jid] = max(job_completion.get(jid, 0.0), op["end_time"])

                for job in jobs:
                    jid = str(job.job_id)
                    due = getattr(job, "due_date", None)
                    ct = job_completion.get(jid, 0.0)
                    tard = max(0.0, ct - (due or ct))
                    db.add(JobRecord(
                        run_id=run_row.id,
                        job_id=jid,
                        due_date=due,
                        completion_time=ct,
                        tardiness=tard,
                    ))

                db.commit()
                logger.info("Task {}: Persisted to database (run_id={})", task_id, run_row.id)
            db.close()
        except Exception as db_err:
            logger.error("Task {}: DB persistence failed — {}", task_id, str(db_err))

        logger.info(
            "Task {}: Complete. Makespan={}, Tardiness={}",
            task_id,
            metrics.get("makespan"),
            metrics.get("total_tardiness"),
        )

        # Push completion via WebSocket
        send_task_progress_sync(task_id, {
            "type": "complete",
            "result": result,
        })
        send_global_notification_sync({
            "type": "run_completed",
            "task_id": task_id,
            "algorithm": algorithm,
            "makespan": metrics.get("makespan"),
            "total_tardiness": metrics.get("total_tardiness"),
        })

    except Exception as exc:
        logger.error("Task {}: Failed — {}", task_id, str(exc))
        _update_run_status(task_id, "error", message=str(exc))

        # Push error via WebSocket
        send_task_progress_sync(task_id, {
            "type": "error",
            "message": str(exc),
        })
        send_global_notification_sync({
            "type": "run_failed",
            "task_id": task_id,
            "error": str(exc),
        })


# ---------------------------------------------------------------------------
# POST /api/schedule/upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=202,
    summary="Upload production data and start optimization",
)
async def upload_and_schedule(
    file: UploadFile = File(...),
    setup_time: int = Form(default=2, ge=0, le=60),
    algorithm: str = Form(default="GA"),
    pop_size: int = Form(default=30, ge=5, le=500),
    generations: int = Form(default=50, ge=5, le=2000),
    mutation_rate: float = Form(default=0.1, ge=0.0, le=1.0),
    tournament_size: int = Form(default=3, ge=2, le=20),
    w_makespan: float = Form(default=0.6, ge=0.0, le=1.0),
    w_tardiness: float = Form(default=0.4, ge=0.0, le=1.0),
    current_user=Depends(get_optional_user),
) -> UploadResponse:
    # Validate file type
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are supported.")

    # Validate algorithm
    allowed_algorithms = {"GA", "FCFS", "SPT", "EDD", "WSPT"}
    algorithm = algorithm.upper()
    if algorithm not in allowed_algorithms:
        raise HTTPException(status_code=422, detail=f"algorithm must be one of {allowed_algorithms}")

    # Save uploaded file
    task_id = str(uuid.uuid4())
    original_filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, f"{task_id}.xlsx")
    try:
        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error("Failed to save uploaded file: {}", str(e))
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    logger.info("File uploaded for task {}. Starting {} optimization.", task_id, algorithm)

    # Create initial DB row (status = pending)
    try:
        from core.database import SessionLocal
        from core.models_db import ScheduleRun
        db = SessionLocal()
        db.add(ScheduleRun(
            task_id=task_id,
            status="pending",
            algorithm=algorithm,
            file_name=original_filename,
            user_id=current_user.id if current_user else None,
            trigger_type="initial",
        ))
        db.commit()
        db.close()
    except Exception as db_err:
        logger.warning("Task {}: Could not create DB row — {}", task_id, str(db_err))

    # Run in background thread (no Redis/Celery required)
    thread = threading.Thread(
        target=_run_schedule_background,
        kwargs={
            "task_id": task_id,
            "filepath": filepath,
            "original_filename": original_filename,
            "setup_time": setup_time,
            "algorithm": algorithm,
            "pop_size": pop_size,
            "generations": generations,
            "mutation_rate": mutation_rate,
            "tournament_size": tournament_size,
            "w_makespan": w_makespan,
            "w_tardiness": w_tardiness,
        },
        daemon=True,
    )
    thread.start()

    return UploadResponse(
        task_id=task_id,
        message=f"{algorithm} optimization started.",
        status_url=f"/api/schedule/status/{task_id}",
    )


# ---------------------------------------------------------------------------
# GET /api/schedule/status/{task_id}
# ---------------------------------------------------------------------------

@router.get(
    "/status/{task_id}",
    response_model=ScheduleStatusResponse,
    summary="Poll task status",
)
async def get_status(task_id: str) -> ScheduleStatusResponse:
    run = _get_run(task_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    result_data = None
    if run["status"] == "complete" and run.get("result_json"):
        try:
            result_data = _build_result(json.loads(run["result_json"]))
        except Exception:
            logger.warning("Task {}: Could not deserialize result_json", task_id)

    return ScheduleStatusResponse(
        task_id=task_id,
        state=run["status"],
        message=run.get("error_message") or "",
        result=result_data,
    )


# ---------------------------------------------------------------------------
# GET /api/schedule/results/{task_id}
# ---------------------------------------------------------------------------

@router.get(
    "/results/{task_id}",
    response_model=ScheduleStatusResponse,
    summary="Get full optimization results",
)
async def get_results(task_id: str) -> ScheduleStatusResponse:
    run = _get_run(task_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    if run["status"] == "complete" and run.get("result_json"):
        try:
            result_data = _build_result(json.loads(run["result_json"]))
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to deserialize stored results.")

        return ScheduleStatusResponse(
            task_id=task_id,
            state="complete",
            message="Optimization complete.",
            result=result_data,
        )

    if run["status"] == "error":
        return ScheduleStatusResponse(
            task_id=task_id,
            state="error",
            message=run.get("error_message") or "",
        )

    raise HTTPException(
        status_code=404,
        detail=f"Results not available yet. Task state: {run['status']}",
    )


# ---------------------------------------------------------------------------
# GET /api/schedule/download/{filename}
# ---------------------------------------------------------------------------

@router.get("/download/{filename}", summary="Download generated Excel report")
async def download_file(filename: str) -> FileResponse:
    path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_result(data: dict) -> ScheduleResultData:
    return ScheduleResultData(
        makespan=data.get("makespan", 0),
        total_tardiness=data.get("total_tardiness", 0),
        avg_flow_time=data.get("avg_flow_time", 0.0),
        on_time_percent=data.get("on_time_percent", 0.0),
        algorithm=data.get("algorithm", "UNKNOWN"),
        chart_url=data.get("chart_url"),
        excel_url=data.get("excel_url"),
        schedule=[ScheduledOperationSchema(**op) for op in data.get("schedule", [])],
        utilization=[UtilizationSchema(**u) for u in data.get("utilization", [])],
    )
