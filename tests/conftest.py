"""
Shared fixtures for Phase 4 auth and admin tests.

Provides: client, db (async session), auth_headers_user, auth_headers_admin.
Uses real JWT from auth_service so 401/403 on invalid or missing token are testable.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Docker-safe imports. Prefer same path as app (models.models) to avoid duplicate SQLAlchemy mappers.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from main import app
    from database import async_session
    from models.models import User
    from services.auth_service import create_jwt_token
except ImportError:
    from app.main import app
    from app.database import async_session
    from app.models.models import User
    from app.services.auth_service import create_jwt_token


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient for the app."""
    return TestClient(app)


# Emails used for test users; created once per module scope so JWTs match existing DB rows
TEST_USER_EMAIL = "phase4_user@example.com"
TEST_ADMIN_EMAIL = "phase4_admin@example.com"


async def _ensure_user(session: AsyncSession, email: str, role: str) -> User:
    """Create or get existing user by email."""
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.role = role
        user.is_active = True
        await session.commit()
        await session.refresh(user)
        return user
    user = User(email=email, role=role, is_active=True)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture(scope="module")
async def auth_headers_user():
    """Authorization headers with valid JWT for a user (role=user)."""
    async with async_session() as session:
        user = await _ensure_user(session, TEST_USER_EMAIL, "user")
        token = create_jwt_token(user.email, user.role)
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
async def auth_headers_admin():
    """Authorization headers with valid JWT for an admin (role=admin)."""
    async with async_session() as session:
        user = await _ensure_user(session, TEST_ADMIN_EMAIL, "admin")
        token = create_jwt_token(user.email, user.role)
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def db() -> AsyncSession:
    """Async DB session for creating test data (e.g. User, Order, Commemoration)."""
    async with async_session() as session:
        yield session
