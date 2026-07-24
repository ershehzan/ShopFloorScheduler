"""
tests/test_maintenance.py
Tests for Phase 4 Predictive Maintenance module.

Covers:
  - SensorSimulator: synthetic data generation, reproducibility, anomaly injection
  - MaintenancePredictor: prediction output structure, severity classification
  - proactive_block_windows: threshold filtering, window generation
  - API endpoints: ingest, health, alerts, forecast
"""
import datetime
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# SensorSimulator tests
# ---------------------------------------------------------------------------

class TestSensorSimulator:
    def test_generates_correct_number_of_readings(self):
        from ml.predictive_maintenance import SensorSimulator
        sim = SensorSimulator(seed=42)
        result = sim.generate(["M1", "M2"], n_readings=10)
        assert "M1" in result
        assert "M2" in result
        assert len(result["M1"]) == 10
        assert len(result["M2"]) == 10

    def test_readings_are_reproducible_with_same_seed(self):
        from ml.predictive_maintenance import SensorSimulator
        sim1 = SensorSimulator(seed=99)
        sim2 = SensorSimulator(seed=99)
        r1 = sim1.generate(["M1"], n_readings=5)
        r2 = sim2.generate(["M1"], n_readings=5)
        for a, b in zip(r1["M1"], r2["M1"]):
            assert abs(a.temperature - b.temperature) < 0.001

    def test_readings_differ_with_different_seeds(self):
        from ml.predictive_maintenance import SensorSimulator
        sim1 = SensorSimulator(seed=1)
        sim2 = SensorSimulator(seed=2)
        r1 = sim1.generate(["M1"], n_readings=10)
        r2 = sim2.generate(["M1"], n_readings=10)
        temps1 = [r.temperature for r in r1["M1"]]
        temps2 = [r.temperature for r in r2["M1"]]
        assert temps1 != temps2

    def test_readings_within_physical_bounds(self):
        from ml.predictive_maintenance import SensorSimulator
        sim = SensorSimulator(anomaly_fraction=1.0, seed=7)  # all anomalies
        result = sim.generate(["M1"], n_readings=50)
        for r in result["M1"]:
            assert 20.0 <= r.temperature <= 150.0
            assert 0.0 <= r.vibration <= 20.0
            assert 0.0 <= r.load_pct <= 100.0

    def test_single_reading_generation(self):
        from ml.predictive_maintenance import SensorSimulator
        sim = SensorSimulator()
        reading = sim.generate_single("M3")
        assert reading.machine_id == "M3"
        assert reading.timestamp is not None

    def test_to_dict_serialization(self):
        from ml.predictive_maintenance import SensorSimulator
        sim = SensorSimulator(seed=1)
        reading = sim.generate_single("M5")
        d = reading.to_dict()
        assert d["machine_id"] == "M5"
        assert "temperature" in d
        assert "vibration" in d
        assert "load_pct" in d

    def test_timestamps_are_sequential(self):
        from ml.predictive_maintenance import SensorSimulator
        sim = SensorSimulator(seed=42)
        result = sim.generate(["M1"], n_readings=5, interval_minutes=30)
        timestamps = [r.timestamp for r in result["M1"]]
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i - 1]


# ---------------------------------------------------------------------------
# MaintenancePredictor tests
# ---------------------------------------------------------------------------

class TestMaintenancePredictor:
    def test_predict_returns_result_structure(self):
        from ml.predictive_maintenance import MaintenancePredictor, SensorSimulator
        predictor = MaintenancePredictor()
        sim = SensorSimulator(seed=42)
        readings = sim.generate(["M1"], n_readings=10)["M1"]
        result = predictor.predict(readings)
        assert result.machine_id == "M1"
        assert 0.0 <= result.failure_probability <= 1.0
        assert result.severity in ("low", "medium", "high", "critical")
        assert result.recommended_action is not None

    def test_predict_raises_on_empty_readings(self):
        from ml.predictive_maintenance import MaintenancePredictor
        predictor = MaintenancePredictor()
        with pytest.raises(ValueError, match="No readings"):
            predictor.predict([])

    def test_predict_batch(self):
        from ml.predictive_maintenance import MaintenancePredictor, SensorSimulator
        predictor = MaintenancePredictor()
        sim = SensorSimulator(seed=42)
        readings = sim.generate(["M1", "M2"], n_readings=5)
        results = predictor.predict_batch(readings)
        assert "M1" in results
        assert "M2" in results

    def test_high_anomaly_reading_produces_high_probability(self):
        """Force clearly anomalous sensor values and expect higher-than-normal probability."""
        from ml.predictive_maintenance import MaintenancePredictor, SensorReading
        predictor = MaintenancePredictor()
        # Create extreme readings
        now = datetime.datetime.utcnow()
        readings = [
            SensorReading("M_bad", now, temperature=145.0, vibration=18.0, load_pct=99.0)
            for _ in range(10)
        ]
        result = predictor.predict(readings)
        # Should be classified at least medium
        assert result.failure_probability >= 0.2

    def test_severity_classification(self):
        from ml.predictive_maintenance import _classify_severity, SEVERITY_THRESHOLDS
        assert _classify_severity(0.9) == "critical"
        assert _classify_severity(0.7) == "high"
        assert _classify_severity(0.4) == "medium"
        assert _classify_severity(0.05) == "low"


