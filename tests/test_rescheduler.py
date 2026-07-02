# tests/test_rescheduler.py
"""
Unit and integration tests for Phase 3 Dynamic Rescheduling logic and router.
"""
import json
import pytest
from models import Job, Operation, Machine
from scheduler.rescheduler import reschedule_after_breakdown, insert_rush_order
from core.models_db import ScheduleRun, User


def test_reschedule_after_breakdown_unit():
    # 2 machines, 2 jobs
    # Job 0: M0(3) -> M1(4)
    # Job 1: M1(2) -> M0(3)
    machines = [Machine(0), Machine(1)]
    jobs = [
        Job(0, [Operation(0, 3), Operation(1, 4)], due_date=10, priority=2),
        Job(1, [Operation(1, 2), Operation(0, 3)], due_date=15, priority=1),
    ]
    
    # Original schedule FCFS:
    # Job 0 Op 0: M0 [0, 3]
    # Job 0 Op 1: M1 [3, 7]
    # Job 1 Op 0: M1 [0, 2]
    # Job 1 Op 1: M0 [3, 6] (assuming setup time = 0 for simple test)
    original_schedule = [
        (0, 0, 0, 0, 3),
        (1, 0, 1, 0, 2),
        (0, 1, 1, 3, 7),
        (1, 1, 0, 3, 6),
    ]
    
    # Machine 1 breakdown from 2 to 6
    new_schedule = reschedule_after_breakdown(
        original_schedule=original_schedule,
        broken_machine_id=1,
        downtime_start=2,
        downtime_end=6,
        jobs=jobs,
        machines=machines,
        setup_time=0,
    )
    
    # Completed before downtime_start (2):
    # Job 1 Op 0 completes at 2, so it should be preserved
    assert (1, 0, 1, 0, 2) in new_schedule
    
    # Needs rescheduling: Job 0 Op 1 on M1. It should start at or after 6 (downtime end)
    for op in new_schedule:
        if op[0] == 0 and op[1] == 1:
            assert op[2] == 1
            assert op[3] >= 6


def test_insert_rush_order_unit():
    machines = [Machine(0), Machine(1)]
    jobs = [
        Job(0, [Operation(0, 3), Operation(1, 4)], due_date=10, priority=1),
    ]
    original_schedule = [
        (0, 0, 0, 0, 3),
        (0, 1, 1, 3, 7),
    ]
    
    # Insert rush job at current_time = 0
    rush_job = Job(99, [Operation(0, 2)], due_date=5, priority=10)
    
    new_schedule = insert_rush_order(
        original_schedule=original_schedule,
        rush_job=rush_job,
        jobs=jobs,
        machines=machines,
        setup_time=0,
        current_time=0,
    )
    
    # Rush job (99) should complete first since it has highest priority
    rush_op = [op for op in new_schedule if op[0] == 99][0]
    assert rush_op[2] == 0
    assert rush_op[3] == 0
    assert rush_op[4] == 2


@pytest.fixture
def mock_completed_run(test_db):
    """Seed the database with a completed run to test rescheduling routes."""
    # Find test user
    user = test_db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(email="test@example.com", username="testuser", hashed_password="pw", is_active=True)
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

    run = ScheduleRun(
        task_id="original-task-uuid",
        status="complete",
        algorithm="FCFS",
        file_name="data.xlsx",
        makespan=15.0,
        total_tardiness=0.0,
        user_id=user.id,
        result_json=json.dumps({
            "makespan": 15,
            "total_tardiness": 0,
            "algorithm": "FCFS",
            "schedule": [
                {"job_id": 0, "op_index": 0, "machine_id": 0, "start_time": 0, "end_time": 3},
                {"job_id": 0, "op_index": 1, "machine_id": 1, "start_time": 3, "end_time": 7}
            ]
        })
    )
    test_db.add(run)
    test_db.commit()
    test_db.refresh(run)
    return run


def test_api_reschedule_breakdown(client, auth_headers, mock_completed_run):
    payload = {
        "task_id": mock_completed_run.task_id,
        "machine_id": 1,
        "downtime_start": 2,
        "downtime_end": 6
    }
    # Mock excel file existence by copying data.xlsx
    import os
    import shutil
    os.makedirs("uploads", exist_ok=True)
    filepath = f"uploads/{mock_completed_run.task_id}.xlsx"
    shutil.copy("data.xlsx", filepath)

    try:
        res = client.post("/api/reschedule/breakdown", json=payload, headers=auth_headers)
        # Should return 202 with rescheduled task_id
        assert res.status_code == 202
        data = res.json()
        assert "task_id" in data
        assert "status_url" in data
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


def test_api_reschedule_rush_order(client, auth_headers, mock_completed_run):
    payload = {
        "task_id": mock_completed_run.task_id,
        "rush_job": {
            "job_id": 99,
            "operations": [
                {"machine_id": 0, "processing_time": 2}
            ],
            "due_date": 5,
            "priority": 10
        }
    }
    # Mock excel file existence by copying data.xlsx
    import os
    import shutil
    os.makedirs("uploads", exist_ok=True)
    filepath = f"uploads/{mock_completed_run.task_id}.xlsx"
    shutil.copy("data.xlsx", filepath)

    try:
        res = client.post("/api/reschedule/rush-order", json=payload, headers=auth_headers)
        assert res.status_code == 202
        data = res.json()
        assert "task_id" in data
        assert "status_url" in data
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

