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
import copy

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse

from api.schemas import (
    UploadResponse,
    ScheduleStatusResponse,
    ScheduleResultData,
    ScheduledOperationSchema,
    UtilizationSchema,
    ComparisonRunResult,
    ComparisonResultResponse,
    ManualSchedulePatch,
    ManualScheduleResult,
)
from core.logger import logger
from core.security import get_current_user

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
            "user_id": run.user_id,
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
        elif algorithm == "RL":
            from rl.rl_scheduler import run_rl_schedule
            send_task_progress_sync(task_id, {"type": "progress", "percent": 0, "message": "RL scheduler loading model..."})
            best_schedule = run_rl_schedule(
                jobs=jobs,
                machines=machines,
                setup_time=setup_time,
                lambda_tardiness=w_tardiness,
            )
            send_task_progress_sync(task_id, {"type": "progress", "percent": 100, "message": "RL schedule complete."})
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



def _run_compare_background(
    task_id: str,
    filepath: str,
    original_filename: str,
    setup_time: int,
    algorithms: list[str],
    pop_size: int,
    generations: int,
    mutation_rate: float,
    tournament_size: int,
    w_makespan: float,
    w_tardiness: float,
):
    """Run multiple scheduling algorithms side-by-side in a background thread."""
    _update_run_status(task_id, "processing")
    try:
        from data_loader import load_data_from_excel
        from scheduler.engine import ALGORITHM_MAP
        from scheduler.metrics import build_full_metrics
        from visualization import create_gantt_chart
        from exporter import export_to_excel
        from genetic_algorithm import run_genetic_algorithm
        from core.database import SessionLocal
        from core.models_db import ScheduleRun
        from api.routers.ws import send_task_progress_sync, send_global_notification_sync

        logger.info("Task {}: Loading data from {}", task_id, filepath)
        machines, jobs = load_data_from_excel(filepath)

        results = []
        for i, algo in enumerate(algorithms):
            logger.info("Task {}: Running {} ({}/{})", task_id, algo, i + 1, len(algorithms))
            
            # Send status update for current algorithm
            send_task_progress_sync(task_id, {
                "type": "progress",
                "message": f"Running {algo} algorithm...",
                "percent": round((i / len(algorithms)) * 100, 1),
            })

            # Create a deep copy of the machines list so that state mutations
            # (available_at, last_job_id) do not leak between algorithm runs.
            algo_machines = copy.deepcopy(machines)

            if algo == "GA":
                # Build WebSocket progress callback for GA
                def _ws_progress(generation, total_generations, best_fitness):
                    base_percent = (i / len(algorithms)) * 100
                    ga_percent = (generation / total_generations) * (100 / len(algorithms))
                    percent = round(base_percent + ga_percent, 1)
                    send_task_progress_sync(task_id, {
                        "type": "progress",
                        "message": f"GA: Generation {generation}/{total_generations} (best makespan/fitness: {round(best_fitness, 2)})",
                        "percent": percent,
                    })

                best_schedule = run_genetic_algorithm(
                    jobs=jobs,
                    machines=algo_machines,
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
                fn = ALGORITHM_MAP.get(algo)
                if fn is None:
                    raise ValueError(f"Unknown algorithm: {algo}")
                best_schedule = fn(jobs, algo_machines, setup_time)

            metrics = build_full_metrics(best_schedule, jobs, algo_machines)

            # Generate Gantt chart for this algorithm
            chart_filename = f"gantt_{task_id}_{algo}.png"
            chart_path = os.path.join("static", chart_filename)
            try:
                create_gantt_chart(best_schedule, f"{algo} Schedule", chart_path)
                chart_url = f"/static/{chart_filename}"
            except Exception as e:
                logger.warning("Task {}: Gantt chart for {} failed: {}", task_id, algo, e)
                chart_url = None

            # Export Excel for this algorithm
            excel_filename = f"schedule_{task_id}_{algo}.xlsx"
            excel_path = os.path.join(OUTPUT_FOLDER, excel_filename)
            try:
                export_to_excel(best_schedule, jobs, excel_path)
                excel_url = f"/api/schedule/download/{excel_filename}"
            except Exception as e:
                logger.warning("Task {}: Excel export for {} failed: {}", task_id, algo, e)
                excel_url = None

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

            results.append({
                "algorithm": algo,
                "makespan": metrics.get("makespan", 0),
                "total_tardiness": metrics.get("total_tardiness", 0),
                "avg_flow_time": metrics.get("avg_flow_time", 0.0),
                "on_time_percent": metrics.get("on_time_percent", 0.0),
                "chart_url": chart_url,
                "excel_url": excel_url,
                "schedule": schedule_list,
                "utilization": utilization_list,
            })

        # Save to DB
        db = SessionLocal()
        try:
            run_row = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
            if run_row:
                # Find the best run among compared runs (by makespan first, then tardiness)
                best_run = min(results, key=lambda r: (r["makespan"], r["total_tardiness"]))
                
                run_row.status = "complete"
                run_row.makespan = best_run["makespan"]
                run_row.total_tardiness = best_run["total_tardiness"]
                run_row.avg_flow_time = best_run["avg_flow_time"]
                run_row.on_time_percent = best_run["on_time_percent"]
                # Store the full comparison list in result_json
                run_row.result_json = json.dumps({"results": results})
                db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

        logger.info("Task {}: Comparative optimization complete.", task_id)
        send_task_progress_sync(task_id, {
            "type": "complete",
            "result": {"results": results},
        })
        send_global_notification_sync({
            "type": "run_completed",
            "task_id": task_id,
            "algorithm": "COMPARE",
            "makespan": best_run["makespan"],
            "total_tardiness": best_run["total_tardiness"],
        })
    except Exception as e:
        logger.exception("Task {}: Comparative run failed", task_id)
        _update_run_status(task_id, "error", str(e))
        send_task_progress_sync(task_id, {
            "type": "error",
            "message": str(e),
        })
        send_global_notification_sync({
            "type": "run_failed",
            "task_id": task_id,
            "error": str(e),
        })


# ---------------------------------------------------------------------------
# POST /api/schedule/compare
# ---------------------------------------------------------------------------

@router.post(
    "/compare",
    response_model=UploadResponse,
    status_code=202,
    summary="Upload production data and run comparative scheduling across multiple algorithms",
)
async def upload_and_compare(
    file: UploadFile = File(...),
    setup_time: int = Form(default=2, ge=0, le=60),
    algorithms: str = Form(default="GA,FCFS,SPT,EDD,WSPT"),
    pop_size: int = Form(default=30, ge=5, le=500),
    generations: int = Form(default=50, ge=5, le=2000),
    mutation_rate: float = Form(default=0.1, ge=0.0, le=1.0),
    tournament_size: int = Form(default=3, ge=2, le=20),
    w_makespan: float = Form(default=0.6, ge=0.0, le=1.0),
    w_tardiness: float = Form(default=0.4, ge=0.0, le=1.0),
    current_user=Depends(get_current_user),
) -> UploadResponse:
    # Validate file type
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are supported.")

    # Validate algorithms
    algo_list = [a.strip().upper() for a in algorithms.split(",") if a.strip()]
    allowed_algorithms = {"GA", "FCFS", "SPT", "EDD", "WSPT"}
    for algo in algo_list:
        if algo not in allowed_algorithms:
            raise HTTPException(status_code=422, detail=f"Algorithm '{algo}' must be one of {allowed_algorithms}")

    if not algo_list:
        raise HTTPException(status_code=400, detail="At least one algorithm must be specified.")

    # Save uploaded file
    task_id = str(uuid.uuid4())
    original_filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, f"{task_id}.xlsx")
    try:
        MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
        contents = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large. Maximum upload size is 10 MB.")
        with open(filepath, "wb") as f:
            f.write(contents)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to save uploaded file: {}", str(e))
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    logger.info("File uploaded for comparison task {}. Algorithms: {}", task_id, algo_list)

    # Create initial DB row (status = pending, algorithm = COMPARE)
    try:
        from core.database import SessionLocal
        from core.models_db import ScheduleRun
        db = SessionLocal()
        db.add(ScheduleRun(
            task_id=task_id,
            status="pending",
            algorithm="COMPARE",
            file_name=original_filename,
            user_id=current_user.id,
            trigger_type="initial",
        ))
        db.commit()
        db.close()
    except Exception as db_err:
        logger.warning("Task {}: Could not create DB row — {}", task_id, str(db_err))

    # Run in background thread
    thread = threading.Thread(
        target=_run_compare_background,
        kwargs={
            "task_id": task_id,
            "filepath": filepath,
            "original_filename": original_filename,
            "setup_time": setup_time,
            "algorithms": algo_list,
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
        message="Comparative schedule optimization started.",
        status_url=f"/api/schedule/compare/status/{task_id}",
    )


# ---------------------------------------------------------------------------
# GET /api/schedule/compare/status/{task_id}
# ---------------------------------------------------------------------------

@router.get(
    "/compare/status/{task_id}",
    response_model=ComparisonResultResponse,
    summary="Poll comparison task status",
)
async def get_compare_status(
    task_id: str,
    current_user=Depends(get_current_user),
) -> ComparisonResultResponse:
    run = _get_run(task_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    # Ownership check
    if run.get("user_id") is not None:
        if not current_user.is_admin and current_user.id != run["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied to this schedule run.")

    results_data = None
    if run["status"] == "complete" and run.get("result_json"):
        try:
            raw_result = json.loads(run["result_json"])
            results_data = [
                ComparisonRunResult(
                    algorithm=r["algorithm"],
                    makespan=r["makespan"],
                    total_tardiness=r["total_tardiness"],
                    avg_flow_time=r["avg_flow_time"],
                    on_time_percent=r["on_time_percent"],
                    chart_url=r.get("chart_url"),
                    excel_url=r.get("excel_url"),
                    schedule=[ScheduledOperationSchema(**op) for op in r.get("schedule", [])],
                    utilization=[UtilizationSchema(**u) for u in r.get("utilization", [])],
                )
                for r in raw_result.get("results", [])
            ]
        except Exception as e:
            logger.exception("Task {}: Could not deserialize result_json for comparison status", task_id)

    return ComparisonResultResponse(
        task_id=task_id,
        state=run["status"],
        message=run.get("error_message") or "",
        results=results_data,
    )


# ---------------------------------------------------------------------------
# GET /api/schedule/compare/results/{task_id}
# ---------------------------------------------------------------------------

@router.get(
    "/compare/results/{task_id}",
    response_model=ComparisonResultResponse,
    summary="Get full comparative results",
)
async def get_compare_results(
    task_id: str,
    current_user=Depends(get_current_user),
) -> ComparisonResultResponse:
    res = await get_compare_status(task_id, current_user)
    if res.state != "complete":
        raise HTTPException(
            status_code=400,
            detail=f"Results not available yet. Task state: {res.state}",
        )
    return res


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
    current_user=Depends(get_current_user),
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
        MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
        contents = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large. Maximum upload size is 10 MB.")
        with open(filepath, "wb") as f:
            f.write(contents)
    except HTTPException:
        raise
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
            user_id=current_user.id,
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
async def get_status(
    task_id: str,
    current_user=Depends(get_current_user),
) -> ScheduleStatusResponse:
    run = _get_run(task_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    # Ownership check
    if run.get("user_id") is not None:
        if not current_user.is_admin and current_user.id != run["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied to this schedule run.")

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
async def get_results(
    task_id: str,
    current_user=Depends(get_current_user),
) -> ScheduleStatusResponse:
    run = _get_run(task_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    # Ownership check
    if run.get("user_id") is not None:
        if not current_user.is_admin and current_user.id != run["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied to this schedule run.")

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
async def download_file(
    filename: str,
    current_user=Depends(get_current_user),
) -> FileResponse:
    import pathlib

    # --- Path traversal guard ---
    safe_root = pathlib.Path(OUTPUT_FOLDER).resolve()
    requested_path = (safe_root / filename).resolve()
    if not str(requested_path).startswith(str(safe_root) + os.sep) and requested_path != safe_root:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    # Extract task_id from filename to check ownership
    task_id = filename
    if filename.startswith("schedule_") and filename.endswith(".xlsx"):
        task_id = filename[len("schedule_"):-len(".xlsx")]
    elif filename.startswith("gantt_") and filename.endswith(".png"):
        task_id = filename[len("gantt_"):-len(".png")]

    run = _get_run(task_id)
    if run is not None and run.get("user_id") is not None:
        if not current_user.is_admin and current_user.id != run["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied to this schedule run.")

    if not requested_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
    return FileResponse(
        path=str(requested_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_result(data: dict) -> ScheduleResultData:
    if "results" in data and isinstance(data["results"], list) and len(data["results"]) > 0:
        # Find the best run among compared runs (by makespan first, then tardiness)
        best_run = min(data["results"], key=lambda r: (r.get("makespan", 0), r.get("total_tardiness", 0)))
        return ScheduleResultData(
            makespan=best_run.get("makespan", 0),
            total_tardiness=best_run.get("total_tardiness", 0),
            avg_flow_time=best_run.get("avg_flow_time", 0.0),
            on_time_percent=best_run.get("on_time_percent", 0.0),
            algorithm="COMPARE",
            chart_url=best_run.get("chart_url"),
            excel_url=best_run.get("excel_url"),
            schedule=[ScheduledOperationSchema(**op) for op in best_run.get("schedule", [])],
            utilization=[UtilizationSchema(**u) for u in best_run.get("utilization", [])],
        )

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


# ---------------------------------------------------------------------------
# Phase 5 — PDF report download
# ---------------------------------------------------------------------------

@router.get(
    "/pdf/{task_id}",
    summary="Download PDF report for a completed run (Phase 5)",
    tags=["Scheduling"],
)
def download_pdf(
    task_id: str,
    current_user=Depends(get_current_user),
):
    """
    Generate (or retrieve cached) a PDF report for a completed schedule run
    and return it as a file download.
    """
    from pdf_exporter import generate_pdf_from_db

    pdf_path_candidate = os.path.join(OUTPUT_FOLDER, f"report_{task_id[:8]}.pdf")

    # Use cached PDF if it already exists
    if not os.path.exists(pdf_path_candidate):
        try:
            generate_pdf_from_db(task_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    if not os.path.exists(pdf_path_candidate):
        raise HTTPException(status_code=500, detail="PDF generation failed.")

    return FileResponse(
        path=pdf_path_candidate,
        filename=f"schedule_report_{task_id[:8]}.pdf",
        media_type="application/pdf",
    )


# ---------------------------------------------------------------------------
# Phase 5 — Manual Gantt editor PATCH
# ---------------------------------------------------------------------------

@router.patch(
    "/{task_id}/manual",
    summary="Commit a manually edited schedule (Phase 5)",
    tags=["Scheduling"],
)
def patch_manual_schedule(
    task_id: str,
    body: ManualSchedulePatch,
    current_user=Depends(get_current_user),
):
    """
    Accept a manually adjusted schedule (dragged in the Gantt editor),
    validate it for conflicts, recompute metrics, and persist the updated result.

    Returns the new KPI metrics and a list of any constraint warnings.
    """
    from scheduler.metrics import (
        calculate_makespan as compute_makespan,
        calculate_tardiness,
        calculate_avg_flow_time,
        calculate_on_time_percent,
        calculate_utilization,
    )
    from core.database import SessionLocal
    from core.models_db import ScheduleRun, JobRecord, OperationRecord
    import json

    run = _get_run(task_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.get("status") != "complete":
        raise HTTPException(status_code=409, detail="Can only edit completed runs.")
    if run.get("user_id") and not current_user.is_admin and current_user.id != run["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Re-parse body in case it's passed as dict
    if not isinstance(body, ManualSchedulePatch):
        body = ManualSchedulePatch(**body)

    ops = body.schedule
    schedule_tuples = [(o.job_id, o.op_index, o.machine_id, o.start_time, o.end_time) for o in ops]

    # --- Conflict detection ---
    conflicts: list[str] = []
    from collections import defaultdict
    by_machine: dict[int, list[tuple]] = defaultdict(list)
    for jid, oi, mid, st, et in schedule_tuples:
        by_machine[mid].append((st, et, jid, oi))

    for mid, intervals in by_machine.items():
        intervals.sort()
        for i in range(1, len(intervals)):
            if intervals[i][0] < intervals[i - 1][1]:
                conflicts.append(
                    f"Overlap on Machine {mid}: "
                    f"Job {intervals[i-1][2]} op {intervals[i-1][3]+1} ends at {intervals[i-1][1]:.0f}, "
                    f"Job {intervals[i][2]} op {intervals[i][3]+1} starts at {intervals[i][0]:.0f}"
                )

    # --- Recompute metrics ---
    result_json_orig = run.get("result_json") or "{}"
    orig_result = json.loads(result_json_orig)

    # Build job due-date map from original result
    job_due_dates: dict[int, float] = {}
    for job_rec in orig_result.get("schedule", []):
        pass  # due dates aren't in schedule ops; we'll load from JobRecord

    db = SessionLocal()
    try:
        db_run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
        if not db_run:
            raise HTTPException(status_code=404, detail="Run not found in DB.")

        job_records = db.query(JobRecord).filter(JobRecord.run_id == db_run.id).all()
        for jr in job_records:
            try:
                job_due_dates[int(jr.job_id)] = jr.due_date or 0
            except (ValueError, TypeError):
                pass

        from models import Job, Operation, Machine
        # Build synthetic jobs from schedule ops for metric computation
        job_ops: dict[int, dict] = {}
        for jid, oi, mid, st, et in schedule_tuples:
            if jid not in job_ops:
                job_ops[jid] = {"ops": [], "due_date": job_due_dates.get(jid, 9999)}
            job_ops[jid]["ops"].append(Operation(mid, int(et - st)))

        jobs = [
            Job(jid, data["ops"], int(data["due_date"]), 1)
            for jid, data in job_ops.items()
        ]

        makespan = compute_makespan(schedule_tuples)
        total_tardiness = calculate_tardiness(schedule_tuples, jobs)
        avg_flow = calculate_avg_flow_time(schedule_tuples, jobs)
        on_time = calculate_on_time_percent(schedule_tuples, jobs)

        # Build utilization
        machine_ids = list({mid for _, _, mid, _, _ in schedule_tuples})
        machines = [Machine(mid, []) for mid in machine_ids]
        util_dict = calculate_utilization(schedule_tuples, machines)
        utilization = [{"machine_id": mid, "utilization": u} for mid, u in util_dict.items()]

        new_result = {
            **orig_result,
            "makespan": makespan,
            "total_tardiness": int(total_tardiness),
            "avg_flow_time": avg_flow,
            "on_time_percent": on_time,
            "algorithm": orig_result.get("algorithm", "MANUAL"),

            "schedule": [
                {"job_id": jid, "op_index": oi, "machine_id": mid, "start_time": st, "end_time": et}
                for jid, oi, mid, st, et in schedule_tuples
            ],
            "utilization": [{"machine_id": u["machine_id"], "utilization": u["utilization"]} for u in utilization],
        }

        # Persist updated metrics
        db_run.makespan = float(makespan)
        db_run.total_tardiness = float(new_result["total_tardiness"])
        db_run.avg_flow_time = float(avg_flow)
        db_run.on_time_percent = float(on_time)
        db_run.result_json = json.dumps(new_result)
        db_run.algorithm = new_result["algorithm"]

        # Update operation records
        db.query(OperationRecord).filter(OperationRecord.run_id == db_run.id).delete()
        for jid, oi, mid, st, et in schedule_tuples:
            db.add(OperationRecord(
                run_id=db_run.id,
                job_id=str(jid), op_index=oi,
                machine_id=str(mid), start_time=st, end_time=et,
            ))
        db.commit()

        logger.info(
            "Manual schedule applied to run {}: makespan={}, conflicts={}",
            task_id[:8], makespan, len(conflicts),
        )

        return ManualScheduleResult(
            task_id=task_id,
            makespan=float(makespan),
            total_tardiness=float(new_result["total_tardiness"]),
            avg_flow_time=float(avg_flow),
            on_time_percent=float(on_time),
            conflicts=conflicts,
        )
    finally:
        db.close()

