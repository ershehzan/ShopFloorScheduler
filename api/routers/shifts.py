# api/routers/shifts.py
"""
Phase 5: Machine Shift Scheduling API

Routes:
  GET    /api/shifts                      — List all machine shift configurations
  POST   /api/shifts                      — Create / upsert a shift for a machine
  PUT    /api/shifts/{shift_id}           — Update a shift configuration
  DELETE /api/shifts/{shift_id}           — Remove a shift configuration
  GET    /api/shifts/{machine_id}         — Get shifts for a specific machine
"""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.schemas import (
    MachineShiftIn,
    MachineShiftOut,
)
from core.database import get_db
from core.logger import logger
from core.models_db import MachineShift
from core.security import get_current_user

router = APIRouter(prefix="/api/shifts", tags=["Shift Scheduling"])



# ---------------------------------------------------------------------------
# GET /api/shifts
# ---------------------------------------------------------------------------

@router.get("", response_model=list[MachineShiftOut], summary="List all machine shift configurations")
def list_shifts(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """Return all shift window configurations, optionally filtering to active only."""
    query = db.query(MachineShift)
    if active_only:
        query = query.filter(MachineShift.is_active == True)
    shifts = query.order_by(MachineShift.machine_id, MachineShift.shift_name).all()
    return [_to_out(s) for s in shifts]


# ---------------------------------------------------------------------------
# GET /api/shifts/machine/{machine_id}
# ---------------------------------------------------------------------------

@router.get(
    "/machine/{machine_id}",
    response_model=list[MachineShiftOut],
    summary="Get all shift windows for a specific machine",
)
def get_machine_shifts(
    machine_id: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    shifts = (
        db.query(MachineShift)
        .filter(MachineShift.machine_id == machine_id)
        .order_by(MachineShift.shift_name)
        .all()
    )
    return [_to_out(s) for s in shifts]


# ---------------------------------------------------------------------------
# POST /api/shifts
# ---------------------------------------------------------------------------

@router.post("", response_model=MachineShiftOut, status_code=201, summary="Create a shift configuration")
def create_shift(
    body: MachineShiftIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    Create a new shift window for a machine.
    If an active shift with the same machine_id + shift_name already exists, it is updated (upsert).
    """
    # Upsert logic: deactivate existing shift with same name for this machine
    existing = (
        db.query(MachineShift)
        .filter(
            MachineShift.machine_id == body.machine_id,
            MachineShift.shift_name == body.shift_name.upper(),
        )
        .first()
    )
    if existing:
        existing.shift_start = body.shift_start
        existing.shift_end = body.shift_end
        existing.cycle_length = body.cycle_length
        existing.is_active = body.is_active
        db.commit()
        db.refresh(existing)
        logger.info(
            "Updated shift '{}' for machine '{}'.",
            body.shift_name.upper(),
            body.machine_id,
        )
        return _to_out(existing)

    shift = MachineShift(
        machine_id=body.machine_id,
        shift_name=body.shift_name.upper(),
        shift_start=body.shift_start,
        shift_end=body.shift_end,
        cycle_length=body.cycle_length,
        is_active=body.is_active,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    logger.info("Created shift '{}' for machine '{}'.", shift.shift_name, shift.machine_id)
    return _to_out(shift)


# ---------------------------------------------------------------------------
# PUT /api/shifts/{shift_id}
# ---------------------------------------------------------------------------

@router.put("/{shift_id}", response_model=MachineShiftOut, summary="Update a shift configuration")
def update_shift(
    shift_id: int,
    body: MachineShiftIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    shift = db.query(MachineShift).filter(MachineShift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift configuration not found.")

    shift.machine_id = body.machine_id
    shift.shift_name = body.shift_name.upper()
    shift.shift_start = body.shift_start
    shift.shift_end = body.shift_end
    shift.cycle_length = body.cycle_length
    shift.is_active = body.is_active
    db.commit()
    db.refresh(shift)
    logger.info("Updated shift id={} for machine '{}'.", shift_id, shift.machine_id)
    return _to_out(shift)


# ---------------------------------------------------------------------------
# DELETE /api/shifts/{shift_id}
# ---------------------------------------------------------------------------

@router.delete("/{shift_id}", status_code=204, summary="Delete a shift configuration")
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    shift = db.query(MachineShift).filter(MachineShift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift configuration not found.")
    db.delete(shift)
    db.commit()
    logger.info("Deleted shift id={}.", shift_id)
    return None


# ---------------------------------------------------------------------------
# Internal serialiser
# ---------------------------------------------------------------------------

def _to_out(s: MachineShift) -> MachineShiftOut:
    return MachineShiftOut(
        id=s.id,
        machine_id=s.machine_id,
        shift_name=s.shift_name,
        shift_start=s.shift_start,
        shift_end=s.shift_end,
        cycle_length=s.cycle_length,
        is_active=s.is_active,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )
