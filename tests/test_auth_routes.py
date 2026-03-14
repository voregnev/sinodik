"""Integration tests for auth API: request-otp, verify-otp, GET /me (phase 03-02, USER-03)."""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock

import jwt
import pytest
from fastapi.testclient import TestClient

# Support both: run from project root (app as package) and from container (PYTHONPATH=/app)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from app.main import app
except ImportError:
    from main import app

client = TestClient(app)

AUTH_REQUEST_OTP = "/api/v1/auth/request-otp"
AUTH_VERIFY_OTP = "/api/v1/auth/verify-otp"
AUTH_ME = "/api/v1/auth/me"


def test_request_otp_valid_email_returns_202_and_message():
    """Valid email returns 202 and body has 'message'."""
    with patch("services.auth_service.settings") as mock_settings, \
         patch("services.auth_service.check_rate_limit", new_callable=AsyncMock, return_value=True):
        mock_settings.otp_plaintext_fallback = True
        resp = client.post(AUTH_REQUEST_OTP, json={"email": "auth_routes_test@example.com"})
    assert resp.status_code == 202
    data = resp.json()
    assert "message" in data


def test_request_otp_invalid_email_returns_400():
    """Invalid email returns 400."""
    resp = client.post(AUTH_REQUEST_OTP, json={"email": "not-an-email"})
    assert resp.status_code == 400


def test_request_otp_rate_limit_returns_429():
    """When auth_service returns rate limit message, endpoint returns 429."""
    with patch("services.auth_service.check_rate_limit", new_callable=AsyncMock, return_value=False):
        r = client.post(AUTH_REQUEST_OTP, json={"email": "ratelimit@example.com"})
    assert r.status_code == 429
    assert "Rate limit" in r.json().get("detail", "")


def test_verify_otp_success_returns_200_with_token_and_user():
    """When verify_otp returns token and user, endpoint returns 200 with token and user."""
    email = "verify_success_test@example.com"
    fake_result = {"token": "fake-jwt", "user": {"id": 1, "email": email, "role": "user"}}
    with patch("api.routes.auth.verify_otp", new_callable=AsyncMock, return_value=fake_result):
        r = client.post(AUTH_VERIFY_OTP, json={"email": email, "code": "123456"})
    assert r.status_code == 200
    vdata = r.json()
    assert vdata["token"] == "fake-jwt"
    assert vdata["user"]["email"] == email
    assert "role" in vdata["user"]


def test_verify_otp_invalid_code_returns_401():
    """When verify_otp returns None, endpoint returns 401 with detail 'Invalid or expired code'."""
    with patch("api.routes.auth.verify_otp", new_callable=AsyncMock, return_value=None):
        r = client.post(AUTH_VERIFY_OTP, json={"email": "someone@example.com", "code": "000000"})
    assert r.status_code == 401
    assert r.json().get("detail") == "Invalid or expired code"


def test_me_without_auth_returns_401():
    """GET /api/v1/auth/me without Authorization header returns 401 (USER-03: logout = discard JWT)."""
    r = client.get(AUTH_ME)
    assert r.status_code == 401


def test_me_with_valid_token_returns_200_with_user():
    """GET /api/v1/auth/me with valid Bearer returns 200 with id, email, role, is_active."""
    try:
        from config import settings
        from api.deps import get_current_user
    except ImportError:
        from app.config import settings
        from app.api.deps import get_current_user
    token = jwt.encode(
        {"sub": "me_valid_test@example.com", "role": "user",
         "exp": datetime.now(timezone.utc) + timedelta(days=1),
         "iat": datetime.now(timezone.utc)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    mock_user = MagicMock()
    mock_user.id = 42
    mock_user.email = "me_valid_test@example.com"
    mock_user.role = "user"
    mock_user.is_active = True

    async def override_get_current_user():
        return mock_user
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        r = client.get(AUTH_ME, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        me_data = r.json()
        assert me_data["id"] == 42
        assert me_data["email"] == "me_valid_test@example.com"
        assert me_data["role"] == "user"
        assert me_data["is_active"] is True
    finally:
        del app.dependency_overrides[get_current_user]


def test_me_with_expired_or_malformed_token_returns_401():
    """GET /api/v1/auth/me with expired or malformed token returns 401."""
    # Malformed token
    r = client.get(AUTH_ME, headers={"Authorization": "Bearer invalid-token"})
    assert r.status_code == 401
    # Expired token (same secret as app)
    try:
        from config import settings
    except ImportError:
        from app.config import settings
    payload = {
        "sub": "expired@example.com",
        "role": "user",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    r2 = client.get(AUTH_ME, headers={"Authorization": f"Bearer {expired_token}"})
    assert r2.status_code == 401
