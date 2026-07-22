"""
tests/test_pdf_exporter.py
Phase 5: Tests for PDF report generation.
"""
import os
import tempfile
import json
import pytest


SAMPLE_RESULT_JSON = json.dumps({
    "makespan": 85,
    "total_tardiness": 10,
    "avg_flow_time": 45.5,
    "on_time_percent": 80.0,
    "algorithm": "GA",
    "schedule": [
        {"job_id": 1, "op_index": 0, "machine_id": 1, "start_time": 0, "end_time": 15},
        {"job_id": 1, "op_index": 1, "machine_id": 2, "start_time": 15, "end_time": 30},
        {"job_id": 2, "op_index": 0, "machine_id": 2, "start_time": 30, "end_time": 50},
        {"job_id": 2, "op_index": 1, "machine_id": 1, "start_time": 50, "end_time": 85},
    ],
    "utilization": [
        {"machine_id": 1, "utilization": 0.59},
        {"machine_id": 2, "utilization": 0.47},
    ],
})

SAMPLE_META = {
    "algorithm": "GA",
    "created_at": "2026-07-22T10:00:00",
    "file_name": "test_data.xlsx",
    "makespan": 85,
    "total_tardiness": 10,
    "avg_flow_time": 45.5,
    "on_time_percent": 80.0,
}


class TestPDFExporter:
    def test_generate_pdf_returns_path(self, tmp_path, monkeypatch):
        """generate_pdf_report should return a valid file path."""
        import pdf_exporter as pdf_mod

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        static_dir = tmp_path / "static"
        static_dir.mkdir()
        monkeypatch.setattr(pdf_mod, "PDF_FOLDER", str(output_dir))

        task_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        pdf_path = pdf_mod.generate_pdf_report(
            task_id=task_id,
            result_json=SAMPLE_RESULT_JSON,
            run_meta=SAMPLE_META,
        )
        assert os.path.exists(pdf_path)

    def test_generate_pdf_is_pdf_format(self, tmp_path, monkeypatch):
        """Generated file should start with the PDF magic bytes."""
        import pdf_exporter as pdf_mod

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        monkeypatch.setattr(pdf_mod, "PDF_FOLDER", str(output_dir))

        task_id = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        pdf_path = pdf_mod.generate_pdf_report(
            task_id=task_id,
            result_json=SAMPLE_RESULT_JSON,
            run_meta=SAMPLE_META,
        )
        with open(pdf_path, "rb") as f:
            header = f.read(4)
        assert header == b"%PDF", f"File does not start with PDF magic bytes: {header!r}"

    def test_generate_pdf_with_no_schedule(self, tmp_path, monkeypatch):
        """PDF generation should succeed even with an empty schedule."""
        import pdf_exporter as pdf_mod

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        monkeypatch.setattr(pdf_mod, "PDF_FOLDER", str(output_dir))

        empty_result = json.dumps({
            "makespan": 0, "total_tardiness": 0,
            "avg_flow_time": 0.0, "on_time_percent": 0.0,
            "algorithm": "FCFS", "schedule": [], "utilization": [],
        })
        task_id = "c3d4e5f6-a7b8-9012-cdef-123456789012"
        pdf_path = pdf_mod.generate_pdf_report(task_id=task_id, result_json=empty_result, run_meta={})
        assert os.path.exists(pdf_path)

    def test_generate_pdf_minimum_file_size(self, tmp_path, monkeypatch):
        """PDF should be at least 5 KB (not an empty file)."""
        import pdf_exporter as pdf_mod

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        monkeypatch.setattr(pdf_mod, "PDF_FOLDER", str(output_dir))

        task_id = "d4e5f6a7-b8c9-0123-defa-234567890123"
        pdf_path = pdf_mod.generate_pdf_report(
            task_id=task_id,
            result_json=SAMPLE_RESULT_JSON,
            run_meta=SAMPLE_META,
        )
        size = os.path.getsize(pdf_path)
        assert size > 5000, f"PDF too small: {size} bytes"

    def test_generate_pdf_from_db_not_found(self):
        """generate_pdf_from_db should raise ValueError for nonexistent task_id."""
        from pdf_exporter import generate_pdf_from_db
        with pytest.raises(ValueError, match="not found"):
            generate_pdf_from_db("nonexistent-task-id-00000000")

    def test_pdf_endpoint_nonexistent_run(self, client, auth_headers):
        """GET /api/schedule/pdf/{task_id} should return 404 for unknown run."""
        resp = client.get("/api/schedule/pdf/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert resp.status_code == 404
