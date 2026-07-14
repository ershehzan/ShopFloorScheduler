# tests/test_compare.py
"""
Unit and integration tests for Phase 4 Comparative Optimization API endpoints.
"""
import io
import os
import time
import json
import pytest
from core.models_db import ScheduleRun

class TestCompareAPI:
    def test_rejects_non_excel_file(self, client, auth_headers):
        """POST /api/schedule/compare with a .txt file should return 400."""
        fake_file = io.BytesIO(b"not an excel file")
        response = client.post(
            "/api/schedule/compare",
            files={"file": ("test.txt", fake_file, "text/plain")},
            data={"algorithms": "FCFS,SPT", "setup_time": "2"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Excel" in response.json()["detail"]

    def test_rejects_invalid_algorithm(self, client, auth_headers):
        """POST /api/schedule/compare with an unknown algorithm should return 422."""
        fake_file = io.BytesIO(b"fake excel data")
        response = client.post(
            "/api/schedule/compare",
            files={"file": ("test.xlsx", fake_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"algorithms": "FCFS,INVALID", "setup_time": "2"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data.xlsx")),
        reason="data.xlsx not found",
    )
    def test_compare_valid_file_workflow(self, client, auth_headers, test_db):
        """Full end-to-end integration flow of uploading, polling, and retrieving comparison results."""
        xlsx_path = os.path.join(os.path.dirname(__file__), "..", "data.xlsx")
        
        # 1. Start comparison
        with open(xlsx_path, "rb") as f:
            response = client.post(
                "/api/schedule/compare",
                files={"file": ("data.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"algorithms": "FCFS,SPT", "setup_time": "2"},
                headers=auth_headers,
            )
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        task_id = data["task_id"]

        # 2. Poll status until complete or error (with 15s timeout)
        timeout = 15
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < timeout:
            status_resp = client.get(f"/api/schedule/compare/status/{task_id}", headers=auth_headers)
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert status_data["task_id"] == task_id
            
            if status_data["state"] == "complete":
                completed = True
                assert status_data["results"] is not None
                assert len(status_data["results"]) == 2
                
                # Check metrics structure
                for run_res in status_data["results"]:
                    assert "algorithm" in run_res
                    assert run_res["algorithm"] in ["FCFS", "SPT"]
                    assert "makespan" in run_res
                    assert "total_tardiness" in run_res
                    assert "avg_flow_time" in run_res
                    assert "on_time_percent" in run_res
                    assert "schedule" in run_res
                    assert len(run_res["schedule"]) > 0
                break
            elif status_data["state"] == "error":
                pytest.fail(f"Task ended with error: {status_data['message']}")
            time.sleep(0.5)

        assert completed, f"Comparison task {task_id} did not complete within timeout."

        # 3. Fetch explicit results endpoint
        results_resp = client.get(f"/api/schedule/compare/results/{task_id}", headers=auth_headers)
        assert results_resp.status_code == 200
        results_data = results_resp.json()
        assert results_data["state"] == "complete"
        assert len(results_data["results"]) == 2

    def test_unknown_task_returns_404(self, client, auth_headers):
        """Poll status for an unknown task ID should return 404."""
        response = client.get("/api/schedule/compare/status/nonexistent-uuid", headers=auth_headers)
        assert response.status_code == 404

        response = client.get("/api/schedule/compare/results/nonexistent-uuid", headers=auth_headers)
        assert response.status_code == 404
