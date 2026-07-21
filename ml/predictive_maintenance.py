"""
ml/predictive_maintenance.py
Predictive maintenance engine for ShopFloorScheduler (Phase 4).

Provides:
  - SensorSimulator   : Generates synthetic sensor telemetry for machines.
  - MaintenancePredictor : Isolation Forest anomaly detector that produces
                           failure probability scores and maintenance forecasts.
  - proactive_block_windows : Converts high-probability windows into machine
                              unavailability tuples compatible with the scheduler.
"""
from __future__ import annotations

import math
import random
import datetime
from typing import List, Dict, Optional, Tuple

from core.logger import logger

# ---------------------------------------------------------------------------
# Try to import scikit-learn; provide graceful degradation if not installed
# ---------------------------------------------------------------------------
try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    _SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed — MaintenancePredictor will use heuristic fallback.")


# ---------------------------------------------------------------------------
# Constants / tuning knobs
# ---------------------------------------------------------------------------
_BASELINE_TEMP = 65.0          # °C normal operating temperature
_BASELINE_VIB = 2.5            # mm/s RMS normal vibration
_BASELINE_LOAD = 60.0          # % normal load
_TEMP_STDDEV = 5.0
_VIB_STDDEV = 0.8
_LOAD_STDDEV = 10.0

# Thresholds for heuristic fallback (used when sklearn unavailable)
_HIGH_TEMP_THRESHOLD = 85.0
_HIGH_VIB_THRESHOLD = 5.5
_HIGH_LOAD_THRESHOLD = 88.0

SEVERITY_THRESHOLDS = {
    "critical": 0.80,
    "high": 0.60,
    "medium": 0.35,
    "low": 0.10,
}

RECOMMENDED_ACTIONS = {
    "critical": "Schedule immediate maintenance shutdown. Do not run further operations.",
    "high": "Schedule preventive maintenance within 4 hours. Monitor closely.",
    "medium": "Flag for next scheduled maintenance window. Increase monitoring frequency.",
    "low": "Log for trend analysis. No immediate action required.",
}


# ---------------------------------------------------------------------------
# Sensor Simulator
# ---------------------------------------------------------------------------

class SensorReading:
    """Immutable snapshot of sensor state at a point in time."""
    __slots__ = ("machine_id", "timestamp", "temperature", "vibration", "load_pct")

    def __init__(
        self,
        machine_id: str,
        timestamp: datetime.datetime,
        temperature: float,
        vibration: float,
        load_pct: float,
    ) -> None:
        self.machine_id = machine_id
        self.timestamp = timestamp
        self.temperature = temperature
        self.vibration = vibration
        self.load_pct = load_pct

    def to_dict(self) -> dict:
        return {
            "machine_id": self.machine_id,
            "timestamp": self.timestamp.isoformat(),
            "temperature": round(self.temperature, 2),
            "vibration": round(self.vibration, 3),
            "load_pct": round(self.load_pct, 1),
        }


class SensorSimulator:
    """
    Generates realistic synthetic sensor time-series for a set of machines.

    The simulator uses a per-machine PRNG seeded by `machine_id` so results
    are reproducible. A small number of readings will have injected anomalies
    (temperature spikes, vibration bursts, overload events) to give the
    anomaly detector something meaningful to detect.
    """

    def __init__(self, anomaly_fraction: float = 0.08, seed: Optional[int] = None) -> None:
        self.anomaly_fraction = anomaly_fraction
        self._global_seed = seed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        machine_ids: List[str],
        n_readings: int = 48,
        start_time: Optional[datetime.datetime] = None,
        interval_minutes: int = 30,
    ) -> Dict[str, List[SensorReading]]:
        """
        Generate `n_readings` sensor readings per machine, spaced `interval_minutes` apart.

        Returns a dict mapping machine_id → list[SensorReading].
        """
        if start_time is None:
            start_time = datetime.datetime.utcnow() - datetime.timedelta(
                minutes=interval_minutes * n_readings
            )

        result: Dict[str, List[SensorReading]] = {}
        for machine_id in machine_ids:
            rng = random.Random(f"{self._global_seed}-{machine_id}")
            readings: List[SensorReading] = []
            for i in range(n_readings):
                ts = start_time + datetime.timedelta(minutes=i * interval_minutes)
                temp, vib, load = self._sample_reading(rng, i, n_readings)
                readings.append(SensorReading(machine_id, ts, temp, vib, load))
            result[machine_id] = readings

        return result

    def generate_single(
        self,
        machine_id: str,
        timestamp: Optional[datetime.datetime] = None,
    ) -> SensorReading:
        """Generate one fresh sensor reading (for real-time ingest simulation)."""
        rng = random.Random()  # non-deterministic for live readings
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        temp, vib, load = self._sample_reading(rng, 0, 1)
        return SensorReading(machine_id, timestamp, temp, vib, load)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sample_reading(
        self,
        rng: random.Random,
        index: int,
        total: int,
    ) -> Tuple[float, float, float]:
        """Sample temperature, vibration, and load with occasional anomalies."""
        is_anomaly = rng.random() < self.anomaly_fraction

        if is_anomaly:
            anomaly_type = rng.choice(["temp", "vib", "load", "combined"])
            temp = _BASELINE_TEMP + rng.gauss(0, _TEMP_STDDEV)
            vib = _BASELINE_VIB + rng.gauss(0, _VIB_STDDEV)
            load = _BASELINE_LOAD + rng.gauss(0, _LOAD_STDDEV)
            if anomaly_type in ("temp", "combined"):
                temp += rng.uniform(15.0, 35.0)   # spike
            if anomaly_type in ("vib", "combined"):
                vib += rng.uniform(3.0, 7.0)       # burst
            if anomaly_type in ("load", "combined"):
                load = min(100.0, load + rng.uniform(20.0, 40.0))
        else:
            # Normal operation: slight degradation trend as index increases
            degradation = (index / max(total - 1, 1)) * 3.0
            temp = _BASELINE_TEMP + degradation + rng.gauss(0, _TEMP_STDDEV)
            vib = _BASELINE_VIB + degradation * 0.1 + rng.gauss(0, _VIB_STDDEV)
            load = _BASELINE_LOAD + rng.gauss(0, _LOAD_STDDEV)

        # Clamp to physically plausible ranges
        temp = max(20.0, min(150.0, temp))
        vib = max(0.0, min(20.0, vib))
        load = max(0.0, min(100.0, load))
        return temp, vib, load


