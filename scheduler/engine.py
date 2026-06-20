# scheduler/engine.py
"""
Core scheduling engine for ShopFloorScheduler.

Contains all scheduling algorithm implementations:
- FCFS  : First-Come, First-Served
- SPT   : Shortest Processing Time
- EDD   : Earliest Due Date
- WSPT  : Weighted Shortest Processing Time

All algorithms delegate to schedule_fcfs() as the constraint-aware
base executor. The sorting order of jobs passed to it defines the
algorithm behaviour.
"""
from models import Job, Machine
from core.logger import logger


def schedule_fcfs(jobs: list[Job], machines: list[Machine], setup_time: int) -> list:
    """
    Schedules jobs using the First-Come, First-Served (FCFS) algorithm.

    This is the core scheduling engine that also handles all constraints:
    - Setup times between different jobs on the same machine
    - Machine unavailability / maintenance windows
    - Precedence within a single job (operation ordering)

    Args:
        jobs: Ordered list of Job objects to schedule.
        machines: List of Machine objects with their availability state.
        setup_time: Time units added when a machine switches to a different job.

    Returns:
        List of tuples: (job_id, op_index, machine_id, start_time, end_time)
    """
    schedule = []
    machine_map = {m.machine_id: m for m in machines}

    for job in jobs:
        current_job_end_time = 0
        for i, operation in enumerate(job.operations):
            machine = machine_map[operation.machine_id]

            # --- Setup time ---
            setup = 0
            if machine.last_job_id is not None and machine.last_job_id != job.job_id:
                setup = setup_time

            earliest_start = max(machine.available_at + setup, current_job_end_time)

            # --- Resolve machine unavailability conflicts ---
            valid_start_time = earliest_start
            while True:
                conflict_found = False
                proposed_end_time = valid_start_time + operation.processing_time
                for down_start, down_end in machine.unavailable_periods:
                    if valid_start_time < down_end and down_start < proposed_end_time:
                        valid_start_time = down_end
                        conflict_found = True
                        break
                if not conflict_found:
                    break

            start_time = valid_start_time
            end_time = start_time + operation.processing_time

            schedule.append((job.job_id, i, machine.machine_id, start_time, end_time))

            machine.available_at = end_time
            machine.last_job_id = job.job_id
            current_job_end_time = end_time

    logger.debug(
        "FCFS scheduled {} operations for {} jobs.",
        len(schedule),
        len(jobs),
    )
    return schedule


def schedule_spt(jobs: list[Job], machines: list[Machine], setup_time: int) -> list:
    """
    Schedules jobs using Shortest Processing Time (SPT) rule.
    Jobs with the smallest total processing time run first.
    """
    sorted_jobs = sorted(jobs, key=lambda job: sum(op.processing_time for op in job.operations))
    logger.debug("SPT ordering applied to {} jobs.", len(sorted_jobs))
    return schedule_fcfs(sorted_jobs, machines, setup_time)


def schedule_edd(jobs: list[Job], machines: list[Machine], setup_time: int) -> list:
    """
    Schedules jobs using Earliest Due Date (EDD) rule.
    Jobs with the closest due dates are prioritised to minimise tardiness.
    """
    sorted_jobs = sorted(jobs, key=lambda job: job.due_date)
    logger.debug("EDD ordering applied to {} jobs.", len(sorted_jobs))
    return schedule_fcfs(sorted_jobs, machines, setup_time)


def schedule_wspt(jobs: list[Job], machines: list[Machine], setup_time: int) -> list:
    """
    Schedules jobs using Weighted Shortest Processing Time (WSPT) rule.
    Balances speed and priority: shorter/higher-priority jobs run first.
    """
    sorted_jobs = sorted(
        jobs,
        key=lambda job: sum(op.processing_time for op in job.operations) / job.priority,
    )
    logger.debug("WSPT ordering applied to {} jobs.", len(sorted_jobs))
    return schedule_fcfs(sorted_jobs, machines, setup_time)


# Convenience mapping for API and CLI usage
ALGORITHM_MAP = {
    "FCFS": schedule_fcfs,
    "SPT": schedule_spt,
    "EDD": schedule_edd,
    "WSPT": schedule_wspt,
}
