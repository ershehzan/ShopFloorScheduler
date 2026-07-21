"""
api/routers/maintenance.py
Predictive Maintenance REST API endpoints (Phase 4).

Routes:
  POST   /api/maintenance/ingest               — Ingest or auto-generate sensor readings
  GET    /api/maintenance/health/{machine_id}  — Latest health snapshot + failure prob
  GET    /api/maintenance/alerts               — List active (unresolved) alerts
  POST   /api/maintenance/alerts/{alert_id}/resolve — Mark alert as resolved
  GET    /api/maintenance/forecast             — Predicted unavailability windows per machine
  GET    /api/maintenance/history/{machine_id} — Historical telemetry for a machine
"""
from __future__ import annotations

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.schemas import (
    SensorIngestRequest,
    MachineHealthOut,
    MaintenanceAlertOut,
    MaintenanceForecastOut,
    MaintenanceForecastItem,
)
from core.database import get_db
from core.logger import logger
from core.models_db import MachineHealth, MaintenanceAlert
from ml.predictive_maintenance import (
    SensorSimulator,
    MaintenancePredictor,
    proactive_block_windows,
)

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

# Singleton predictor (trains baseline on first import — cached for lifetime of process)
_predictor: Optional[MaintenancePredictor] = None


def _get_predictor() -> MaintenancePredictor:
    global _predictor
    if _predictor is None:
        _predictor = MaintenancePredictor()
    return _predictor


# ---------------------------------------------------------------------------
# POST /api/maintenance/ingest
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=List[MachineHealthOut], status_code=201)
def ingest_sensor_readings(
    payload: SensorIngestRequest,
    db: Session = Depends(get_db),
):
    """
    Ingest sensor readings for one or more machines.

    If `auto_generate=true`, the simulator will produce `n_readings` synthetic
    readings for all listed machine IDs. Otherwise, the caller must supply
    explicit reading values in `readings`.

    Each ingested reading is scored by the anomaly detector and persisted.
    If any machine's failure probability exceeds the medium threshold, a
    MaintenanceAlert is automatically created.
    """
    predictor = _get_predictor()
    simulator = SensorSimulator(seed=42)

    created_health: List[MachineHealth] = []

    if payload.auto_generate:
        machine_ids = payload.machine_ids or ["M1", "M2", "M3"]
        n = payload.n_readings or 24
        readings_map = simulator.generate(machine_ids, n_readings=n)
    else:
        # Build readings_map from explicit payload.readings
        if not payload.readings:
            raise HTTPException(status_code=422, detail="Provide readings or set auto_generate=true")
        from ml.predictive_maintenance import SensorReading
        readings_map = {}
        for r in payload.readings:
            ts = r.timestamp or datetime.datetime.utcnow()
            sr = SensorReading(r.machine_id, ts, r.temperature, r.vibration, r.load_pct)
            readings_map.setdefault(r.machine_id, []).append(sr)

    # Score + persist
    predictions = predictor.predict_batch(readings_map)

    for machine_id, readings_list in readings_map.items():
        pred = predictions[machine_id]
        for reading in readings_list:
            health_row = MachineHealth(
                machine_id=machine_id,
                timestamp=reading.timestamp,
                temperature=reading.temperature,
                vibration=reading.vibration,
                load_pct=reading.load_pct,
                failure_probability=pred.failure_probability,
                anomaly_score=pred.anomaly_score,
            )
            db.add(health_row)
            created_health.append(health_row)

        # Auto-create alert if probability crosses medium threshold
        from ml.predictive_maintenance import SEVERITY_THRESHOLDS
        if pred.failure_probability >= SEVERITY_THRESHOLDS["medium"]:
            alert = MaintenanceAlert(
                machine_id=machine_id,
                failure_probability=pred.failure_probability,
                severity=pred.severity,
                recommended_action=pred.recommended_action,
                predicted_failure_at=pred.predicted_failure_at,
            )
            db.add(alert)
            logger.info(f"Auto-created {pred.severity} alert for machine {machine_id}")

    db.commit()
    for h in created_health:
        db.refresh(h)

    logger.info(f"Ingested {len(created_health)} sensor readings across {len(readings_map)} machines.")
    return [_health_to_schema(h) for h in created_health]


# ---------------------------------------------------------------------------
# GET /api/maintenance/health/{machine_id}
# ---------------------------------------------------------------------------

