"""Auth and scope tests for /api/v1/commemorations: GET requires auth and scope; mutate endpoints admin-only (ADMN-06, ADMN-07)."""

import os
import sys
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from app.main import app
except ImportError:
    from main import app

try:
    from app.api.routes import commemorations as commemorations_routes
except ImportError:
    from api.routes import commemorations as commemorations_routes

client = TestClient(app)
COMMEMORATIONS = "/api/v1/commemorations"


def test_get_commemorations_no_token_returns_401():
    """GET /commemorations without Authorization returns 401."""
    resp = client.get(COMMEMORATIONS)
    assert resp.status_code == 401


def test_get_commemorations_with_user_token_returns_own_scope():
    """GET /commemorations with user token returns only that user's order commemorations."""
    mock_user = MagicMock()
    mock_user.email = "user_comm@example.com"
    mock_user.role = "user"
    mock_user.is_active = True

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[commemorations_routes.get_current_user] = override_get_current_user
    try:
        with patch("api.routes.commemorations.get_commemorations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"id": 1, "user_email": "user_comm@example.com", "canonical_name": "Иван"},
            ]
            resp = client.get(
                COMMEMORATIONS,
                headers={"Authorization": "Bearer any"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data and "count" in data
            mock_get.assert_called_once()
            call_kw = mock_get.call_args[1]
            assert call_kw.get("user_email") == "user_comm@example.com"
    finally:
        del app.dependency_overrides[commemorations_routes.get_current_user]


def test_get_commemorations_with_admin_returns_all():
    """GET /commemorations with admin token returns all (no user filter)."""
    mock_admin = MagicMock()
    mock_admin.email = "admin@example.com"
    mock_admin.role = "admin"
    mock_admin.is_active = True

    async def override_get_current_user():
        return mock_admin

    app.dependency_overrides[commemorations_routes.get_current_user] = override_get_current_user
    try:
        with patch("api.routes.commemorations.get_commemorations", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"id": 1, "user_email": "a@x.com", "canonical_name": "A"},
                {"id": 2, "user_email": "b@x.com", "canonical_name": "B"},
            ]
            resp = client.get(
                COMMEMORATIONS,
                headers={"Authorization": "Bearer any"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["items"]) == 2
            mock_get.assert_called_once()
            call_kw = mock_get.call_args[1]
            assert call_kw.get("user_email") is None
    finally:
        del app.dependency_overrides[commemorations_routes.get_current_user]


def test_patch_commemoration_as_user_returns_403():
    """PATCH /commemorations/{id} as non-admin returns 403."""
    async def override_require_admin_403():
        raise HTTPException(status_code=403, detail="Admin required")

    app.dependency_overrides[commemorations_routes.require_admin] = override_require_admin_403
    try:
        resp = client.patch(
            f"{COMMEMORATIONS}/1",
            json={"starts_at": "2025-01-01T00:00:00"},
            headers={"Authorization": "Bearer any"},
        )
        assert resp.status_code == 403
    finally:
        del app.dependency_overrides[commemorations_routes.require_admin]


def test_delete_commemoration_as_user_returns_403():
    """DELETE /commemorations/{id} as non-admin returns 403."""
    async def override_require_admin_403():
        raise HTTPException(status_code=403, detail="Admin required")

    app.dependency_overrides[commemorations_routes.require_admin] = override_require_admin_403
    try:
        resp = client.delete(
            f"{COMMEMORATIONS}/1",
            headers={"Authorization": "Bearer any"},
        )
        assert resp.status_code == 403
    finally:
        del app.dependency_overrides[commemorations_routes.require_admin]


def test_bulk_update_as_user_returns_403():
    """POST /commemorations/bulk-update as non-admin returns 403."""
    async def override_require_admin_403():
        raise HTTPException(status_code=403, detail="Admin required")

    app.dependency_overrides[commemorations_routes.require_admin] = override_require_admin_403
    try:
        resp = client.post(
            f"{COMMEMORATIONS}/bulk-update",
            json={"ids": [1, 2], "starts_at": "2025-01-01T00:00:00"},
            headers={"Authorization": "Bearer any"},
        )
        assert resp.status_code == 403
    finally:
        del app.dependency_overrides[commemorations_routes.require_admin]


def test_patch_commemoration_as_admin_returns_200_or_404():
    """PATCH /commemorations/{id} as admin returns 200 when resource exists, 404 when not."""
    mock_admin = MagicMock()
    mock_admin.email = "admin@example.com"
    mock_admin.role = "admin"
    mock_admin.is_active = True

    async def override_get_current_user():
        return mock_admin

    async def override_require_admin_ok():
        return mock_admin

    app.dependency_overrides[commemorations_routes.get_current_user] = override_get_current_user
    app.dependency_overrides[commemorations_routes.require_admin] = override_require_admin_ok
    try:
        resp = client.patch(
            f"{COMMEMORATIONS}/999",
            json={"starts_at": "2025-01-01T00:00:00"},
            headers={"Authorization": "Bearer any"},
        )
        assert resp.status_code in (200, 404)
    finally:
        del app.dependency_overrides[commemorations_routes.get_current_user]
        del app.dependency_overrides[commemorations_routes.require_admin]


def test_delete_commemoration_as_admin_returns_200_or_404():
    """DELETE /commemorations/{id} as admin returns 200 when found, 404 when not."""
    mock_admin = MagicMock()
    mock_admin.email = "admin@example.com"
    mock_admin.role = "admin"
    mock_admin.is_active = True

    async def override_get_current_user():
        return mock_admin

    async def override_require_admin_ok():
        return mock_admin

    # Use same get_db reference as the route so override is applied (avoids asyncpg event-loop in TestClient)
    get_db_ref = commemorations_routes.get_db
    async def mock_get_db():
        session = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None  # not found -> 404
        session.execute = AsyncMock(return_value=result)
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[commemorations_routes.get_current_user] = override_get_current_user
    app.dependency_overrides[get_db_ref] = mock_get_db
    app.dependency_overrides[commemorations_routes.require_admin] = override_require_admin_ok
    try:
        resp = client.delete(
            f"{COMMEMORATIONS}/999999",
            headers={"Authorization": "Bearer any"},
        )
        assert resp.status_code == 404
    finally:
        del app.dependency_overrides[commemorations_routes.get_current_user]
        del app.dependency_overrides[get_db_ref]
        del app.dependency_overrides[commemorations_routes.require_admin]
