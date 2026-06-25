# api/routers/schedule.py
"""
Schedule router — core scheduling API endpoints.

Routes:
  POST /api/schedule/upload         — Upload Excel file and start optimization
  GET  /api/schedule/status/{id}    — Poll task status
  GET  /api/schedule/results/{id}   — Get final results (completed tasks only)
  GET  /api/schedule/download/{fn}  — Download generated Excel report

NOTE: Uses in-process background threading when Redis/Celery is unavailable.
"""
import os
import uuid
import threading
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse

from api.schemas import (
    UploadResponse,
    ScheduleStatusResponse,
    ScheduleResultData,
    ScheduledOperationSchema,
    UtilizationSchema,
)
from core.logger import logger

router = APIRouter(prefix="/api/schedule", tags=["Scheduling"])

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# In-memory job store (replaces Celery when Redis is unavailable)
# ---------------------------------------------------------------------------
_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()


def _set_job(task_id: str, state: str, message: str = "", result: Optional[dict] = None):
    with _JOBS_LOCK:
        _JOBS[task_id] = {"state": state, "message": message, "result": result}


def _get_job(task_id: str) -> Optional[dict]:
    with _JOBS_LOCK:
        return _JOBS.get(task_id)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _run_schedule_background(
    task_id: str,
    filepath: str,
    setup_time: int,
    algorithm: str,
    pop_size: int,
    generations: int,
    mutation_rate: float,
    tournament_size: int,
    w_makespan: float,
    w_tardiness: float,
):
    """Run the full scheduling pipeline in a background thread."""
    _set_job(task_id, "processing", "Loading data...")
    try:
        from data_loader import load_data_from_excel
        from scheduler.engine import ALGORITHM_MAP, schedule_fcfs
        from scheduler.metrics import build_full_metrics
        from visualization import create_gantt_chart
        from exporter import export_to_excel
        from genetic_algorithm import run_genetic_algorithm

        logger.info("Task {}: Loading data from {}", task_id, filepath)
        _set_job(task_id, "processing", "Loading Excel data...")
        jobs, machines = load_data_from_excel(filepath)

        _set_job(task_id, "processing", f"Running {algorithm} algorithm...")
        logger.info("Task {}: Running {} algorithm", task_id, algorithm)

        if algorithm == "GA":
            best_schedule, _ = run_genetic_algorithm(
                jobs=jobs,
                machines=machines,
                setup_time=setup_time,
                pop_size=pop_size,
                generations=generations,
                mutation_rate=mutation_rate,
                tournament_size=tournament_size,
                w_makespan=w_makespan,
                w_tardiness=w_tardiness,
            )
        else:
            fn = ALGORITHM_MAP.get(algorithm)
            if fn is None:
                raise ValueError(f"Unknown algorithm: {algorithm}")
            best_schedule = fn(jobs, machines, setup_time)

        _set_job(task_id, "processing", "Generating reports...")
        logger.info("Task {}: Computing metrics", task_id)
        metrics = build_full_metrics(best_schedule, jobs, machines)

        # Generate Gantt chart
        chart_filename = f"gantt_{task_id}.png"
        chart_path = os.path.join("static", chart_filename)
        try:
            create_gantt_chart(best_schedule, machines, chart_path)
            chart_url = f"/static/{chart_filename}"
        except Exception as e:
            logger.warning("Task {}: Gantt chart generation failed: {}", task_id, e)
            chart_url = None

        # Export Excel
        excel_filename = f"schedule_{task_id}.xlsx"
        excel_path = os.path.join(OUTPUT_FOLDER, excel_filename)
        try:
            export_to_excel(best_schedule, jobs, machines, metrics, excel_path)
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

        _set_job(task_id, "complete", "Optimization complete.", result)
        logger.info(
            "Task {}: Complete. Makespan={}, Tardiness={}",
            task_id,
            metrics.get("makespan"),
            metrics.get("total_tardiness"),
        )

    except Exception as exc:
        logger.error("Task {}: Failed — {}", task_id, str(exc))
        _set_job(task_id, "error", str(exc))


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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    setup_time: int = Form(default=2, ge=0, le=60),
    algorithm: str = Form(default="GA"),
    pop_size: int = Form(default=30, ge=5, le=500),
    generations: int = Form(default=50, ge=5, le=2000),
    mutation_rate: float = Form(default=0.1, ge=0.0, le=1.0),
    tournament_size: int = Form(default=3, ge=2, le=20),
    w_makespan: float = Form(default=0.6, ge=0.0, le=1.0),
    w_tardiness: float = Form(default=0.4, ge=0.0, le=1.0),
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
    filepath = os.path.join(UPLOAD_FOLDER, f"{task_id}.xlsx")
    try:
        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error("Failed to save uploaded file: {}", str(e))
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    logger.info("File uploaded for task {}. Starting {} optimization.", task_id, algorithm)

    # Register job as pending immediately
    _set_job(task_id, "pending", "Task queued.")

    # Run in background thread (no Redis/Celery required)
    thread = threading.Thread(
        target=_run_schedule_background,
        kwargs={
            "task_id": task_id,
            "filepath": filepath,
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
    job = _get_job(task_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    return ScheduleStatusResponse(
        task_id=task_id,
        state=job["state"],
        message=job.get("message", ""),
        result=_build_result(job["result"]) if job.get("result") else None,
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
    job = _get_job(task_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    if job["state"] == "complete" and job.get("result"):
        return ScheduleStatusResponse(
            task_id=task_id,
            state="complete",
            message="Optimization complete.",
            result=_build_result(job["result"]),
        )

    if job["state"] == "error":
        return ScheduleStatusResponse(task_id=task_id, state="error", message=job.get("message", ""))

    raise HTTPException(
        status_code=404,
        detail=f"Results not available yet. Task state: {job['state']}",
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
