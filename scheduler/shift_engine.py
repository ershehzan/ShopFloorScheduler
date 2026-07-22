# scheduler/shift_engine.py
"""
Shift-aware scheduling engine for ShopFloorScheduler (Phase 5).

Extends the base FCFS engine to respect shift windows:
  - Each machine may have one or more active shift windows
  - Operations are pushed forward until they land inside a valid shift window
  - Shift windows repeat with a configurable cycle_length (default 24 time units)

Shift window format (loaded from DB or passed directly):
    {machine_id: (shift_start, shift_end, cycle_length)}

Example: machine_id="1", shift_start=6, shift_end=14, cycle_length=24
  => Machine 1 works 6-14 every 24 time-units.
  => An operation starting at t=0 would be pushed to t=6.
  => An operation at t=14 would be pushed to t=30 (6+24).
"""
from __future__ import annotations

from models import Job, Machine
from core.logger import logger


# Type alias: machine_id -> (start, end, cycle)
ShiftMap = dict[str | int, tuple[float, float, float]]


def _next_shift_start(t: float, shift_start: float, shift_end: float, cycle: float) -> float:
    """
    Given current time t, return the earliest time >= t that falls
    within a shift window [shift_start, shift_end) repeating every cycle.

    Args:
        t: Current time (absolute).
        shift_start: Start of shift within cycle (e.g. 6.0).
        shift_end: End of shift within cycle (e.g. 14.0).
        cycle: Repetition period (e.g. 24.0).

    Returns:
        Adjusted start time >= t that lies within a shift window.
    """
    # Position within the current cycle
    offset = t % cycle
    if offset < shift_start:
        # Before shift starts in this cycle: push to shift_start
        return t - offset + shift_start
    elif offset < shift_end:
        # Inside the shift: no adjustment needed
        return t
    else:
        # After shift ends: push to shift_start in the next cycle
        return t - offset + cycle + shift_start


def _adjust_for_shift(
    start: float,
    duration: float,
    shift_start: float,
    shift_end: float,
    cycle: float,
) -> float:
    """
    Repeatedly adjust start time until the entire operation [start, start+duration)
    fits inside a shift window. Handles operations that span the shift boundary.

    Returns:
        A valid start time within the shift window.
    """
    max_iters = 1000
    for _ in range(max_iters):
        # Ensure start is inside a shift window
        adjusted = _next_shift_start(start, shift_start, shift_end, cycle)
        if adjusted != start:
            start = adjusted
            continue
        # Check if the whole operation fits before shift_end
        shift_window_end = (start // cycle) * cycle + shift_end
        if start + duration <= shift_window_end:
            return start
        # Operation overflows the shift: push to next shift window
        start = (start // cycle) * cycle + cycle + shift_start
    return start  # fallback


def schedule_fcfs_with_shifts(
    jobs: list[Job],
    machines: list[Machine],
    setup_time: int,
    shift_map: ShiftMap | None = None,
) -> list:
    """
    Schedules jobs using FCFS with optional shift-window constraints.

    Args:
        jobs: Ordered list of Job objects.
        machines: List of Machine objects.
        setup_time: Extra time units when a machine switches jobs.
        shift_map: Optional mapping of machine_id -> (shift_start, shift_end, cycle_length).
                   If None or a machine is not in the map, no shift constraint is applied.

    Returns:
        List of tuples: (job_id, op_index, machine_id, start_time, end_time)
    """
    shift_map = shift_map or {}
    schedule = []
    machine_map = {m.machine_id: m for m in machines}

    for job in jobs:
        current_job_end_time = 0.0
        for i, operation in enumerate(job.operations):
            machine = machine_map[operation.machine_id]

            # --- Setup time ---
            setup = 0
            if machine.last_job_id is not None and machine.last_job_id != job.job_id:
                setup = setup_time

            earliest_start = max(machine.available_at + setup, current_job_end_time)

            # --- Resolve machine unavailability conflicts ---
            valid_start = earliest_start
            while True:
                conflict = False
                proposed_end = valid_start + operation.processing_time
                for down_start, down_end in machine.unavailable_periods:
                    if valid_start < down_end and down_start < proposed_end:
                        valid_start = down_end
                        conflict = True
                        break
                if not conflict:
                    break

            # --- Resolve shift window constraints ---
            mid = str(operation.machine_id)
            if mid in shift_map:
                s_start, s_end, cycle = shift_map[mid]
                valid_start = _adjust_for_shift(
                    valid_start, operation.processing_time, s_start, s_end, cycle
                )
                # Re-check unavailability after shift adjustment (simplified: single pass)
                proposed_end = valid_start + operation.processing_time
                for down_start, down_end in machine.unavailable_periods:
                    if valid_start < down_end and down_start < proposed_end:
                        valid_start = _adjust_for_shift(
                            down_end, operation.processing_time, s_start, s_end, cycle
                        )
                        break

            start_time = valid_start
            end_time = start_time + operation.processing_time

            schedule.append((job.job_id, i, machine.machine_id, start_time, end_time))

            machine.available_at = end_time
            machine.last_job_id = job.job_id
            current_job_end_time = end_time

    logger.debug(
        "Shift-aware FCFS scheduled {} operations for {} jobs with {} shift constraints.",
        len(schedule),
        len(jobs),
        len(shift_map),
    )
    return schedule


def load_shift_map_from_db(machine_ids: list[str | int] | None = None) -> ShiftMap:
    """
    Load active shift windows from the database.

    Args:
        machine_ids: Optional list to filter; if None, loads all active shifts.

    Returns:
        ShiftMap: {machine_id_str: (shift_start, shift_end, cycle_length)}
        Only the first active shift per machine is used.
    """
    from core.database import SessionLocal
    from core.models_db import MachineShift

    db = SessionLocal()
    try:
        query = db.query(MachineShift).filter(MachineShift.is_active == True)
        if machine_ids:
            str_ids = [str(m) for m in machine_ids]
            query = query.filter(MachineShift.machine_id.in_(str_ids))
        shifts = query.all()

        shift_map: ShiftMap = {}
        for s in shifts:
            mid = str(s.machine_id)
            if mid not in shift_map:  # first active shift wins
                shift_map[mid] = (s.shift_start, s.shift_end, s.cycle_length)
        return shift_map
    finally:
        db.close()
