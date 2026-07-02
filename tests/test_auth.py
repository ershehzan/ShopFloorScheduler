# tests/test_auth.py
"""
Unit and integration tests for Phase 3 JWT Authentication and router.
"""
import pytest
from core.models_db import User, RefreshToken


def test_register_and_login(client):
    # 1. Register a new user
    reg_payload = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "securepassword123",
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201
    reg_data = res.json()
    assert reg_data["email"] == "newuser@example.com"
    assert reg_data["username"] == "newuser"
    assert "id" in reg_data
    assert reg_data["is_active"] is True
    assert reg_data["is_admin"] is False

    # 2. Try registering duplicate email
    res_dup = client.post("/api/auth/register", json=reg_payload)
    assert res_dup.status_code == 409

    # 3. Log in with the registered credentials
    login_payload = {
        "email": "newuser@example.com",
        "password": "securepassword123",
    }
    res_login = client.post("/api/auth/login", json=login_payload)
    assert res_login.status_code == 200
    tokens = res_login.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"

    # 4. Access protected profile /me
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    profile = res_me.json()
    assert profile["email"] == "newuser@example.com"
    assert profile["username"] == "newuser"


def test_login_invalid_credentials(client):
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "wrongpassword",
    }
    res = client.post("/api/auth/login", json=login_payload)
    assert res.status_code == 401


def test_token_refresh_and_rotation(client):
    # Register and login to get refresh token
    reg_payload = {
        "email": "refresh@example.com",
        "username": "refreshuser",
        "password": "password123",
    }
    client.post("/api/auth/register", json=reg_payload)
    
    login_res = client.post("/api/auth/login", json={
        "email": "refresh@example.com",
        "password": "password123",
    })
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # Exchange refresh token for new access + refresh pair
    refresh_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != refresh_token

    # Verify that the old refresh token is now revoked and cannot be reused
    reuse_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_res.status_code == 401


def test_logout(client):
    # Login to get refresh token
    reg_payload = {
        "email": "logout@example.com",
        "username": "logoutuser",
        "password": "password123",
    }
    client.post("/api/auth/register", json=reg_payload)
    
    login_res = client.post("/api/auth/login", json={
        "email": "logout@example.com",
        "password": "password123",
    })
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # Call logout
    logout_res = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 204

    # Verify that the logged out token is revoked and cannot be used
    refresh_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 401
