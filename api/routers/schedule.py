# api/routers/schedule.py
"""
Schedule router — core scheduling API endpoints.

Routes:
  POST /api/schedule/upload         — Upload Excel file and start optimization
  GET  /api/schedule/status/{id}    — Poll task status
  GET  /api/schedule/results/{id}   — Get final results (completed tasks only)
  GET  /api/schedule/download/{fn}  — Download generated Excel report
"""
import os
import uuid

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from celery.result import AsyncResult

from celery_app import celery_app
from scheduler.tasks import run_schedule_task
from api.schemas import UploadResponse, ScheduleStatusResponse, ScheduleResultData, ScheduledOperationSchema, UtilizationSchema
from core.logger import logger

router = APIRouter(prefix="/api/schedule", tags=["Scheduling"])

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# POST /api/schedule/upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=202,
    summary="Upload production data and start optimization",
    description=(
        "Accepts a multipart/form-data request with an Excel (.xlsx) file and "
        "scheduling configuration parameters. Returns a task_id immediately; "
        "use GET /api/schedule/status/{task_id} to track progress."
    ),
)
async def upload_and_schedule(
    file: UploadFile = File(..., description="Excel file with 'Jobs' and 'Machines' sheets."),
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
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are supported.")

    # Validate algorithm choice
    allowed_algorithms = {"GA", "FCFS", "SPT", "EDD", "WSPT"}
    if algorithm.upper() not in allowed_algorithms:
        raise HTTPException(
            status_code=422,
            detail=f"algorithm must be one of {allowed_algorithms}",
        )

    # Save uploaded file with unique name
    task_id = str(uuid.uuid4())
    filepath = os.path.join(UPLOAD_FOLDER, f"{task_id}.xlsx")

    try:
        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error("Failed to save uploaded file: {}", str(e))
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    logger.info("File uploaded for task {}. Starting {} optimization.", task_id, algorithm.upper())

    # Enqueue Celery task
    run_schedule_task.apply_async(
        kwargs={
            "task_id": task_id,
            "filepath": filepath,
            "setup_time": setup_time,
            "algorithm": algorithm.upper(),
            "pop_size": pop_size,
            "generations": generations,
            "mutation_rate": mutation_rate,
            "tournament_size": tournament_size,
            "w_makespan": w_makespan,
            "w_tardiness": w_tardiness,
        },
        task_id=task_id,  # Use our UUID as the Celery task ID for easy lookup
    )

    return UploadResponse(
        task_id=task_id,
        message=f"{algorithm.upper()} optimization started. Poll the status URL for updates.",
        status_url=f"/api/schedule/status/{task_id}",
    )


# ---------------------------------------------------------------------------
# GET /api/schedule/status/{task_id}
# ---------------------------------------------------------------------------

@router.get(
    "/status/{task_id}",
    response_model=ScheduleStatusResponse,
    summary="Poll task status",
    description="Returns the current state of an optimization task. Poll every 2–3 seconds until state is 'complete' or 'error'.",
)
async def get_status(task_id: str) -> ScheduleStatusResponse:
    result: AsyncResult = celery_app.AsyncResult(task_id)
    state = result.state

    logger.debug("Status check for task {}: {}", task_id, state)

    if state == "PENDING":
        return ScheduleStatusResponse(task_id=task_id, state="pending", message="Task is queued.")

    if state == "PROGRESS":
        meta = result.info or {}
        return ScheduleStatusResponse(
            task_id=task_id,
            state="processing",
            message=meta.get("message", "Processing..."),
        )

    if state == "SUCCESS":
        data = result.result or {}
        return ScheduleStatusResponse(
            task_id=task_id,
            state="complete",
            message="Optimization complete.",
            result=_build_result(data),
        )

    if state == "FAILURE":
        err = str(result.info) if result.info else "Unknown error."
        return ScheduleStatusResponse(task_id=task_id, state="error", message=err)

    # REVOKED or other states
    return ScheduleStatusResponse(task_id=task_id, state=state.lower(), message="Unexpected task state.")


# ---------------------------------------------------------------------------
# GET /api/schedule/results/{task_id}
# ---------------------------------------------------------------------------

@router.get(
    "/results/{task_id}",
    response_model=ScheduleResultData,
    summary="Get full optimization results",
    description="Returns the complete result payload for a finished task. Returns 404 if the task is still running.",
)
async def get_results(task_id: str) -> ScheduleResultData:
    result: AsyncResult = celery_app.AsyncResult(task_id)

    if result.state != "SUCCESS":
        raise HTTPException(
            status_code=404,
            detail=f"Results not available. Task state: {result.state}",
        )

    data = result.result or {}
    return _build_result(data)


# ---------------------------------------------------------------------------
# GET /api/schedule/download/{filename}
# ---------------------------------------------------------------------------

@router.get(
    "/download/{filename}",
    summary="Download generated Excel report",
    description="Streams the Excel schedule export as a file download.",
)
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
    """Convert the raw Celery result dict into a typed ScheduleResultData."""
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