# ---------------------------------------------------------------------------
# proactive_block_windows tests
# ---------------------------------------------------------------------------

class TestProactiveBlockWindows:
    def test_low_probability_not_blocked(self):
        from ml.predictive_maintenance import (
            proactive_block_windows, PredictionResult, SEVERITY_THRESHOLDS
        )
        pred = PredictionResult("M1", failure_probability=0.05, anomaly_score=-0.05)
        windows = proactive_block_windows({"M1": pred})
        assert "M1" not in windows

    def test_high_probability_creates_window(self):
        from ml.predictive_maintenance import proactive_block_windows, PredictionResult
        import datetime
        pred = PredictionResult(
            "M2",
            failure_probability=0.75,
            anomaly_score=-0.5,
            predicted_failure_at=datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        )
        windows = proactive_block_windows({"M2": pred})
        assert "M2" in windows
        assert len(windows["M2"]) == 1
        start, end = windows["M2"][0]
        assert end > start

    def test_no_windows_when_no_predicted_failure_at(self):
        from ml.predictive_maintenance import proactive_block_windows, PredictionResult
        pred = PredictionResult("M3", failure_probability=0.9, anomaly_score=-0.9)
        # predicted_failure_at is None
        windows = proactive_block_windows({"M3": pred})
        assert "M3" not in windows


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestMaintenanceAPI:
    def test_ingest_auto_generate(self, client, auth_headers):
        response = client.post("/api/maintenance/ingest", json={
            "auto_generate": True,
            "machine_ids": ["M1", "M2"],
            "n_readings": 5,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 10  # 2 machines × 5 readings

    def test_ingest_explicit_readings(self, client, auth_headers):
        response = client.post("/api/maintenance/ingest", json={
            "auto_generate": False,
            "readings": [
                {
                    "machine_id": "M99",
                    "temperature": 70.0,
                    "vibration": 3.0,
                    "load_pct": 65.0,
                }
            ],
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert data[0]["machine_id"] == "M99"

    def test_ingest_missing_both_raises_422(self, client, auth_headers):
        response = client.post("/api/maintenance/ingest", json={
            "auto_generate": False,
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_get_machine_health(self, client, auth_headers):
        # First ingest
        client.post("/api/maintenance/ingest", json={
            "auto_generate": True, "machine_ids": ["M_test"], "n_readings": 3
        }, headers=auth_headers)
        response = client.get("/api/maintenance/health/M_test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["machine_id"] == "M_test"

    def test_get_machine_health_not_found(self, client, auth_headers):
        response = client.get("/api/maintenance/health/NONEXISTENT_XYZ", headers=auth_headers)
        assert response.status_code == 404

    def test_list_alerts(self, client, auth_headers):
        response = client.get("/api/maintenance/alerts", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_forecast(self, client, auth_headers):
        # Ingest first
        client.post("/api/maintenance/ingest", json={
            "auto_generate": True, "machine_ids": ["F1", "F2"], "n_readings": 5
        }, headers=auth_headers)
        response = client.get("/api/maintenance/forecast?machine_ids=F1,F2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "windows" in data
        assert "generated_at" in data

    def test_resolve_nonexistent_alert(self, client, admin_headers):
        response = client.post("/api/maintenance/alerts/9999999/resolve", headers=admin_headers)
        assert response.status_code == 404