@router.get("/health/{machine_id}", response_model=MachineHealthOut)
def get_machine_health(machine_id: str, db: Session = Depends(get_db)):
    """Return the most recent health reading for a machine."""
    row = (
        db.query(MachineHealth)
        .filter(MachineHealth.machine_id == machine_id)
        .order_by(MachineHealth.timestamp.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"No health data for machine '{machine_id}'")
    return _health_to_schema(row)


# ---------------------------------------------------------------------------
# GET /api/maintenance/history/{machine_id}
# ---------------------------------------------------------------------------

@router.get("/history/{machine_id}", response_model=List[MachineHealthOut])
def get_machine_health_history(
    machine_id: str,
    limit: int = Query(default=48, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return recent health telemetry for a machine (ordered newest-first)."""
    rows = (
        db.query(MachineHealth)
        .filter(MachineHealth.machine_id == machine_id)
        .order_by(MachineHealth.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [_health_to_schema(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/maintenance/alerts
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=List[MaintenanceAlertOut])
def list_alerts(
    machine_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List maintenance alerts. Filterable by machine, severity, and resolved status."""
    q = db.query(MaintenanceAlert)
    if machine_id:
        q = q.filter(MaintenanceAlert.machine_id == machine_id)
    if resolved is not None:
        q = q.filter(MaintenanceAlert.resolved == resolved)
    if severity:
        q = q.filter(MaintenanceAlert.severity == severity)
    rows = q.order_by(MaintenanceAlert.created_at.desc()).limit(200).all()
    return [_alert_to_schema(r) for r in rows]


# ---------------------------------------------------------------------------
# POST /api/maintenance/alerts/{alert_id}/resolve
# ---------------------------------------------------------------------------

@router.post("/alerts/{alert_id}/resolve", response_model=MaintenanceAlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark a maintenance alert as resolved."""
    alert = db.query(MaintenanceAlert).filter(MaintenanceAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    if alert.resolved:
        raise HTTPException(status_code=409, detail="Alert already resolved")
    alert.resolved = True
    alert.resolved_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(alert)
    logger.info(f"Alert {alert_id} resolved for machine {alert.machine_id}")
    return _alert_to_schema(alert)


# ---------------------------------------------------------------------------
# GET /api/maintenance/forecast
# ---------------------------------------------------------------------------

@router.get("/forecast", response_model=MaintenanceForecastOut)
def get_maintenance_forecast(
    machine_ids: Optional[str] = Query(default=None, description="Comma-separated machine IDs"),
    db: Session = Depends(get_db),
):
    """
    Returns predicted unavailability windows per machine, ready to be injected
    into a new schedule upload request.

    If `machine_ids` is not provided, uses all machines that have health data.
    """
    # Determine which machines to forecast
    if machine_ids:
        mids = [m.strip() for m in machine_ids.split(",")]
    else:
        rows = db.query(MachineHealth.machine_id).distinct().all()
        mids = [r[0] for r in rows]

    if not mids:
        return MaintenanceForecastOut(windows={}, generated_at=datetime.datetime.utcnow().isoformat())

    # Get latest readings for each machine
    from ml.predictive_maintenance import SensorReading
    readings_map: dict = {}
    for mid in mids:
        health_rows = (
            db.query(MachineHealth)
            .filter(MachineHealth.machine_id == mid)
            .order_by(MachineHealth.timestamp.desc())
            .limit(24)
            .all()
        )
        if health_rows:
            readings_map[mid] = [
                SensorReading(r.machine_id, r.timestamp, r.temperature, r.vibration, r.load_pct)
                for r in health_rows
            ]

    if not readings_map:
        return MaintenanceForecastOut(windows={}, generated_at=datetime.datetime.utcnow().isoformat())

    predictor = _get_predictor()
    predictions = predictor.predict_batch(readings_map)
    windows = proactive_block_windows(predictions)

    items: dict = {}
    for mid, pred in predictions.items():
        win = windows.get(mid, [])
        items[mid] = MaintenanceForecastItem(
            machine_id=mid,
            failure_probability=pred.failure_probability,
            severity=pred.severity,
            predicted_failure_at=pred.predicted_failure_at.isoformat() if pred.predicted_failure_at else None,
            recommended_action=pred.recommended_action,
            unavailability_windows=win,
        )

    return MaintenanceForecastOut(
        windows=items,
        generated_at=datetime.datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# Internal serializers
# ---------------------------------------------------------------------------

def _health_to_schema(row: MachineHealth) -> MachineHealthOut:
    return MachineHealthOut(
        id=row.id,
        machine_id=row.machine_id,
        timestamp=row.timestamp.isoformat(),
        temperature=row.temperature,
        vibration=row.vibration,
        load_pct=row.load_pct,
        failure_probability=row.failure_probability,
        anomaly_score=row.anomaly_score,
    )


def _alert_to_schema(row: MaintenanceAlert) -> MaintenanceAlertOut:
    return MaintenanceAlertOut(
        id=row.id,
        machine_id=row.machine_id,
        created_at=row.created_at.isoformat(),
        predicted_failure_at=row.predicted_failure_at.isoformat() if row.predicted_failure_at else None,
        severity=row.severity,
        failure_probability=row.failure_probability,
        recommended_action=row.recommended_action,
        resolved=row.resolved,
        resolved_at=row.resolved_at.isoformat() if row.resolved_at else None,
    )
