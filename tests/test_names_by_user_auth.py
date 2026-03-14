"""Tests for GET /names/by-user: auth required, user sees own data, admin can pass ?email= (phase 04-02)."""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from app.main import app
except ImportError:
    from main import app

try:
    from app.config import settings
except ImportError:
    from config import settings

client = TestClient(app)
BY_USER = "/api/v1/names/by-user"


def _get_current_user_dep():
    """Same get_current_user the by-user route uses (from the route module)."""
    try:
        from app.api.routes import names as names_route
    except ImportError:
        from api.routes import names as names_route
    return names_route.get_current_user


def _make_token(email: str, role: str = "user") -> str:
    return jwt.encode(
        {
            "sub": email,
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(days=1),
            "iat": datetime.now(timezone.utc),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def test_by_user_no_token_returns_401():
    """GET /names/by-user without Authorization returns 401."""
    r = client.get(BY_USER)
    assert r.status_code == 401


def test_by_user_with_user_token_returns_own_data():
    """User token -> returns only that user's data; email query not used for non-admin."""
    user_email = "names_user_test@example.com"
    token = _make_token(user_email, "user")
    mock_user = MagicMock()
    mock_user.email = user_email
    mock_user.role = "user"

    async def override():
        return mock_user

    get_current_user = _get_current_user_dep()
    app.dependency_overrides[get_current_user] = override
    try:
        with patch("api.routes.names.get_by_user", new_callable=AsyncMock, return_value=[]) as mock_get_by_user:
            r = client.get(BY_USER, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["user_email"] == user_email
        assert "commemorations" in data
        assert "count" in data
        mock_get_by_user.assert_called_once()
        call_kw = mock_get_by_user.call_args[1]
        assert call_kw["user_email"] == user_email
    finally:
        del app.dependency_overrides[get_current_user]


def test_by_user_admin_without_email_param_returns_own_data():
    """Admin token without ?email= -> own data."""
    admin_email = "names_admin@example.com"
    token = _make_token(admin_email, "admin")
    mock_admin = MagicMock()
    mock_admin.email = admin_email
    mock_admin.role = "admin"

    async def override():
        return mock_admin

    get_current_user = _get_current_user_dep()
    app.dependency_overrides[get_current_user] = override
    try:
        with patch("api.routes.names.get_by_user", new_callable=AsyncMock, return_value=[]):
            r = client.get(BY_USER, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["user_email"] == admin_email
    finally:
        del app.dependency_overrides[get_current_user]


def test_by_user_admin_with_email_param_returns_that_users_data():
    """Admin with ?email=other@x -> that user's data."""
    admin_email = "names_admin2@example.com"
    other_email = "other_user@example.com"
    token = _make_token(admin_email, "admin")
    mock_admin = MagicMock()
    mock_admin.email = admin_email
    mock_admin.role = "admin"

    async def override():
        return mock_admin

    get_current_user = _get_current_user_dep()
    app.dependency_overrides[get_current_user] = override
    try:
        with patch("api.routes.names.get_by_user", new_callable=AsyncMock, return_value=[]) as mock_get_by_user:
            r = client.get(
                BY_USER,
                params={"email": other_email},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200
        assert r.json()["user_email"] == other_email
        call_kw = mock_get_by_user.call_args[1]
        assert call_kw["user_email"] == other_email
    finally:
        del app.dependency_overrides[get_current_user]
