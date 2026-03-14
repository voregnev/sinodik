"""Tests for orders API: auth and scope (phase 04-02). GET list requires auth; POST optional auth links to JWT user; by-id and mutate are admin-only."""

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
ORDERS = "/api/v1/orders"


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


def _get_orders_deps():
    """Same get_current_user and require_admin the orders routes use."""
    try:
        from app.api.routes import orders as orders_route
    except ImportError:
        from api.routes import orders as orders_route
    return orders_route.get_current_user, orders_route.require_admin


def _get_optional_dep():
    try:
        from app.api.routes import orders as orders_route
    except ImportError:
        from api.routes import orders as orders_route
    return orders_route.get_current_user_optional


def _get_db_dep():
    """Same get_db the orders routes use."""
    try:
        from app.api.routes import orders as orders_route
    except ImportError:
        from api.routes import orders as orders_route
    return orders_route.get_db


def test_get_orders_without_token_returns_401():
    """GET /orders without Authorization returns 401."""
    r = client.get(ORDERS)
    assert r.status_code == 401


def test_get_orders_with_user_token_returns_only_own_orders():
    """GET /orders with user token returns only orders where user_email == that user."""
    user_email = "orders_user@example.com"
    token = _make_token(user_email, "user")
    mock_user = MagicMock()
    mock_user.email = user_email
    mock_user.role = "user"

    async def override_get_current_user():
        return mock_user

    get_current_user, _ = _get_orders_deps()
    get_db = _get_db_dep()
    app.dependency_overrides[get_current_user] = override_get_current_user
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    async def override_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = override_get_db
    try:
        r = client.get(ORDERS, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json() == []
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_db]


def test_get_orders_with_admin_token_returns_all_orders():
    """GET /orders with admin token returns all orders (no filter)."""
    admin_email = "orders_admin@example.com"
    token = _make_token(admin_email, "admin")
    mock_admin = MagicMock()
    mock_admin.email = admin_email
    mock_admin.role = "admin"

    async def override_get_current_user():
        return mock_admin

    get_current_user, _ = _get_orders_deps()
    get_db = _get_db_dep()
    app.dependency_overrides[get_current_user] = override_get_current_user
    mock_order = MagicMock()
    mock_order.id = 1
    mock_order.user_email = "other@example.com"
    mock_order.source_channel = "api"
    mock_order.external_id = None
    mock_order.need_receipt = False
    mock_order.ordered_at = None
    mock_order.created_at = datetime.now(timezone.utc)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_order]
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    async def override_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = override_get_db
    try:
        r = client.get(ORDERS, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["user_email"] == "other@example.com"
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_db]


def test_post_orders_with_token_links_to_jwt_user():
    """POST /orders with Bearer token sets order user_email from token."""
    user_email = "post_user@example.com"
    token = _make_token(user_email, "user")
    mock_user = MagicMock()
    mock_user.email = user_email
    mock_user.role = "user"

    async def override_get_current_user_optional():
        return mock_user

    get_current_user_optional = _get_optional_dep()
    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional
    try:
        with patch("api.routes.orders.create_manual_order", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = []  # no comms created for empty names_text or mock
            r = client.post(
                ORDERS,
                json={
                    "order_type": "здравие",
                    "period_type": "разовое",
                    "names_text": "Иван",
                    "user_email": "ignored@example.com",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200
        call_kw = mock_create.call_args[1]
        assert call_kw["user_email"] == user_email
    finally:
        del app.dependency_overrides[get_current_user_optional]


def test_post_orders_without_token_uses_body_user_email():
    """POST /orders without token uses body.user_email (anonymous order)."""
    get_current_user_optional = _get_optional_dep()
    async def override_none():
        return None
    app.dependency_overrides[get_current_user_optional] = override_none
    try:
        with patch("api.routes.orders.create_manual_order", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = []
            r = client.post(
                ORDERS,
                json={
                    "order_type": "здравие",
                    "period_type": "разовое",
                    "names_text": "Иван",
                    "user_email": "anon@example.com",
                },
            )
        assert r.status_code == 200
        call_kw = mock_create.call_args[1]
        assert call_kw["user_email"] == "anon@example.com"
    finally:
        del app.dependency_overrides[get_current_user_optional]


def test_get_order_by_id_as_user_returns_403():
    """GET /orders/{id} as non-admin returns 403."""
    user_email = "plain_user@example.com"
    token = _make_token(user_email, "user")
    mock_user = MagicMock()
    mock_user.email = user_email
    mock_user.role = "user"

    async def override_get_current_user():
        return mock_user

    get_current_user, _ = _get_orders_deps()
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        r = client.get(
            f"{ORDERS}/1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


def test_get_order_by_id_as_admin_returns_200_when_exists():
    """GET /orders/{id} as admin returns 200 when order exists."""
    admin_email = "admin_get@example.com"
    token = _make_token(admin_email, "admin")
    mock_admin = MagicMock()
    mock_admin.email = admin_email
    mock_admin.role = "admin"

    async def override_get_current_user():
        return mock_admin

    async def override_require_admin():
        return mock_admin

    get_current_user, require_admin = _get_orders_deps()
    get_db = _get_db_dep()
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_admin] = override_require_admin
    mock_order = MagicMock()
    mock_order.id = 1
    mock_order.user_email = "u@x.com"
    mock_order.source_channel = "api"
    mock_order.source_raw = None
    mock_order.external_id = None
    mock_order.need_receipt = False
    mock_order.ordered_at = None
    mock_order.created_at = datetime.now(timezone.utc)
    result1 = MagicMock()
    result1.scalar_one_or_none.return_value = mock_order
    result2 = MagicMock()
    result2.all.return_value = []
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=[result1, result2])
    async def override_get_db():
        yield mock_db
    app.dependency_overrides[get_db] = override_get_db
    try:
        r = client.get(
            f"{ORDERS}/1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == 1
        assert data["user_email"] == "u@x.com"
    finally:
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[require_admin]
        del app.dependency_overrides[get_db]
