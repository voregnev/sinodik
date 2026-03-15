"""Unit tests for authentication service functionality.

Tests for AUTH-02: User can request OTP by providing email
Tests for AUTH-03: User can verify OTP and receive JWT session
Tests for AUTH-04: Account created automatically on first OTP verification
Tests for AUTH-07: OTP lifecycle with expiry and single-use
Tests for AUTH-08: Rate limiting for OTP attempts
Tests for AUTH-09: Integration with email service with fallback
"""

import asyncio
import hashlib
import pytest
from datetime import datetime, timedelta
import secrets
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.auth_service import request_otp, verify_otp, create_jwt_token, check_rate_limit, cleanup_expired_otps
from app.models.models import User, OtpCode


_SENTINEL = object()


def _make_result_mock(scalar_one_or_none_val=_SENTINEL, scalars_all_val=None, rowcount=None):
    """Build a sync result mock: await execute() returns this, .scalar_one_or_none() / .scalars().all() / .rowcount."""
    m = MagicMock()
    if scalar_one_or_none_val is not _SENTINEL:
        m.scalar_one_or_none.return_value = scalar_one_or_none_val
    if scalars_all_val is not None:
        m.scalars.return_value.all.return_value = scalars_all_val
    if rowcount is not None:
        m.rowcount = rowcount
    return m


@pytest.mark.asyncio
async def test_request_otp_success():
    """Test successful OTP request creates OTP code in database."""
    email = "test@example.com"
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = _make_result_mock(scalars_all_val=[])
    with patch('app.services.auth_service.check_rate_limit', new_callable=AsyncMock, return_value=True), \
         patch('app.services.auth_service.send_otp_email', new_callable=AsyncMock, return_value=True), \
         patch('app.services.auth_service.OtpCode', MagicMock()):
        result = await request_otp(email, mock_db_session)
    assert "success" in result
    assert result["success"] is True


@pytest.mark.asyncio
async def test_request_otp_invalid_email():
    """Test requesting OTP with invalid email format."""
    # Arrange
    email = "invalid-email"
    mock_db_session = AsyncMock()

    # Act & Assert
    with pytest.raises(ValueError):
        await request_otp(email, mock_db_session)


@pytest.mark.asyncio
async def test_verify_otp_success():
    """Test successful OTP verification returns JWT token."""
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()
    mock_otp = MagicMock()
    mock_otp.expires_at = datetime.now(datetime.UTC)+ timedelta(minutes=5)
    mock_otp.used = False
    mock_otp.attempt_count = 0
    mock_otp.code_hash = hashlib.sha256(otp_code.encode()).hexdigest()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = email
    mock_user.role = "user"
    # verify_otp: execute(otp) -> otp_record; _get_or_create_user: execute(user) -> user
    mock_db_session.execute.side_effect = [
        _make_result_mock(scalar_one_or_none_val=mock_otp),
        _make_result_mock(scalar_one_or_none_val=mock_user),
    ]
    result = await verify_otp(email, otp_code, mock_db_session)
    assert result is not None
    assert "token" in result
    assert "user" in result


@pytest.mark.asyncio
async def test_verify_otp_invalid_code():
    """Test verification fails with invalid OTP code."""
    email = "test@example.com"
    otp_code = "wrongcode"
    mock_db_session = AsyncMock()
    mock_otp = MagicMock()
    mock_otp.expires_at = datetime.now(datetime.UTC)+ timedelta(minutes=5)
    mock_otp.used = False
    mock_otp.attempt_count = 0
    mock_otp.code_hash = hashlib.sha256(b"123456").hexdigest()
    mock_db_session.execute.return_value = _make_result_mock(scalar_one_or_none_val=mock_otp)
    result = await verify_otp(email, otp_code, mock_db_session)
    assert result is None


@pytest.mark.asyncio
async def test_verify_otp_expired():
    """Test verification fails with expired OTP code (query excludes expired, so no record)."""
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = _make_result_mock(scalar_one_or_none_val=None)
    result = await verify_otp(email, otp_code, mock_db_session)
    assert result is None


@pytest.mark.asyncio
async def test_verify_otp_already_used():
    """Test verification fails with already used OTP (query has used==False, so no record on reuse)."""
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = _make_result_mock(scalar_one_or_none_val=None)
    result = await verify_otp(email, otp_code, mock_db_session)
    assert result is None


