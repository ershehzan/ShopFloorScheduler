# tests/test_api.py
"""
Integration tests for the FastAPI application endpoints.

Uses FastAPI's TestClient with an in-memory SQLite database
so tests are isolated from the production shopfloor.db.
"""
import io
import os
import pytest


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestUploadEndpoint:
    def test_rejects_non_excel_file(self, client, auth_headers):
        """POST with a .txt file should return 400."""
        fake_file = io.BytesIO(b"not an excel file")
        response = client.post(
            "/api/schedule/upload",
            files={"file": ("test.txt", fake_file, "text/plain")},
            data={"algorithm": "FCFS"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Excel" in response.json()["detail"]

    def test_rejects_invalid_algorithm(self, client, auth_headers):
        """POST with an unknown algorithm should return 422."""
        fake_file = io.BytesIO(b"fake excel data")
        response = client.post(
            "/api/schedule/upload",
            files={"file": ("test.xlsx", fake_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"algorithm": "INVALID_ALGO"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "data.xlsx")),
        reason="data.xlsx not found",
    )
    def test_upload_valid_file_returns_202(self, client, auth_headers):
        """POST with a real Excel file should return 202 with a task_id."""
        xlsx_path = os.path.join(os.path.dirname(__file__), "..", "data.xlsx")
        with open(xlsx_path, "rb") as f:
            response = client.post(
                "/api/schedule/upload",
                files={"file": ("data.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"algorithm": "FCFS", "setup_time": "2"},
                headers=auth_headers,
            )
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert "status_url" in data
        assert data["task_id"]  # non-empty


class TestStatusEndpoint:
    def test_unknown_task_returns_404(self, client, auth_headers):
        response = client.get("/api/schedule/status/nonexistent-uuid", headers=auth_headers)
        assert response.status_code == 404


class TestResultsEndpoint:
    def test_unknown_task_returns_404(self, client, auth_headers):
        response = client.get("/api/schedule/results/nonexistent-uuid", headers=auth_headers)
        assert response.status_code == 404


class TestDownloadEndpoint:
    def test_missing_file_returns_404(self, client, auth_headers):
        response = client.get("/api/schedule/download/nonexistent_file.xlsx", headers=auth_headers)
        assert response.status_code == 404


class TestHistoryEndpoint:
    def test_history_empty(self, client, auth_headers):
        """History should return empty items on a clean database."""
        response = client.get("/api/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["pages"] == 1

    def test_history_with_filters(self, client, auth_headers):
        """History with filters should return 200 even with no matches."""
        response = client.get("/api/history?algorithm=GA&status=complete", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

