# api/routers/ws.py
"""
WebSocket router — real-time task progress and system notifications.

Channels:
  WS /api/ws/tasks/{task_id}    — Per-task progress updates (GA generations, completion)
  WS /api/ws/notifications      — System-wide event broadcast
"""
import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.logger import logger

router = APIRouter(tags=["WebSocket"])


# ---------------------------------------------------------------------------
# Connection Manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages active WebSocket connections for both per-task progress
    and global notification channels.
    """

    def __init__(self):
        # task_id -> list of WebSocket connections watching that task
        self._task_connections: dict[str, list[WebSocket]] = {}
        # Global notification subscribers
        self._global_connections: list[WebSocket] = []

    async def connect_task(self, task_id: str, websocket: WebSocket):
        """Accept and register a WebSocket connection for a specific task."""
        await websocket.accept()
        if task_id not in self._task_connections:
            self._task_connections[task_id] = []
        self._task_connections[task_id].append(websocket)
        logger.info("WS: Client connected to task {}", task_id)

    def disconnect_task(self, task_id: str, websocket: WebSocket):
        """Remove a WebSocket connection from a task channel."""
        if task_id in self._task_connections:
            self._task_connections[task_id] = [
                ws for ws in self._task_connections[task_id] if ws != websocket
            ]
            if not self._task_connections[task_id]:
                del self._task_connections[task_id]
        logger.info("WS: Client disconnected from task {}", task_id)

    async def connect_global(self, websocket: WebSocket):
        """Accept and register a global notification subscriber."""
        await websocket.accept()
        self._global_connections.append(websocket)
        logger.info("WS: Client connected to global notifications")

    def disconnect_global(self, websocket: WebSocket):
        """Remove a global notification subscriber."""
        self._global_connections = [
            ws for ws in self._global_connections if ws != websocket
        ]
        logger.info("WS: Client disconnected from global notifications")

    async def send_task_update(self, task_id: str, data: dict):
        """
        Send a JSON message to all WebSocket connections watching a task.
        Silently removes broken connections.
        """
        if task_id not in self._task_connections:
            return

        message = json.dumps(data)
        broken = []
        for ws in self._task_connections[task_id]:
            try:
                await ws.send_text(message)
            except Exception:
                broken.append(ws)

        # Cleanup broken connections
        for ws in broken:
            self.disconnect_task(task_id, ws)

    async def broadcast_notification(self, data: dict):
        """
        Broadcast a JSON message to all global notification subscribers.
        """
        message = json.dumps(data)
        broken = []
        for ws in self._global_connections:
            try:
                await ws.send_text(message)
            except Exception:
                broken.append(ws)

        for ws in broken:
            self.disconnect_global(ws)

    def has_task_listeners(self, task_id: str) -> bool:
        """Check if anyone is listening for a specific task's updates."""
        return task_id in self._task_connections and len(self._task_connections[task_id]) > 0

    @property
    def task_count(self) -> int:
        """Number of tasks with active listeners."""
        return len(self._task_connections)

    @property
    def global_count(self) -> int:
        """Number of global notification subscribers."""
        return len(self._global_connections)


# Singleton instance — shared across the application
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# WebSocket endpoints
# ---------------------------------------------------------------------------

@router.websocket("/api/ws/tasks/{task_id}")
async def websocket_task_progress(websocket: WebSocket, task_id: str, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time task progress.
    Requires JWT access token passed as a query parameter.
    """
    from core.security import decode_token
    from core.database import SessionLocal
    from core.models_db import User, ScheduleRun

    user = None
    db = SessionLocal()
    try:
        if token:
            payload = decode_token(token)
            if payload.get("type") == "access":
                user_id = payload.get("sub")
                if user_id:
                    user = db.query(User).filter(User.id == int(user_id)).first()
        
        if user and user.is_active:
            # Check ownership
            run = db.query(ScheduleRun).filter(ScheduleRun.task_id == task_id).first()
            if run and run.user_id is not None:
                if not user.is_admin and user.id != run.user_id:
                    user = None
        else:
            user = None
    except Exception:
        user = None
    finally:
        db.close()

    if not user:
        # Reject connection
        await websocket.accept()
        await websocket.close(code=1008)
        return

    await manager.connect_task(task_id, websocket)

    # Send initial connection confirmation
    await websocket.send_json({
        "type": "connected",
        "task_id": task_id,
        "message": f"Connected to task {task_id} progress channel.",
    })

    try:
        # Keep the connection alive — wait for client messages or disconnection
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect_task(task_id, websocket)


@router.websocket("/api/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket endpoint for system-wide notifications.
    Requires JWT access token passed as a query parameter.
    """
    from core.security import decode_token
    from core.database import SessionLocal
    from core.models_db import User

    user = None
    db = SessionLocal()
    try:
        if token:
            payload = decode_token(token)
            if payload.get("type") == "access":
                user_id = payload.get("sub")
                if user_id:
                    user = db.query(User).filter(User.id == int(user_id)).first()
        if user and not user.is_active:
            user = None
    except Exception:
        user = None
    finally:
        db.close()

    if not user:
        await websocket.accept()
        await websocket.close(code=1008)
        return

    await manager.connect_global(websocket)

    await websocket.send_json({
        "type": "connected",
        "message": "Connected to global notifications channel.",
    })

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect_global(websocket)


# ---------------------------------------------------------------------------
# Helper for background threads to push updates
# ---------------------------------------------------------------------------

def send_task_progress_sync(task_id: str, data: dict):
    """
    Thread-safe helper to push a task update from a background thread.
    Creates an event loop if needed (for use from non-async contexts).
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule the coroutine on the running loop
            asyncio.ensure_future(manager.send_task_update(task_id, data))
        else:
            loop.run_until_complete(manager.send_task_update(task_id, data))
    except RuntimeError:
        # No event loop in this thread — create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(manager.send_task_update(task_id, data))
        finally:
            loop.close()


def send_global_notification_sync(data: dict):
    """
    Thread-safe helper to broadcast a global notification from a background thread.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(manager.broadcast_notification(data))
        else:
            loop.run_until_complete(manager.broadcast_notification(data))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(manager.broadcast_notification(data))
        finally:
            loop.close()
