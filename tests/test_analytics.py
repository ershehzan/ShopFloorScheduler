# tests/test_analytics.py
"""
Unit and integration tests for Phase 3 Analytics Dashboard API.
"""
import json
import datetime
import pytest
from core.models_db import ScheduleRun, User, JobRecord


@pytest.fixture
def seeded_runs(test_db):
    """Seed the database with mock completed runs associated with the test user."""
    # Find or create test user
    user = test_db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=False,
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

    # Seed runs
    now = datetime.datetime.utcnow()
    run1 = ScheduleRun(
        task_id="task-uuid-1",
        status="complete",
        algorithm="GA",
        makespan=150.0,
        total_tardiness=20.0,
        avg_flow_time=12.0,
        on_time_percent=80.0,
        user_id=user.id,
        created_at=now - datetime.timedelta(minutes=10),
        result_json=json.dumps({
            "makespan": 150,
            "total_tardiness": 20,
            "avg_flow_time": 12,
            "on_time_percent": 80,
            "algorithm": "GA",
            "utilization": [
                {"machine_id": 1, "utilization": 0.85},
                {"machine_id": 2, "utilization": 0.70}
            ]
        })
    )

    run2 = ScheduleRun(
        task_id="task-uuid-2",
        status="complete",
        algorithm="FCFS",
        makespan=200.0,
        total_tardiness=50.0,
        avg_flow_time=22.0,
        on_time_percent=40.0,
        user_id=user.id,
        created_at=now,
        result_json=json.dumps({
            "makespan": 200,
            "total_tardiness": 50,
            "avg_flow_time": 22,
            "on_time_percent": 40,
            "algorithm": "FCFS",
            "utilization": [
                {"machine_id": 1, "utilization": 0.90},
                {"machine_id": 2, "utilization": 0.50}
            ]
        })
    )

    test_db.add(run1)
    test_db.add(run2)
    test_db.commit()

    # Seed job records for tardiness distribution
    test_db.add(JobRecord(run_id=run1.id, job_id="1", tardiness=5.0))
    test_db.add(JobRecord(run_id=run1.id, job_id="2", tardiness=0.0))
    test_db.add(JobRecord(run_id=run2.id, job_id="1", tardiness=15.0))
    test_db.add(JobRecord(run_id=run2.id, job_id="2", tardiness=35.0))
    test_db.commit()

    return user.id


def test_analytics_summary(client, auth_headers, seeded_runs):
    res = client.get("/api/analytics/summary", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_runs"] == 2
    assert data["avg_makespan"] == 175.0
    assert data["avg_tardiness"] == 35.0
    assert data["best_makespan"] == 150.0
    assert data["best_algorithm"] == "GA"


def test_analytics_trends(client, auth_headers, seeded_runs):
    res = client.get("/api/analytics/trends", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["points"]) == 2
    assert data["total"] == 2
    task_ids = {pt["task_id"] for pt in data["points"]}
    assert task_ids == {"task-uuid-1", "task-uuid-2"}



def test_utilization_heatmap(client, auth_headers, seeded_runs):
    res = client.get("/api/analytics/utilization-heatmap", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["cells"]) == 4
    assert data["machines"] == [1, 2]
    assert "task-uuid-1" in data["runs"]


def test_algorithm_comparison(client, auth_headers, seeded_runs):
    res = client.get("/api/analytics/algorithm-comparison", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["algorithms"]) == 2
    stats = {item["algorithm"]: item for item in data["algorithms"]}
    assert "GA" in stats
    assert "FCFS" in stats
    assert stats["GA"]["run_count"] == 1
    assert stats["GA"]["best_makespan"] == 150.0


def test_tardiness_distribution(client, auth_headers, seeded_runs):
    res = client.get("/api/analytics/tardiness-distribution?bucket_size=10", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_jobs"] == 4
    # tardiness values: [5.0, 0.0, 15.0, 35.0]
    # buckets: '0-10' (counts 0.0, 5.0 -> 2), '10-20' (counts 15.0 -> 1), '20-30' (counts -> 0), '30-40' (counts 35.0 -> 1)
    # let's assert count values are present
    assert sum(data["counts"]) == 4