# ---------------------------------------------------------------------------
# Maintenance Predictor
# ---------------------------------------------------------------------------

class PredictionResult:
    """Holds the output of a single machine's health assessment."""
    __slots__ = (
        "machine_id", "failure_probability", "anomaly_score",
        "severity", "recommended_action", "predicted_failure_at",
    )

    def __init__(
        self,
        machine_id: str,
        failure_probability: float,
        anomaly_score: float,
        predicted_failure_at: Optional[datetime.datetime] = None,
    ) -> None:
        self.machine_id = machine_id
        self.failure_probability = round(failure_probability, 4)
        self.anomaly_score = round(anomaly_score, 4)
        self.severity = _classify_severity(failure_probability)
        self.recommended_action = RECOMMENDED_ACTIONS[self.severity]
        self.predicted_failure_at = predicted_failure_at

    def to_dict(self) -> dict:
        return {
            "machine_id": self.machine_id,
            "failure_probability": self.failure_probability,
            "anomaly_score": self.anomaly_score,
            "severity": self.severity,
            "recommended_action": self.recommended_action,
            "predicted_failure_at": (
                self.predicted_failure_at.isoformat() if self.predicted_failure_at else None
            ),
        }


class MaintenancePredictor:
    """
    Lightweight anomaly detector using sklearn Isolation Forest.

    The predictor is pre-trained on a large synthetic "normal operation"
    baseline whenever it is first instantiated. It then scores incoming
    sensor readings against that baseline to produce a failure probability.

    Falls back to a purely heuristic scoring method when sklearn is not
    available (ensures the module loads without optional dependencies).
    """

    # Isolation Forest hyperparameters
    _N_ESTIMATORS = 100
    _CONTAMINATION = 0.08   # matches SensorSimulator.anomaly_fraction
    _RANDOM_STATE = 42

    # How many synthetic baseline samples to train on
    _BASELINE_SAMPLES = 2000

    def __init__(self) -> None:
        self._model: Optional["IsolationForest"] = None  # type: ignore[name-defined]
        if _SKLEARN_AVAILABLE:
            self._train_baseline()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, readings: List[SensorReading]) -> PredictionResult:
        """
        Score a list of recent readings for a single machine and return a
        PredictionResult with failure probability + recommended action.
        """
        if not readings:
            raise ValueError("No readings provided for prediction.")

        machine_id = readings[0].machine_id
        features = self._extract_features(readings)

        if _SKLEARN_AVAILABLE and self._model is not None:
            fp, score = self._sklearn_score(features)
        else:
            fp, score = self._heuristic_score(readings)

        # Estimate time-to-failure based on probability
        predicted_at: Optional[datetime.datetime] = None
        if fp >= SEVERITY_THRESHOLDS["medium"]:
            hours_ahead = max(1, round((1.0 - fp) * 24))   # higher prob → sooner
            predicted_at = datetime.datetime.utcnow() + datetime.timedelta(hours=hours_ahead)

        return PredictionResult(machine_id, fp, score, predicted_at)

    def predict_batch(
        self,
        readings_by_machine: Dict[str, List[SensorReading]],
    ) -> Dict[str, PredictionResult]:
        """Score multiple machines in one call."""
        return {mid: self.predict(rdgs) for mid, rdgs in readings_by_machine.items()}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _train_baseline(self) -> None:
        """Train Isolation Forest on synthetic normal-operation data."""
        sim = SensorSimulator(anomaly_fraction=0.0, seed=99)
        # Generate windows of readings per fictitious machine and extract aggregate features
        fake_machines = [f"M{i}" for i in range(10)]
        n_per_machine = max(20, self._BASELINE_SAMPLES // len(fake_machines))
        readings_map = sim.generate(fake_machines, n_readings=n_per_machine)

        all_features: list = []
        window_size = 5  # Extract features from rolling windows
        for rdgs in readings_map.values():
            for start in range(0, len(rdgs) - window_size + 1, window_size):
                window = rdgs[start:start + window_size]
                all_features.append(self._extract_features(window))

        if not all_features:
            return

        X = np.array(all_features)
        self._model = IsolationForest(
            n_estimators=self._N_ESTIMATORS,
            contamination=self._CONTAMINATION,
            random_state=self._RANDOM_STATE,
        )
        self._model.fit(X)
        logger.info(f"MaintenancePredictor: IsolationForest trained on {len(X)} baseline feature vectors.")


    def _extract_features(self, readings: List[SensorReading]) -> list:
        """Compute aggregate feature vector (mean + std + max) per sensor channel."""
        temps = [r.temperature for r in readings]
        vibs = [r.vibration for r in readings]
        loads = [r.load_pct for r in readings]

        def _stats(vals: list) -> Tuple[float, float, float]:
            n = len(vals)
            mean = sum(vals) / n
            variance = sum((v - mean) ** 2 for v in vals) / n
            return mean, math.sqrt(variance), max(vals)

        t_mean, t_std, t_max = _stats(temps)
        v_mean, v_std, v_max = _stats(vibs)
        l_mean, l_std, l_max = _stats(loads)
        return [t_mean, t_std, t_max, v_mean, v_std, v_max, l_mean, l_std, l_max]

    def _sklearn_score(self, features: list) -> Tuple[float, float]:
        """Use Isolation Forest to score a feature vector."""
        X = np.array(features).reshape(1, -1)
        # decision_function: higher = more normal; raw_score < 0 → anomaly
        raw_score = float(self._model.decision_function(X)[0])
        # Map to [0, 1]: score -0.5 → prob 1.0, score +0.5 → prob 0.0
        failure_prob = max(0.0, min(1.0, 0.5 - raw_score))
        return failure_prob, raw_score

    def _heuristic_score(self, readings: List[SensorReading]) -> Tuple[float, float]:
        """Fallback heuristic when sklearn is unavailable."""
        score = 0.0
        n = len(readings)
        for r in readings:
            if r.temperature > _HIGH_TEMP_THRESHOLD:
                score += (r.temperature - _HIGH_TEMP_THRESHOLD) / 50.0
            if r.vibration > _HIGH_VIB_THRESHOLD:
                score += (r.vibration - _HIGH_VIB_THRESHOLD) / 10.0
            if r.load_pct > _HIGH_LOAD_THRESHOLD:
                score += (r.load_pct - _HIGH_LOAD_THRESHOLD) / 30.0
        prob = min(1.0, score / max(n, 1))
        return prob, -prob  # Fake a score consistent with IF sign convention


# ---------------------------------------------------------------------------
# Utility: convert predictions to scheduler-compatible unavailability windows
# ---------------------------------------------------------------------------

def proactive_block_windows(
    predictions: Dict[str, PredictionResult],
    maintenance_duration_hours: int = 4,
    threshold: float = SEVERITY_THRESHOLDS["medium"],
) -> Dict[str, List[Tuple[float, float]]]:
    """
    Convert high-probability failure predictions into machine unavailability
    tuples ``(start_time_units, end_time_units)`` compatible with the existing
    scheduling engine.

    The scheduler works in abstract time units (not wall-clock hours), so the
    conversion assumes 1 time-unit ≈ 1 minute and expresses windows relative
    to *now* (t=0).

    Args:
        predictions:              Output of MaintenancePredictor.predict_batch().
        maintenance_duration_hours: How long to block the machine (default 4 h).
        threshold:                Minimum failure_probability to block.

    Returns:
        Dict mapping machine_id → list of (start, end) time-unit pairs.
    """
    windows: Dict[str, List[Tuple[float, float]]] = {}
    now = datetime.datetime.utcnow()

    for machine_id, pred in predictions.items():
        if pred.failure_probability < threshold:
            continue
        if pred.predicted_failure_at is None:
            continue
        delta_minutes = (pred.predicted_failure_at - now).total_seconds() / 60.0
        delta_minutes = max(0.0, delta_minutes)
        end_minutes = delta_minutes + maintenance_duration_hours * 60.0
        windows[machine_id] = [(delta_minutes, end_minutes)]
        logger.info(
            f"Proactive block: machine={machine_id} window=({delta_minutes:.0f}, {end_minutes:.0f}) "
            f"prob={pred.failure_probability:.3f}"
        )

    return windows


# ---------------------------------------------------------------------------
# Convenience: classify severity from probability
# ---------------------------------------------------------------------------

def _classify_severity(prob: float) -> str:
    if prob >= SEVERITY_THRESHOLDS["critical"]:
        return "critical"
    if prob >= SEVERITY_THRESHOLDS["high"]:
        return "high"
    if prob >= SEVERITY_THRESHOLDS["medium"]:
        return "medium"
    return "low"
