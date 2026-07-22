"""
tests/test_shifts.py
Phase 5: Tests for shift-constrained scheduling and the shifts REST API.
"""
import pytest
from models import Job, Machine, Operation


# ---------------------------------------------------------------------------
# Unit tests: shift engine
# ---------------------------------------------------------------------------

class TestShiftHelpers:
    def test_next_shift_start_inside_window(self):
        """Time already inside shift window should not be adjusted."""
        from scheduler.shift_engine import _next_shift_start
        assert _next_shift_start(8.0, 6.0, 14.0, 24.0) == 8.0

    def test_next_shift_start_before_window(self):
        """Time before shift should be pushed to shift start."""
        from scheduler.shift_engine import _next_shift_start
        result = _next_shift_start(2.0, 6.0, 14.0, 24.0)
        assert result == 6.0

    def test_next_shift_start_after_window(self):
        """Time after shift end should push to next cycle's shift start."""
        from scheduler.shift_engine import _next_shift_start
        result = _next_shift_start(15.0, 6.0, 14.0, 24.0)
        assert result == 30.0  # 0 + 24 + 6

    def test_next_shift_start_at_boundary(self):
        """Time exactly at shift end should push to next cycle."""
        from scheduler.shift_engine import _next_shift_start
        result = _next_shift_start(14.0, 6.0, 14.0, 24.0)
        assert result == 30.0

    def test_adjust_for_shift_fits_in_window(self):
        """Short op that fits inside shift should not move."""
        from scheduler.shift_engine import _adjust_for_shift
        result = _adjust_for_shift(7.0, 4.0, 6.0, 14.0, 24.0)
        assert result == 7.0  # 7 + 4 = 11 <= 14

    def test_adjust_for_shift_overflow(self):
        """Op that overflows shift end should move to next cycle."""
        from scheduler.shift_engine import _adjust_for_shift
        result = _adjust_for_shift(12.0, 5.0, 6.0, 14.0, 24.0)
        assert result == 30.0  # 12+5=17 > 14, next cycle start = 24+6


class TestShiftScheduler:
    def test_operation_pushed_into_shift_window(self):
        """An operation starting outside a shift should be pushed into it."""
        from scheduler.shift_engine import schedule_fcfs_with_shifts

        jobs = [Job(job_id=1, due_date=50, priority=1, operations=[
            Operation(machine_id=1, processing_time=4),
        ])]
        machines = [Machine(machine_id=1, unavailable_periods=[])]
        # Machine 1: shift 8-16, starting at t=0 should push to t=8
        shift_map = {"1": (8.0, 16.0, 24.0)}
        schedule = schedule_fcfs_with_shifts(jobs, machines, setup_time=0, shift_map=shift_map)

        assert len(schedule) == 1
        _, _, _, start, end = schedule[0]
        assert start >= 8.0
        assert end <= 16.0

    def test_no_shifts_behaves_like_fcfs(self):
        """With no shifts, result should match plain FCFS."""
        from scheduler.shift_engine import schedule_fcfs_with_shifts
        from scheduler.engine import schedule_fcfs

        jobs = [
            Job(job_id=1, due_date=50, priority=1, operations=[Operation(machine_id=1, processing_time=5)]),
            Job(job_id=2, due_date=50, priority=1, operations=[Operation(machine_id=1, processing_time=3)]),
        ]
        machines_a = [Machine(machine_id=1, unavailable_periods=[])]
        machines_b = [Machine(machine_id=1, unavailable_periods=[])]

        shift_sched = schedule_fcfs_with_shifts(jobs, machines_a, setup_time=0, shift_map=None)
        base_sched = schedule_fcfs(jobs, machines_b, setup_time=0)

        # Makespans should be equal
        assert max(s[4] for s in shift_sched) == max(s[4] for s in base_sched)

    def test_no_operation_overlap_with_shifts(self):
        """Shift-scheduled operations on the same machine should not overlap."""
        from scheduler.shift_engine import schedule_fcfs_with_shifts
        from collections import defaultdict

        jobs = [
            Job(job_id=i, due_date=200, priority=1, operations=[Operation(machine_id=1, processing_time=3)])
            for i in range(1, 5)
        ]
        machines = [Machine(machine_id=1, unavailable_periods=[])]
        shift_map = {"1": (6.0, 14.0, 24.0)}
        schedule = schedule_fcfs_with_shifts(jobs, machines, setup_time=0, shift_map=shift_map)

        by_machine = defaultdict(list)
        for _, _, mid, st, et in schedule:
            by_machine[mid].append((st, et))
        for mid, intervals in by_machine.items():
            intervals.sort()
            for i in range(1, len(intervals)):
                assert intervals[i][0] >= intervals[i - 1][1], f"Overlap on machine {mid}"

    def test_all_operations_within_shift(self):
        """All operations must start and end within a shift window."""
        from scheduler.shift_engine import schedule_fcfs_with_shifts

        jobs = [
            Job(job_id=i, due_date=500, priority=1, operations=[Operation(machine_id=1, processing_time=2)])
            for i in range(1, 6)
        ]
        machines = [Machine(machine_id=1, unavailable_periods=[])]
        shift_map = {"1": (6.0, 14.0, 24.0)}
        schedule = schedule_fcfs_with_shifts(jobs, machines, setup_time=0, shift_map=shift_map)

        for _, _, _, start, end in schedule:
            # Compute which cycle we're in
            cycle = 24.0
            offset_start = start % cycle
            offset_end = (end - 0.001) % cycle  # end exclusive
            assert offset_start >= 6.0 or end - start == 0, f"Op starts at {start} outside shift"
            assert offset_end < 14.0 or offset_end >= 6.0, f"Op ends at {end} outside shift"


