"""Auth tests for POST /api/v1/upload/csv: 401 without token, 403 for non-admin, 200 for admin (ADMN-08)."""

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

# Same module the upload route uses for require_admin (so override key matches)
try:
    from app.api.routes import upload as upload_routes
except ImportError:
    from api.routes import upload as upload_routes

client = TestClient(app)
UPLOAD_CSV = "/api/v1/upload/csv"


def test_upload_no_token_returns_401():
    """POST /upload/csv without Authorization returns 401."""
    resp = client.post(UPLOAD_CSV, files={"file": ("x.csv", b"a;b", "text/csv")})
    assert resp.status_code == 401


def test_upload_user_token_returns_403():
    """POST /upload/csv with non-admin returns 403 (Admin required)."""
    async def override_require_admin_403():
        raise HTTPException(status_code=403, detail="Admin required")

    app.dependency_overrides[upload_routes.require_admin] = override_require_admin_403
    try:
        resp = client.post(
            UPLOAD_CSV,
            files={"file": ("x.csv", b"a;b", "text/csv")},
            headers={"Authorization": "Bearer any"},
        )
        assert resp.status_code == 403
    finally:
        del app.dependency_overrides[upload_routes.require_admin]


def test_upload_admin_token_returns_200():
    """POST /upload/csv with admin returns 200; CSV processing mocked."""
    mock_admin = MagicMock()
    mock_admin.email = "admin@example.com"
    mock_admin.role = "admin"
    mock_admin.is_active = True

    async def override_require_admin_ok():
        return mock_admin

    app.dependency_overrides[upload_routes.require_admin] = override_require_admin_ok
    try:
        with patch("api.routes.upload.process_csv_upload", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"created": 0, "updated": 0, "errors": []}
            resp = client.post(
                UPLOAD_CSV,
                files={"file": ("x.csv", b"name;type;period", "text/csv")},
                headers={"Authorization": "Bearer any"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "created" in data or "updated" in data or "errors" in data
            mock_process.assert_called_once()
    finally:
        del app.dependency_overrides[upload_routes.require_admin]
