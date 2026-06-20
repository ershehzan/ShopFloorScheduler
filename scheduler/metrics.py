# scheduler/metrics.py
"""
Metric calculations for schedule quality assessment.

All functions are pure (no side-effects) and accept the standard
schedule list format: [(job_id, op_index, machine_id, start, end), ...]
"""
from models import Job
from core.logger import logger


def calculate_makespan(schedule: list) -> int:
    """
    Returns the makespan: the time at which the last operation finishes.

    The makespan is the primary measure of schedule efficiency —
    lower makespan means jobs are completed sooner overall.
    """
    if not schedule:
        return 0
    return max(op[4] for op in schedule)


def calculate_tardiness(schedule: list, jobs: list[Job]) -> int:
    """
    Returns total tardiness across all jobs.

    Tardiness for a job = max(0, completion_time - due_date).
    Zero means the job finished on time or early.
    """
    job_completion_times: dict[int, int] = {}
    for op in schedule:
        job_id, end_time = op[0], op[4]
        job_completion_times[job_id] = max(job_completion_times.get(job_id, 0), end_time)

    job_map = {j.job_id: j for j in jobs}
    total_tardiness = 0
    for job_id, completion_time in job_completion_times.items():
        if job_id in job_map:
            tardiness = max(0, completion_time - job_map[job_id].due_date)
            total_tardiness += tardiness

    return total_tardiness


def calculate_utilization(schedule: list, machines: list) -> dict[int, float]:
    """
    Returns per-machine utilization as a fraction (0.0 – 1.0).

    Utilization = busy_time / makespan.
    A value of 1.0 means the machine was working every time unit.
    """
    makespan = calculate_makespan(schedule)
    if makespan == 0:
        return {m.machine_id: 0.0 for m in machines}

    busy_time: dict[int, int] = {}
    for op in schedule:
        machine_id = op[2]
        duration = op[4] - op[3]
        busy_time[machine_id] = busy_time.get(machine_id, 0) + duration

    utilization = {}
    for m in machines:
        utilization[m.machine_id] = round(busy_time.get(m.machine_id, 0) / makespan, 4)

    logger.debug("Machine utilization computed: {}", utilization)
    return utilization


def calculate_avg_flow_time(schedule: list, jobs: list[Job]) -> float:
    """
    Returns the average flow time (completion time) across all jobs.

    Lower average flow time means jobs move through the system faster.
    """
    if not schedule or not jobs:
        return 0.0

    job_completion_times: dict[int, int] = {}
    for op in schedule:
        job_id, end_time = op[0], op[4]
        job_completion_times[job_id] = max(job_completion_times.get(job_id, 0), end_time)

    return round(sum(job_completion_times.values()) / len(job_completion_times), 2)


def calculate_on_time_percent(schedule: list, jobs: list[Job]) -> float:
    """
    Returns the percentage of jobs completed on or before their due date.
    """
    if not schedule or not jobs:
        return 0.0

    job_completion_times: dict[int, int] = {}
    for op in schedule:
        job_id, end_time = op[0], op[4]
        job_completion_times[job_id] = max(job_completion_times.get(job_id, 0), end_time)

    job_map = {j.job_id: j for j in jobs}
    on_time = sum(
        1
        for job_id, ct in job_completion_times.items()
        if job_id in job_map and ct <= job_map[job_id].due_date
    )
    return round((on_time / len(job_completion_times)) * 100, 1)


def build_full_metrics(schedule: list, jobs: list[Job], machines: list) -> dict:
    """
    Convenience wrapper that returns all KPI metrics in a single dict.

    Returns:
        {
            "makespan": int,
            "total_tardiness": int,
            "avg_flow_time": float,
            "on_time_percent": float,
            "utilization": {machine_id: float}
        }
    """
    return {
        "makespan": calculate_makespan(schedule),
        "total_tardiness": calculate_tardiness(schedule, jobs),
        "avg_flow_time": calculate_avg_flow_time(schedule, jobs),
        "on_time_percent": calculate_on_time_percent(schedule, jobs),
        "utilization": calculate_utilization(schedule, machines),
    }
