"""
api/routers/twin.py
Digital Twin REST + WebSocket endpoints (Phase 4).

Routes:
  POST   /api/twin/start/{task_id}                     — Start a twin session
  GET    /api/twin/sessions                            — List active sessions
  DELETE /api/twin/sessions/{session_id}               — Stop a session
  POST   /api/twin/sessions/{session_id}/inject        — Inject a disruption
  WS     /ws/twin/{session_id}                         — Real-time event stream
"""
from __future__ import annotations

import asyncio
import datetime
import json
import uuid
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from api.schemas import TwinStartRequest, TwinSessionOut, TwinInjectRequest
from core.database import get_db
from core.logger import logger
from core.models_db import ScheduleRun

router = APIRouter(tags=["digital-twin"])

# ---------------------------------------------------------------------------
# Session registry (in-process; ephemeral across restarts)
# ---------------------------------------------------------------------------

_SESSIONS: Dict[str, Dict[str, Any]] = {}
_TWIN_WS_CONNECTIONS: Dict[str, Set[WebSocket]] = {}  # session_id → set of sockets


# ---------------------------------------------------------------------------
# Emit helper (broadcasts to all WS clients subscribed to a session)
# ---------------------------------------------------------------------------

async def _emit(session_id: str, event: dict) -> None:
    connections = _TWIN_WS_CONNECTIONS.get(session_id, set())
    dead: Set[WebSocket] = set()
    for ws in connections:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.add(ws)
    for ws in dead:
        connections.discard(ws)


# ---------------------------------------------------------------------------
# POST /api/twin/start/{task_id}
# ---------------------------------------------------------------------------

@router.post("/api/twin/start/{task_id}", response_model=TwinSessionOut, status_code=201)
async def start_twin_session(task_id: str, payload: TwinStartRequest):
    """
    Start a Digital Twin simulation session for a completed schedule run.

    The session replays the schedule over WebSocket `/ws/twin/{session_id}`.
    """
    # Fetch the completed run from DB
    from sqlalchemy.orm import Session
    from core.database import engine
    with Session(engine) as db:
        run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
        if not run:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
        if run.status != "complete":
            raise HTTPException(
                status_code=409,
                detail=f"Task is not complete (status='{run.status}'). Cannot start twin.",
            )
        # Extract schedule from result_json
        result_data = json.loads(run.result_json) if run.result_json else {}
        raw_schedule = result_data.get("schedule", [])

    if not raw_schedule:
        raise HTTPException(status_code=422, detail="Schedule data not found in run results.")

    # Convert to tuples
    schedule = [
        (
            int(op["job_id"]),
            int(op["op_index"]),
            int(op["machine_id"]),
            float(op["start_time"]),
            float(op["end_time"]),
        )
        for op in raw_schedule
    ]

    session_id = str(uuid.uuid4())[:8]
    _SESSIONS[session_id] = {
        "session_id": session_id,
        "task_id": task_id,
        "status": "running",
        "speed_factor": payload.speed_factor,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "simulator": None,
    }
    _TWIN_WS_CONNECTIONS[session_id] = set()

    # Launch simulation in background
    asyncio.create_task(_run_twin(session_id, schedule, payload))

    ws_url = f"/ws/twin/{session_id}"
    logger.info(f"Digital Twin session started: {session_id} for task {task_id}")
    return TwinSessionOut(
        session_id=session_id,
        task_id=task_id,
        status="running",
        speed_factor=payload.speed_factor,
        created_at=_SESSIONS[session_id]["created_at"],
        ws_url=ws_url,
    )


# ---------------------------------------------------------------------------
# GET /api/twin/sessions
# ---------------------------------------------------------------------------

@router.get("/api/twin/sessions", response_model=List[TwinSessionOut])
def list_twin_sessions():
    """List all active (and recently completed) Digital Twin sessions."""
    result = []
    for sid, s in _SESSIONS.items():
        sim = s.get("simulator")
        status = "running" if (sim and sim.is_running) else s["status"]
        result.append(TwinSessionOut(
            session_id=sid,
            task_id=s["task_id"],
            status=status,
            speed_factor=s["speed_factor"],
            created_at=s["created_at"],
            ws_url=f"/ws/twin/{sid}",
        ))
    return result


# ---------------------------------------------------------------------------
# DELETE /api/twin/sessions/{session_id}
# ---------------------------------------------------------------------------

@router.delete("/api/twin/sessions/{session_id}", status_code=204)
def stop_twin_session(session_id: str):
    """Stop and remove a Digital Twin session."""
    if session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    _SESSIONS[session_id]["status"] = "stopped"
    logger.info(f"Digital Twin session stopped: {session_id}")


# ---------------------------------------------------------------------------
# POST /api/twin/sessions/{session_id}/inject
# ---------------------------------------------------------------------------

@router.post("/api/twin/sessions/{session_id}/inject", status_code=202)
async def inject_disruption(session_id: str, payload: TwinInjectRequest):
    """Inject a disruption (breakdown or rush order) into a running simulation."""
    if session_id not in _SESSIONS:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    sim = _SESSIONS[session_id].get("simulator")
    if not sim or not sim.is_running:
        raise HTTPException(status_code=409, detail="Session is not currently running.")

    disruption = {
        "disruption_type": payload.disruption_type,
        "machine_id": payload.machine_id,
        "at_time": payload.at_time,
        "duration": 20.0,  # default breakdown duration
        "rush_job": payload.rush_job,
    }
    await sim.inject_disruption(disruption)
    logger.info(f"Disruption injected into session {session_id}: {payload.disruption_type}")
    return {"message": f"Disruption '{payload.disruption_type}' queued for injection."}


# ---------------------------------------------------------------------------
# WebSocket /ws/twin/{session_id}
# ---------------------------------------------------------------------------

@router.websocket("/ws/twin/{session_id}")
async def twin_ws(websocket: WebSocket, session_id: str):
    """WebSocket endpoint: streams SimEvent frames for a Digital Twin session."""
    await websocket.accept()

    if session_id not in _SESSIONS:
        await websocket.send_text(json.dumps({"error": "Session not found."}))
        await websocket.close()
        return

    _TWIN_WS_CONNECTIONS.setdefault(session_id, set()).add(websocket)
    logger.info(f"WS client connected to twin session {session_id}")

    try:
        # Keep connection alive until client disconnects
        while True:
            # Wait for any incoming message (ping/pong or close frame)
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                pass  # No message from client; just keep alive
    except WebSocketDisconnect:
        pass
    finally:
        connections = _TWIN_WS_CONNECTIONS.get(session_id, set())
        connections.discard(websocket)
        logger.info(f"WS client disconnected from twin session {session_id}")


# ---------------------------------------------------------------------------
# Background simulation runner
# ---------------------------------------------------------------------------

async def _run_twin(session_id: str, schedule: list, payload: TwinStartRequest) -> None:
    """Async task: run the DigitalTwin simulator for a session."""
    from twin.simulator import DigitalTwin

    try:
        sim = DigitalTwin(
            schedule=schedule,
            session_id=session_id,
            speed_factor=payload.speed_factor,
            inject_failures=payload.inject_failures,
        )
        _SESSIONS[session_id]["simulator"] = sim
        await sim.run(_emit)
        _SESSIONS[session_id]["status"] = "complete"
        logger.info(f"Digital Twin session complete: {session_id}")

    except Exception as exc:
        logger.exception(f"Digital Twin error in session {session_id}: {exc}")
        _SESSIONS[session_id]["status"] = "error"
        await _emit(session_id, {
            "event_type": "error",
            "virtual_time": 0,
            "payload": {"message": str(exc)},
        })
