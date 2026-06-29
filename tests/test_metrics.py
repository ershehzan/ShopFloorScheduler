# tests/test_metrics.py
"""
Tests for scheduler/metrics.py — KPI calculation functions.
"""
import pytest
from models import Job, Operation, Machine
from scheduler.metrics import (
    calculate_makespan,
    calculate_tardiness,
    calculate_utilization,
    calculate_avg_flow_time,
    calculate_on_time_percent,
    build_full_metrics,
)


class TestMakespan:
    def test_basic(self, sample_schedule):
        """Makespan is the maximum end time across all operations."""
        assert calculate_makespan(sample_schedule) == 8

    def test_empty(self):
        """Empty schedule should return makespan of 0."""
        assert calculate_makespan([]) == 0

    def test_single_operation(self):
        schedule = [(1, 0, 0, 0, 42)]
        assert calculate_makespan(schedule) == 42


class TestTardiness:
    def test_all_on_time(self):
        """No tardiness when all jobs finish before due date."""
        jobs = [
            Job(1, [Operation(0, 5)], due_date=100, priority=1),
            Job(2, [Operation(0, 3)], due_date=100, priority=1),
        ]
        schedule = [(1, 0, 0, 0, 5), (2, 0, 0, 5, 8)]
        assert calculate_tardiness(schedule, jobs) == 0

    def test_some_late(self):
        """Tardiness should be sum of max(0, completion - due_date)."""
        jobs = [
            Job(1, [Operation(0, 5)], due_date=3, priority=1),   # finishes at 5, due 3 → tard=2
            Job(2, [Operation(0, 3)], due_date=100, priority=1),  # finishes at 8, due 100 → tard=0
        ]
        schedule = [(1, 0, 0, 0, 5), (2, 0, 0, 5, 8)]
        assert calculate_tardiness(schedule, jobs) == 2

    def test_all_late(self):
        """All jobs late — sum all tardiness values."""
        jobs = [
            Job(1, [Operation(0, 5)], due_date=1, priority=1),   # finishes 5, due 1 → 4
            Job(2, [Operation(0, 3)], due_date=2, priority=1),   # finishes 8, due 2 → 6
        ]
        schedule = [(1, 0, 0, 0, 5), (2, 0, 0, 5, 8)]
        assert calculate_tardiness(schedule, jobs) == 10

    def test_empty_schedule(self):
        jobs = [Job(1, [Operation(0, 5)], due_date=10, priority=1)]
        assert calculate_tardiness([], jobs) == 0


class TestUtilization:
    def test_basic(self):
        """Utilization = busy_time / makespan per machine."""
        machines = [Machine(0), Machine(1)]
        schedule = [
            (1, 0, 0, 0, 5),   # M0 busy 5 units
            (1, 1, 1, 5, 8),   # M1 busy 3 units
        ]
        util = calculate_utilization(schedule, machines)
        # makespan = 8
        assert util[0] == round(5 / 8, 4)
        assert util[1] == round(3 / 8, 4)

    def test_empty_schedule(self):
        machines = [Machine(0)]
        util = calculate_utilization([], machines)
        assert util[0] == 0.0

    def test_full_utilization(self):
        """Machine busy the entire makespan → utilization = 1.0."""
        machines = [Machine(0)]
        schedule = [(1, 0, 0, 0, 10)]
        util = calculate_utilization(schedule, machines)
        assert util[0] == 1.0


class TestAvgFlowTime:
    def test_basic(self, sample_schedule):
        """Average flow time = mean of job completion times."""
        from models import Job, Operation
        jobs = [
            Job(1, [Operation(0, 5), Operation(1, 3)], due_date=20, priority=1),
            Job(2, [Operation(1, 4), Operation(0, 2)], due_date=15, priority=2),
        ]
        # Job 1 finishes at 8, Job 2 finishes at 7 → mean = 7.5
        result = calculate_avg_flow_time(sample_schedule, jobs)
        assert result == 7.5

    def test_empty(self):
        assert calculate_avg_flow_time([], []) == 0.0


class TestOnTimePercent:
    def test_all_on_time(self):
        jobs = [
            Job(1, [Operation(0, 5)], due_date=10, priority=1),
            Job(2, [Operation(0, 3)], due_date=20, priority=1),
        ]
        schedule = [(1, 0, 0, 0, 5), (2, 0, 0, 5, 8)]
        assert calculate_on_time_percent(schedule, jobs) == 100.0

    def test_half_on_time(self):
        jobs = [
            Job(1, [Operation(0, 5)], due_date=3, priority=1),   # late
            Job(2, [Operation(0, 3)], due_date=20, priority=1),  # on time
        ]
        schedule = [(1, 0, 0, 0, 5), (2, 0, 0, 5, 8)]
        assert calculate_on_time_percent(schedule, jobs) == 50.0

    def test_empty(self):
        assert calculate_on_time_percent([], []) == 0.0


class TestBuildFullMetrics:
    def test_returns_all_keys(self, sample_schedule, simple_jobs, simple_machines):
        result = build_full_metrics(sample_schedule, simple_jobs, simple_machines)
        assert "makespan" in result
        assert "total_tardiness" in result
        assert "avg_flow_time" in result
        assert "on_time_percent" in result
        assert "utilization" in result
        assert isinstance(result["utilization"], dict)
