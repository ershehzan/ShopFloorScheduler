# scheduler/rescheduler.py
"""
Dynamic rescheduling logic for ShopFloorScheduler (Phase 3).

Provides two rescheduling strategies:
  1. Machine breakdown — removes affected operations and reschedules remaining work
  2. Rush order injection — inserts a high-priority job into an existing schedule

Both functions reuse the FCFS constraint-aware engine from scheduler/engine.py
to ensure all scheduling rules (setup times, unavailability, precedence) are respected.
"""
import copy
from typing import Optional

from models import Job, Operation, Machine
from scheduler.engine import schedule_fcfs
from scheduler.metrics import build_full_metrics
from core.logger import logger


def reschedule_after_breakdown(
    original_schedule: list,
    broken_machine_id: int,
    downtime_start: int,
    downtime_end: int,
    jobs: list[Job],
    machines: list[Machine],
    setup_time: int,
) -> list:
    """
    Reschedule after a machine breakdown.

    Strategy:
      1. Add the new downtime window to the broken machine's unavailable_periods.
      2. Identify which operations in the original schedule are affected
         (they overlap with the downtime on the broken machine).
      3. Re-run the scheduling algorithm with the updated machine constraints.
         Completed operations (end_time <= downtime_start) are preserved.
         All others are rescheduled.

    Args:
        original_schedule: The current schedule list of tuples.
        broken_machine_id: ID of the machine that broke down.
        downtime_start: When the breakdown starts.
        downtime_end: When the machine is expected back online.
        jobs: Full list of Job objects.
        machines: Full list of Machine objects (will be deep-copied).
        setup_time: Setup time between different jobs.

    Returns:
        New schedule list incorporating the breakdown constraint.
    """
    logger.info(
        "Rescheduling after breakdown: Machine {} down from {} to {}",
        broken_machine_id, downtime_start, downtime_end,
    )

    # Deep copy machines to avoid mutating originals
    machines_copy = copy.deepcopy(machines)

    # Add the breakdown window to the machine's unavailable periods
    for m in machines_copy:
        if m.machine_id == broken_machine_id:
            m.unavailable_periods.append((downtime_start, downtime_end))
            # Sort periods to maintain order
            m.unavailable_periods.sort(key=lambda x: x[0])
            break

    # Separate completed vs. in-progress/future operations
    completed_ops = []
    affected_job_ids = set()

    for op in original_schedule:
        job_id, op_index, machine_id, start_time, end_time = op
        if end_time <= downtime_start:
            # Already completed before breakdown — keep as-is
            completed_ops.append(op)
        else:
            # Needs rescheduling
            affected_job_ids.add(job_id)

    # If no operations are affected, return the original schedule unchanged
    if not affected_job_ids:
        logger.info("No operations affected by breakdown. Schedule unchanged.")
        return original_schedule

    # Determine which jobs need rescheduling
    # For affected jobs, figure out which operations completed vs. need redo
    job_completed_ops: dict[int, set[int]] = {}
    for op in completed_ops:
        jid = op[0]
        if jid not in job_completed_ops:
            job_completed_ops[jid] = set()
        job_completed_ops[jid].add(op[1])  # op_index

    # Build jobs for rescheduling: only include operations that weren't completed
    reschedule_jobs = []
    for job in jobs:
        if job.job_id in affected_job_ids:
            completed_indices = job_completed_ops.get(job.job_id, set())
            remaining_ops = [
                op for i, op in enumerate(job.operations)
                if i not in completed_indices
            ]
            if remaining_ops:
                reschedule_job = Job(
                    job_id=job.job_id,
                    operations=remaining_ops,
                    due_date=job.due_date,
                    priority=job.priority,
                )
                reschedule_jobs.append(reschedule_job)

    if not reschedule_jobs:
        logger.info("All affected operations were already completed.")
        return completed_ops

    # Reset machine state for rescheduling
    # Set machine availability based on completed operations
    for m in machines_copy:
        m.available_at = 0
        m.last_job_id = None

    for op in completed_ops:
        _, _, machine_id, _, end_time = op
        for m in machines_copy:
            if m.machine_id == machine_id:
                m.available_at = max(m.available_at, end_time)
                m.last_job_id = op[0]  # job_id

    # Reschedule remaining work
    new_schedule = schedule_fcfs(reschedule_jobs, machines_copy, setup_time)

    # Combine completed + rescheduled
    final_schedule = completed_ops + new_schedule

    logger.info(
        "Rescheduling complete: {} completed + {} rescheduled = {} total ops",
        len(completed_ops), len(new_schedule), len(final_schedule),
    )
    return final_schedule


def insert_rush_order(
    original_schedule: list,
    rush_job: Job,
    jobs: list[Job],
    machines: list[Machine],
    setup_time: int,
    current_time: int = 0,
) -> list:
    """
    Insert a rush order into an existing schedule.

    Strategy:
      1. All operations that have already completed (end_time <= current_time) are frozen.
      2. The rush job is added to the front of the remaining job queue (highest priority).
      3. The entire remaining schedule is regenerated with the rush job included.

    Args:
        original_schedule: The current schedule list of tuples.
        rush_job: The high-priority Job to insert.
        jobs: Original list of Job objects.
        machines: List of Machine objects (will be deep-copied).
        setup_time: Setup time between different jobs.
        current_time: The current time point (operations ending before this are frozen).

    Returns:
        New schedule list with the rush job inserted.
    """
    logger.info(
        "Inserting rush order: Job {} (due={}, priority={}) at current_time={}",
        rush_job.job_id, rush_job.due_date, rush_job.priority, current_time,
    )

    machines_copy = copy.deepcopy(machines)

    # Separate frozen (completed) vs. future operations
    frozen_ops = []
    future_job_ids = set()

    for op in original_schedule:
        job_id, op_index, machine_id, start_time, end_time = op
        if end_time <= current_time:
            frozen_ops.append(op)
        else:
            future_job_ids.add(job_id)

    # Determine which jobs need to be rescheduled
    # Include all original jobs that have future work, plus the rush job
    reschedule_jobs = []

    # Rush job goes first (highest priority)
    reschedule_jobs.append(rush_job)

    # Add remaining original jobs, sorted by priority descending
    for job in sorted(jobs, key=lambda j: -j.priority):
        if job.job_id in future_job_ids and job.job_id != rush_job.job_id:
            # Figure out which operations were already completed
            completed_indices = set()
            for fop in frozen_ops:
                if fop[0] == job.job_id:
                    completed_indices.add(fop[1])

            remaining_ops = [
                op for i, op in enumerate(job.operations)
                if i not in completed_indices
            ]
            if remaining_ops:
                reschedule_jobs.append(Job(
                    job_id=job.job_id,
                    operations=remaining_ops,
                    due_date=job.due_date,
                    priority=job.priority,
                ))

    # Also include jobs that had no future operations but were in original list
    # (they're fully completed — nothing to reschedule)

    # Reset machine state based on frozen operations
    for m in machines_copy:
        m.available_at = max(current_time, 0)
        m.last_job_id = None

    for op in frozen_ops:
        _, _, machine_id, _, end_time = op
        for m in machines_copy:
            if m.machine_id == machine_id:
                m.available_at = max(m.available_at, end_time)
                m.last_job_id = op[0]

    # Reschedule with rush job at the front
    new_schedule = schedule_fcfs(reschedule_jobs, machines_copy, setup_time)

    final_schedule = frozen_ops + new_schedule

    logger.info(
        "Rush order inserted: {} frozen + {} rescheduled = {} total ops",
        len(frozen_ops), len(new_schedule), len(final_schedule),
    )
    return final_schedule
