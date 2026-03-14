"""Admin routes: GET /admin/users (list with counts), PATCH /admin/users/{id} (role, is_active, last-admin guard)."""

import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

# Prefer same import path as app (main + api.deps when pythonpath=app) so overrides apply
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from main import app
    import api.deps as deps_module
    from database import get_db, async_session
    from models.models import User
except ImportError:
    from app.main import app
    import app.api.deps as deps_module
    from app.database import get_db, async_session
    from app.models.models import User

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


# --- PATCH /admin/users/{id} tests: override get_db so session uses same loop as test ---

def _make_session_factory():
    try:
        from config import settings
    except ImportError:
        from app.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    eng = create_async_engine(settings.database_url, echo=False)
    return async_sessionmaker(eng, expire_on_commit=False)


async def _ensure_user_async(session_factory, email: str, role: str, is_active: bool = True) -> User:
    async with session_factory() as session:
        r = await session.execute(select(User).where(User.email == email))
        u = r.scalar_one_or_none()
        if u:
            u.role = role
            u.is_active = is_active
            await session.commit()
            await session.refresh(u)
            return u
        u = User(email=email, role=role, is_active=is_active)
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u


@pytest.mark.asyncio
async def test_patch_promote_user_to_admin_200():
    """PATCH promote user to admin returns 200 (ADMN-03)."""
    from httpx import ASGITransport, AsyncClient
    session_factory = _make_session_factory()
    user = await _ensure_user_async(session_factory, "patch_promote@example.com", "user")
    async def override_get_db():
        async with session_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    async def override_require_admin_ok():
        return user
    app.dependency_overrides[deps_module.require_admin] = override_require_admin_ok
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(f"{ADMIN_USERS}/{user.id}", json={"role": "admin"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"
    finally:
        del app.dependency_overrides[get_db]
        del app.dependency_overrides[deps_module.require_admin]


@pytest.mark.asyncio
async def test_patch_user_not_found_404():
    """PATCH /admin/users/{id} with non-existent id returns 404."""
    from httpx import ASGITransport, AsyncClient
    session_factory = _make_session_factory()
    async def override_get_db():
        async with session_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    mock_admin = MagicMock()
    mock_admin.id = 1
    mock_admin.email = "admin@example.com"
    mock_admin.role = "admin"
    mock_admin.is_active = True
    async def override_require_admin_ok():
        return mock_admin
    app.dependency_overrides[deps_module.require_admin] = override_require_admin_ok
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(f"{ADMIN_USERS}/999999", json={"role": "admin"})
        assert resp.status_code == 404
    finally:
        del app.dependency_overrides[get_db]
        del app.dependency_overrides[deps_module.require_admin]


@pytest.mark.asyncio
async def test_patch_demote_admin_when_another_admin_exists_200():
    """PATCH demote admin to user when another admin exists returns 200 (ADMN-04)."""
    from httpx import ASGITransport, AsyncClient
    session_factory = _make_session_factory()
    admin1 = await _ensure_user_async(session_factory, "patch_demote_admin1@example.com", "admin")
    admin2 = await _ensure_user_async(session_factory, "patch_demote_admin2@example.com", "admin")
    async def override_get_db():
        async with session_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    async def override_require_admin_ok():
        return admin2
    app.dependency_overrides[deps_module.require_admin] = override_require_admin_ok
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(f"{ADMIN_USERS}/{admin1.id}", json={"role": "user"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "user"
    finally:
        del app.dependency_overrides[get_db]
        del app.dependency_overrides[deps_module.require_admin]


@pytest.mark.asyncio
async def test_patch_demote_last_admin_400():
    """PATCH demote last admin returns 400 (ADMN-04)."""
    from httpx import ASGITransport, AsyncClient
    session_factory = _make_session_factory()
    last_admin = await _ensure_user_async(session_factory, "patch_last_admin@example.com", "admin")
    async with session_factory() as session:
        r = await session.execute(select(User).where(User.id != last_admin.id, User.role == "admin"))
        for o in r.scalars().all():
            o.role = "user"
        await session.commit()
    async def override_get_db():
        async with session_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    async def override_require_admin_ok():
        return last_admin
    app.dependency_overrides[deps_module.require_admin] = override_require_admin_ok
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(f"{ADMIN_USERS}/{last_admin.id}", json={"role": "user"})
        assert resp.status_code == 400
        assert "last admin" in (resp.json().get("detail") or "").lower()
    finally:
        del app.dependency_overrides[get_db]
        del app.dependency_overrides[deps_module.require_admin]


@pytest.mark.asyncio
async def test_patch_disable_user_200():
    """PATCH disable user returns 200 (ADMN-05)."""
    from httpx import ASGITransport, AsyncClient
    session_factory = _make_session_factory()
    user = await _ensure_user_async(session_factory, "patch_disable_user@example.com", "user")
    async def override_get_db():
        async with session_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    async def override_require_admin_ok():
        return user
    app.dependency_overrides[deps_module.require_admin] = override_require_admin_ok
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(f"{ADMIN_USERS}/{user.id}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
    finally:
        del app.dependency_overrides[get_db]
        del app.dependency_overrides[deps_module.require_admin]


@pytest.mark.asyncio
async def test_patch_disable_last_admin_400():
    """PATCH disable last admin returns 400 (ADMN-05)."""
    from httpx import ASGITransport, AsyncClient
    session_factory = _make_session_factory()
    last_admin = await _ensure_user_async(session_factory, "patch_disable_last_admin@example.com", "admin")
    async with session_factory() as session:
        r = await session.execute(select(User).where(User.id != last_admin.id, User.role == "admin"))
        for o in r.scalars().all():
            o.role = "user"
        await session.commit()
    async def override_get_db():
        async with session_factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    async def override_require_admin_ok():
        return last_admin
    app.dependency_overrides[deps_module.require_admin] = override_require_admin_ok
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(f"{ADMIN_USERS}/{last_admin.id}", json={"is_active": False})
        assert resp.status_code == 400
        assert "last admin" in (resp.json().get("detail") or "").lower()
    finally:
        del app.dependency_overrides[get_db]
        del app.dependency_overrides[deps_module.require_admin]
