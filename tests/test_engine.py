# tests/test_engine.py
"""
Tests for scheduler/engine.py — FCFS, SPT, EDD, WSPT algorithms.
"""
import copy
import pytest
from models import Job, Operation, Machine
from scheduler.engine import (
    schedule_fcfs,
    schedule_spt,
    schedule_edd,
    schedule_wspt,
    ALGORITHM_MAP,
)


class TestFCFS:
    """Tests for the core FCFS scheduling algorithm."""

    def test_basic_schedule(self, simple_jobs, simple_machines):
        """FCFS should schedule all operations and return valid tuples."""
        schedule = schedule_fcfs(simple_jobs, simple_machines, setup_time=0)
        # 2 jobs × 2 operations each = 4 scheduled operations
        assert len(schedule) == 4
        # Each entry is (job_id, op_index, machine_id, start, end)
        for entry in schedule:
            assert len(entry) == 5
            job_id, op_idx, m_id, start, end = entry
            assert end > start, "end_time must be greater than start_time"

    def test_no_overlap_on_same_machine(self, sample_jobs, fresh_machines):
        """No two operations on the same machine should overlap in time."""
        schedule = schedule_fcfs(sample_jobs, fresh_machines, setup_time=0)
        # Group by machine
        by_machine: dict[int, list] = {}
        for op in schedule:
            m_id = op[2]
            by_machine.setdefault(m_id, []).append(op)

        for m_id, ops in by_machine.items():
            ops_sorted = sorted(ops, key=lambda x: x[3])  # sort by start_time
            for i in range(1, len(ops_sorted)):
                prev_end = ops_sorted[i - 1][4]
                curr_start = ops_sorted[i][3]
                assert curr_start >= prev_end, (
                    f"Machine {m_id}: overlap detected between ops ending at {prev_end} "
                    f"and starting at {curr_start}"
                )

    def test_setup_time_applied(self):
        """Setup time should be added when machine switches between different jobs."""
        jobs = [
            Job(1, [Operation(0, 5)], due_date=20, priority=1),
            Job(2, [Operation(0, 3)], due_date=20, priority=1),
        ]
        machines = [Machine(machine_id=0)]
        schedule = schedule_fcfs(jobs, machines, setup_time=5)

        # Job 1: M0 starts at 0, ends at 5
        # Job 2: M0 needs setup (5), so starts at 5+5=10, ends at 13
        assert schedule[0] == (1, 0, 0, 0, 5)
        assert schedule[1] == (2, 0, 0, 10, 13)

    def test_no_setup_time_same_job(self):
        """No setup time when consecutive ops on the same machine belong to the same job."""
        jobs = [
            Job(1, [Operation(0, 3), Operation(0, 4)], due_date=20, priority=1),
        ]
        machines = [Machine(machine_id=0)]
        schedule = schedule_fcfs(jobs, machines, setup_time=10)

        # Both ops for job 1 on machine 0 — no setup penalty
        assert schedule[0] == (1, 0, 0, 0, 3)
        assert schedule[1] == (1, 1, 0, 3, 7)

    def test_unavailability_pushes_start(self):
        """Operations should be pushed past machine maintenance windows."""
        jobs = [
            Job(1, [Operation(0, 5)], due_date=50, priority=1),
        ]
        machines = [Machine(machine_id=0, unavailable_periods=[(2, 10)])]
        schedule = schedule_fcfs(jobs, machines, setup_time=0)

        # Machine 0 is down 2-10, so job starts at 10
        assert schedule[0][3] >= 10, "Start should be pushed to at least 10"
        assert schedule[0] == (1, 0, 0, 10, 15)

    def test_precedence_within_job(self):
        """Operations within a job must execute in order."""
        jobs = [
            Job(1, [Operation(0, 3), Operation(1, 4), Operation(0, 2)], due_date=50, priority=1),
        ]
        machines = [Machine(machine_id=0), Machine(machine_id=1)]
        schedule = schedule_fcfs(jobs, machines, setup_time=0)

        for i in range(1, len(schedule)):
            if schedule[i][0] == schedule[i - 1][0]:  # same job
                assert schedule[i][3] >= schedule[i - 1][4], (
                    "Operation must start after previous op in same job ends"
                )


class TestSPT:
    """Tests for Shortest Processing Time ordering."""

    def test_spt_sorts_by_processing_time(self, fresh_machines):
        """SPT should schedule shortest total processing time jobs first."""
        short_job = Job(1, [Operation(0, 1)], due_date=100, priority=1)  # total=1
        long_job = Job(2, [Operation(0, 10)], due_date=100, priority=1)  # total=10
        schedule = schedule_spt([long_job, short_job], fresh_machines, setup_time=0)
        # First op should be from the shorter job
        assert schedule[0][0] == 1, "SPT should schedule the shortest job first"


class TestEDD:
    """Tests for Earliest Due Date ordering."""

    def test_edd_sorts_by_due_date(self, fresh_machines):
        """EDD should schedule earliest due date jobs first."""
        early = Job(1, [Operation(0, 5)], due_date=10, priority=1)
        late = Job(2, [Operation(0, 5)], due_date=50, priority=1)
        schedule = schedule_edd([late, early], fresh_machines, setup_time=0)
        assert schedule[0][0] == 1, "EDD should schedule the earliest due date first"


class TestWSPT:
    """Tests for Weighted Shortest Processing Time ordering."""

    def test_wspt_sorts_by_weighted_ratio(self, fresh_machines):
        """WSPT should schedule by processing_time / priority (ascending)."""
        # Job 1: total_pt=10, priority=5 → ratio=2.0
        # Job 2: total_pt=10, priority=2 → ratio=5.0
        high_prio = Job(1, [Operation(0, 10)], due_date=100, priority=5)
        low_prio = Job(2, [Operation(0, 10)], due_date=100, priority=2)
        schedule = schedule_wspt([low_prio, high_prio], fresh_machines, setup_time=0)
        assert schedule[0][0] == 1, "WSPT should schedule higher priority (lower ratio) first"


class TestAlgorithmMap:
    """Tests for the ALGORITHM_MAP registry."""

    def test_all_algorithms_present(self):
        assert set(ALGORITHM_MAP.keys()) == {"FCFS", "SPT", "EDD", "WSPT"}

    def test_map_values_are_callable(self):
        for name, fn in ALGORITHM_MAP.items():
            assert callable(fn), f"{name} is not callable"