# ---------------------------------------------------------------------------
# API tests: shifts CRUD
# ---------------------------------------------------------------------------

class TestShiftsAPI:
    def test_list_shifts_empty(self, client, auth_headers):
        resp = client.get("/api/shifts", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_shift(self, client, auth_headers):
        resp = client.post("/api/shifts", json={
            "machine_id": "1",
            "shift_name": "DAY",
            "shift_start": 6.0,
            "shift_end": 14.0,
            "cycle_length": 24.0,
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["machine_id"] == "1"
        assert data["shift_name"] == "DAY"
        assert data["shift_start"] == 6.0
        assert data["shift_end"] == 14.0

    def test_create_shift_invalid_end_before_start(self, client, auth_headers):
        resp = client.post("/api/shifts", json={
            "machine_id": "2",
            "shift_name": "NIGHT",
            "shift_start": 14.0,
            "shift_end": 6.0,  # invalid: end < start
            "cycle_length": 24.0,
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_upsert_existing_shift(self, client, auth_headers):
        """Creating same machine+shift_name twice should update, not duplicate."""
        payload = {
            "machine_id": "3",
            "shift_name": "EVENING",
            "shift_start": 14.0,
            "shift_end": 22.0,
            "cycle_length": 24.0,
            "is_active": True,
        }
        resp1 = client.post("/api/shifts", json=payload, headers=auth_headers)
        assert resp1.status_code == 201

        payload["shift_start"] = 15.0  # update
        resp2 = client.post("/api/shifts", json=payload, headers=auth_headers)
        assert resp2.status_code == 201
        assert resp2.json()["shift_start"] == 15.0

        # Verify only one entry exists
        list_resp = client.get("/api/shifts/machine/3", headers=auth_headers)
        assert len(list_resp.json()) == 1

    def test_delete_shift(self, client, auth_headers):
        create_resp = client.post("/api/shifts", json={
            "machine_id": "4",
            "shift_name": "NIGHT",
            "shift_start": 22.0,
            "shift_end": 30.0,
            "cycle_length": 24.0,
            "is_active": True,
        }, headers=auth_headers)
        shift_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api/shifts/{shift_id}", headers=auth_headers)
        assert del_resp.status_code == 204

        list_resp = client.get("/api/shifts/machine/4", headers=auth_headers)
        assert all(s["id"] != shift_id for s in list_resp.json())

    def test_update_shift(self, client, auth_headers):
        create_resp = client.post("/api/shifts", json={
            "machine_id": "5",
            "shift_name": "DAY",
            "shift_start": 6.0,
            "shift_end": 14.0,
            "cycle_length": 24.0,
            "is_active": True,
        }, headers=auth_headers)
        shift_id = create_resp.json()["id"]

        update_resp = client.put(f"/api/shifts/{shift_id}", json={
            "machine_id": "5",
            "shift_name": "DAY",
            "shift_start": 7.0,
            "shift_end": 15.0,
            "cycle_length": 24.0,
            "is_active": True,
        }, headers=auth_headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["shift_start"] == 7.0

    def test_get_shifts_requires_auth(self, client):
        resp = client.get("/api/shifts")
        assert resp.status_code == 401
