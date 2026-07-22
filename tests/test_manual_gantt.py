"""
tests/test_manual_gantt.py
Phase 5: Tests for the manual Gantt editor — PATCH /api/schedule/{task_id}/manual
"""
import os
import io
import time
import json
import pytest


class TestManualGanttAPI:
    """Tests for the PATCH /api/schedule/{task_id}/manual endpoint."""

    def test_unknown_task_returns_404(self, client, auth_headers):
        resp = client.patch(
            "/api/schedule/nonexistent-task-id/manual",
            json={"schedule": [
                {"job_id": 1, "op_index": 0, "machine_id": 1, "start_time": 0.0, "end_time": 10.0}
            ]},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_invalid_schedule_end_before_start_rejected(self, client, auth_headers):
        """Operation with end_time <= start_time should return 422."""
        resp = client.patch(
            "/api/schedule/some-id/manual",
            json={"schedule": [
                {"job_id": 1, "op_index": 0, "machine_id": 1, "start_time": 10.0, "end_time": 5.0}
            ]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_empty_schedule_rejected(self, client, auth_headers):
        """Empty schedule list should be rejected."""
        resp = client.patch(
            "/api/schedule/some-id/manual",
            json={"schedule": []},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data.xlsx")),
        reason="data.xlsx not found",
    )
    def test_manual_patch_on_completed_run(self, client, auth_headers):
        """Full integration: complete a run, then PATCH it with an adjusted schedule."""
        xlsx_path = os.path.join(os.path.dirname(__file__), "..", "data.xlsx")

        # 1. Upload a run
        with open(xlsx_path, "rb") as f:
            upload_resp = client.post(
                "/api/schedule/upload",
                files={"file": ("data.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"algorithm": "FCFS", "setup_time": "0"},
                headers=auth_headers,
            )
        assert upload_resp.status_code == 202
        task_id = upload_resp.json()["task_id"]

        # 2. Wait for completion
        timeout = 20
        start = time.time()
        state = None
        while time.time() - start < timeout:
            status_resp = client.get(f"/api/schedule/status/{task_id}", headers=auth_headers)
            state = status_resp.json().get("state")
            if state in ("complete", "error"):
                break
            time.sleep(0.5)
        assert state == "complete", f"Run did not complete: {state}"

        # 3. Fetch the schedule
        result_resp = client.get(f"/api/schedule/results/{task_id}", headers=auth_headers)
        schedule = result_resp.json()["result"]["schedule"]
        assert len(schedule) > 0

        # 4. Shift all operations by +5 time units
        adjusted = [
            {
                "job_id": op["job_id"],
                "op_index": op["op_index"],
                "machine_id": op["machine_id"],
                "start_time": op["start_time"] + 5.0,
                "end_time": op["end_time"] + 5.0,
            }
            for op in schedule
        ]

        # 5. PATCH with adjusted schedule
        patch_resp = client.patch(
            f"/api/schedule/{task_id}/manual",
            json={"schedule": adjusted},
            headers=auth_headers,
        )
        assert patch_resp.status_code == 200
        result = patch_resp.json()
        assert "makespan" in result
        assert "total_tardiness" in result
        assert "conflicts" in result
        # Makespan should be 5 more than original
        original_makespan = result_resp.json()["result"]["makespan"]
        assert abs(result["makespan"] - (original_makespan + 5)) < 1.0

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data.xlsx")),
        reason="data.xlsx not found",
    )
    def test_conflict_detection(self, client, auth_headers):
        """Overlapping operations on same machine should be detected and reported."""
        xlsx_path = os.path.join(os.path.dirname(__file__), "..", "data.xlsx")

        # 1. Upload + complete a run
        with open(xlsx_path, "rb") as f:
            upload_resp = client.post(
                "/api/schedule/upload",
                files={"file": ("data.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"algorithm": "FCFS", "setup_time": "0"},
                headers=auth_headers,
            )
        task_id = upload_resp.json()["task_id"]

        timeout = 20
        start = time.time()
        while time.time() - start < timeout:
            state = client.get(f"/api/schedule/status/{task_id}", headers=auth_headers).json().get("state")
            if state in ("complete", "error"):
                break
            time.sleep(0.5)

        # 2. Build a deliberately overlapping schedule
        result_resp = client.get(f"/api/schedule/results/{task_id}", headers=auth_headers)
        schedule = result_resp.json()["result"]["schedule"]

        # Force an overlap: duplicate op 0 with same machine, overlapping times
        op0 = schedule[0]
        conflicting = [
            op0,
            {
                "job_id": 999,
                "op_index": 0,
                "machine_id": op0["machine_id"],
                "start_time": op0["start_time"],
                "end_time": op0["end_time"] + 5.0,
            },
        ]

        patch_resp = client.patch(
            f"/api/schedule/{task_id}/manual",
            json={"schedule": conflicting},
            headers=auth_headers,
        )
        assert patch_resp.status_code == 200
        # Conflicts should be reported
        assert len(patch_resp.json()["conflicts"]) > 0

    def test_manual_patch_requires_auth(self, client):
        resp = client.patch(
            "/api/schedule/some-id/manual",
            json={"schedule": [
                {"job_id": 1, "op_index": 0, "machine_id": 1, "start_time": 0.0, "end_time": 10.0}
            ]},
        )
        assert resp.status_code == 401
