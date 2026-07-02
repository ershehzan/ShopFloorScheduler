# tests/test_websocket.py
"""
Unit and integration tests for Phase 3 WebSocket real-time progress and notifications.
"""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from core.security import create_access_token
from core.models_db import User, ScheduleRun


def test_ws_notifications_unauthorized(client):
    # No token provided
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/ws/notifications") as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_ws_notifications_authorized(client, test_db):
    user = test_db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(email="test@example.com", username="testuser", hashed_password="pw", is_active=True)
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    
    with client.websocket_connect(f"/api/ws/notifications?token={token}") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"
        
        # Test ping-pong
        ws.send_text("ping")
        resp = ws.receive_json()
        assert resp["type"] == "pong"


def test_ws_task_progress_auth(client, test_db):
    user1 = test_db.query(User).filter(User.email == "test@example.com").first()
    if not user1:
        user1 = User(email="test@example.com", username="testuser", hashed_password="pw", is_active=True)
        test_db.add(user1)
        test_db.commit()
        test_db.refresh(user1)

    token1 = create_access_token({"sub": str(user1.id), "email": user1.email})
    
    # Create another user (user2)
    user2 = test_db.query(User).filter(User.email == "other@example.com").first()
    if not user2:
        user2 = User(email="other@example.com", username="otheruser", hashed_password="pw", is_active=True)
        test_db.add(user2)
        test_db.commit()
        test_db.refresh(user2)
        
    token2 = create_access_token({"sub": str(user2.id), "email": user2.email})

    # Create a run owned by user1
    run = test_db.query(ScheduleRun).filter(ScheduleRun.task_id == "task-ws-uuid").first()
    if not run:
        run = ScheduleRun(task_id="task-ws-uuid", status="pending", user_id=user1.id)
        test_db.add(run)
        test_db.commit()

    # 1. Connect without token -> fail (1008)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/ws/tasks/task-ws-uuid") as ws:
            ws.receive_json()
    assert exc.value.code == 1008

    # 2. Connect as user2 (not owner) -> fail (1008)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/api/ws/tasks/task-ws-uuid?token={token2}") as ws:
            ws.receive_json()
    assert exc.value.code == 1008

    # 3. Connect as user1 (owner) -> succeed
    with client.websocket_connect(f"/api/ws/tasks/task-ws-uuid?token={token1}") as ws:
        data = ws.receive_json()
        assert data["type"] == "connected"
        assert data["task_id"] == "task-ws-uuid"
