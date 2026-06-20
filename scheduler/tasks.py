# scheduler/tasks.py
"""
Celery task definitions for the ShopFloorScheduler optimization pipeline.

Tasks defined here are enqueued by the FastAPI layer and executed by
the Celery worker process, keeping heavy computation off the web server.

The main task `run_schedule_task` wraps the full optimization pipeline:
  1. Load data from uploaded Excel file
  2. Run the selected scheduling algorithm (GA or heuristic)
  3. Compute KPI metrics
  4. Generate Gantt chart PNG
  5. Generate Excel report
  6. Store results in the Celery result backend (Redis)
"""
import os
import copy

from celery_app import celery_app
from data_loader import load_data_from_excel
from genetic_algorithm import run_genetic_algorithm
from visualization import create_gantt_chart
from exporter import export_to_excel
from scheduler.engine import ALGORITHM_MAP
from scheduler.metrics import build_full_metrics
from core.logger import logger

# Output directories (created on first use)
STATIC_FOLDER = "static"
OUTPUT_FOLDER = "output"
for _folder in [STATIC_FOLDER, OUTPUT_FOLDER]:
    os.makedirs(_folder, exist_ok=True)


@celery_app.task(bind=True, name="scheduler.tasks.run_schedule_task", max_retries=0)
def run_schedule_task(
    self,
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
) -> dict:
    """
    Full schedule optimization pipeline executed asynchronously.

    Updates task state via `self.update_state()` so the API can report
    progress while the job is running.

    Returns a dict that becomes the Celery task result (stored in Redis).
    """
    def _update(msg: str, state: str = "PROGRESS"):
        self.update_state(state=state, meta={"message": msg})
        logger.info("[Task {}] {}", task_id, msg)

    try:
        # --- Step 1: Load Data ---
        _update("Loading production data...")
        machines, jobs_data = load_data_from_excel(filepath)
        logger.info("Loaded {} machines and {} jobs from {}", len(machines), len(jobs_data), filepath)

        # --- Step 2: Run Algorithm ---
        _update(f"Running {algorithm} algorithm...")
        machines_copy = copy.deepcopy(machines)

        if algorithm == "GA":
            schedule_result = run_genetic_algorithm(
                jobs_data,
                machines_copy,
                setup_time,
                pop_size,
                generations,
                mutation_rate,
                tournament_size,
                w_makespan,
                w_tardiness,
            )
        elif algorithm in ALGORITHM_MAP:
            schedule_result = ALGORITHM_MAP[algorithm](jobs_data, machines_copy, setup_time)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm!r}")

        logger.info("{} completed with {} scheduled operations.", algorithm, len(schedule_result))

        # --- Step 3: Compute Metrics ---
        _update("Computing KPI metrics...")
        metrics = build_full_metrics(schedule_result, jobs_data, machines)

        # --- Step 4: Generate Gantt Chart ---
        _update("Generating Gantt chart...")
        chart_filename = f"chart_{task_id}.png"
        chart_path = os.path.join(STATIC_FOLDER, chart_filename)
        create_gantt_chart(schedule_result, f"{algorithm} Schedule", save_path=chart_path)

        # --- Step 5: Generate Excel Report ---
        _update("Generating Excel report...")
        excel_filename = f"schedule_{task_id}.xlsx"
        excel_path = os.path.join(OUTPUT_FOLDER, excel_filename)
        export_to_excel(schedule_result, jobs_data, excel_path)

        # --- Step 6: Build Result Payload ---
        _update("Finalizing results...", state="COMPLETE")

        # Serialize schedule to plain dicts for JSON storage
        serialized_schedule = [
            {
                "job_id": op[0],
                "op_index": op[1],
                "machine_id": op[2],
                "start_time": op[3],
                "end_time": op[4],
            }
            for op in schedule_result
        ]

        result = {
            "state": "complete",
            "message": "Schedule optimization complete.",
            "algorithm": algorithm,
            "makespan": metrics["makespan"],
            "total_tardiness": metrics["total_tardiness"],
            "avg_flow_time": metrics["avg_flow_time"],
            "on_time_percent": metrics["on_time_percent"],
            "utilization": [
                {"machine_id": mid, "utilization": util}
                for mid, util in metrics["utilization"].items()
            ],
            "chart_url": f"/static/{chart_filename}",
            "excel_url": f"/api/schedule/download/{excel_filename}",
            "schedule": serialized_schedule,
        }

        logger.info(
            "Task {} completed. Makespan={}, Tardiness={}",
            task_id,
            metrics["makespan"],
            metrics["total_tardiness"],
        )
        return result

    except Exception as exc:
        logger.error("Task {} failed: {}", task_id, str(exc))
        # Re-raise so Celery marks the task as FAILURE in the backend
        raise exc