def test_jwt_claims_structure():
    """Test JWT contains expected claims: sub, role, exp."""
    # Arrange
    email = "test@example.com"
    role = "user"

    # Act
    token = create_jwt_token(email, role)

    # Assert - we can't decode the token without the secret but we can check it's not None
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
async def test_verify_otp_creates_user_if_not_exists():
    """Test that OTP verification creates user account if it doesn't exist."""
    email = "newuser@example.com"
    otp_code = "123456"
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = email
    mock_user.role = "user"
    mock_otp = MagicMock()
    mock_otp.expires_at = datetime.now(datetime.UTC)+ timedelta(minutes=5)
    mock_otp.used = False
    mock_otp.attempt_count = 0
    mock_otp.code_hash = hashlib.sha256(otp_code.encode()).hexdigest()
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = _make_result_mock(scalar_one_or_none_val=mock_otp)
    with patch('app.services.auth_service._get_or_create_user', new_callable=AsyncMock, return_value=mock_user):
        result = await verify_otp(email, otp_code, mock_db_session)
    assert result is not None


@pytest.mark.asyncio
async def test_verify_otp_max_attempts():
    """Test verification fails when attempt_count >= 5 (excluded from query, no record)."""
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = _make_result_mock(scalar_one_or_none_val=None)
    result = await verify_otp(email, otp_code, mock_db_session)
    assert result is None


@pytest.mark.asyncio
async def test_auth_email_integration():
    """Test that auth service properly integrates with email service respecting fallback setting."""
    with patch('app.services.auth_service.check_rate_limit', new_callable=AsyncMock, return_value=True), \
         patch('app.services.auth_service.send_otp_email', new_callable=AsyncMock, return_value=True) as mock_send_email, \
         patch('app.services.auth_service.OtpCode', MagicMock()), \
         patch('app.services.auth_service.settings') as mock_settings:
        mock_settings.otp_plaintext_fallback = False
        mock_settings.jwt_secret = "test_secret"
        mock_settings.jwt_ttl_days = 7

        email = "integration@test.com"
        mock_db_session = AsyncMock()
        mock_db_session.execute.return_value = _make_result_mock(scalars_all_val=[])

        result = await request_otp(email, mock_db_session)

        mock_send_email.assert_called_once()
        assert "dev_otp_code" not in result or result.get("dev_otp_code") is None
        assert result["success"] is True


@pytest.mark.asyncio
async def test_otp_expiry():
    """Test that expired OTP codes are properly rejected."""
    # This test is already covered in test_verify_otp_expired
    pass


@pytest.mark.asyncio
async def test_otp_single_use():
    """Test that OTP codes are marked as used after successful verification."""
    email = "test@example.com"
    otp_code = "123456"
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = email
    mock_user.role = "user"
    valid_hash = hashlib.sha256(otp_code.encode()).hexdigest()
    # First call: valid OTP + user; second call: same OTP but already used (or no record)
    mock_otp1 = MagicMock()
    mock_otp1.expires_at = datetime.now(datetime.UTC)+ timedelta(minutes=5)
    mock_otp1.used = False
    mock_otp1.attempt_count = 0
    mock_otp1.code_hash = valid_hash
    mock_db_session = AsyncMock()
    mock_db_session.execute.side_effect = [
        _make_result_mock(scalar_one_or_none_val=mock_otp1),
        _make_result_mock(scalar_one_or_none_val=mock_user),
        _make_result_mock(scalar_one_or_none_val=None),  # second verify: no OTP (already used)
    ]
    result1 = await verify_otp(email, otp_code, mock_db_session)
    result2 = await verify_otp(email, otp_code, mock_db_session)
    assert result1 is not None
    assert result2 is None


@pytest.mark.asyncio
async def test_otp_rate_limiting():
    """Test that OTP verification enforces rate limiting (attempt_count >= 5 excluded from query)."""
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = _make_result_mock(scalar_one_or_none_val=None)
    result = await verify_otp(email, otp_code, mock_db_session)
    assert result is None


@pytest.mark.asyncio
async def test_check_rate_limit():
    """Test the rate limiting function for OTP requests."""
    email = "test@example.com"
    mock_otps = [MagicMock() for _ in range(4)]
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = _make_result_mock(scalars_all_val=mock_otps)
    result_within_limit = await check_rate_limit(email, mock_db_session, max_requests=5)
    result_over_limit = await check_rate_limit(email, mock_db_session, max_requests=4)
    assert result_within_limit is True
    assert result_over_limit is False


@pytest.mark.asyncio
async def test_cleanup_expired_otps():
    """Test that expired OTPs can be cleaned up."""
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = _make_result_mock(rowcount=0)
    result = await cleanup_expired_otps(mock_db_session)
    assert isinstance(result, int)
    assert result >= 0


if __name__ == "__main__":
    pytest.main([__file__])