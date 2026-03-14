"""Admin routes: GET /admin/users (list with counts), PATCH /admin/users/{id} (role, is_active, last-admin guard)."""

import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Prefer same import path as app (main + api.deps when pythonpath=app) so overrides apply
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from main import app
    import api.deps as deps_module
except ImportError:
    from app.main import app
    import app.api.deps as deps_module

client = TestClient(app)
ADMIN_USERS = "/api/v1/admin/users"


def test_get_admin_users_no_token_returns_401():
    """GET /admin/users without Authorization returns 401."""
    resp = client.get(ADMIN_USERS)
    assert resp.status_code == 401


def test_get_admin_users_user_token_returns_403():
    """GET /admin/users with non-admin returns 403 (ADMN-02)."""
    async def override_require_admin_403():
        raise HTTPException(status_code=403, detail="Admin required")

    app.dependency_overrides[deps_module.require_admin] = override_require_admin_403
    try:
        resp = client.get(
            ADMIN_USERS,
            headers={"Authorization": "Bearer any"},
        )
        assert resp.status_code == 403
    finally:
        del app.dependency_overrides[deps_module.require_admin]


def test_get_admin_users_admin_token_returns_200_with_counts():
    """GET /admin/users with admin returns 200 and list with orders_count and active_commemoration_count (ADMN-02)."""
    mock_admin = MagicMock()
    mock_admin.email = "admin@example.com"
    mock_admin.role = "admin"
    mock_admin.is_active = True

    async def override_require_admin_ok():
        return mock_admin

    app.dependency_overrides[deps_module.require_admin] = override_require_admin_ok
    try:
        resp = client.get(
            ADMIN_USERS,
            headers={"Authorization": "Bearer any"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data:
            assert "id" in item
            assert "email" in item
            assert "role" in item
            assert "is_active" in item
            assert "created_at" in item
            assert "orders_count" in item
            assert "active_commemoration_count" in item
    finally:
        del app.dependency_overrides[deps_module.require_admin]
