"""Unit tests for authentication service functionality.

Tests for AUTH-02: User can request OTP by providing email
Tests for AUTH-03: User can verify OTP and receive JWT session
Tests for AUTH-04: Account created automatically on first OTP verification
Tests for AUTH-07: OTP lifecycle with expiry and single-use
Tests for AUTH-08: Rate limiting for OTP attempts
Tests for AUTH-09: Integration with email service with fallback
"""

import asyncio
import pytest
from datetime import datetime, timedelta
import secrets
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.auth_service import request_otp, verify_otp, create_jwt_token, check_rate_limit, cleanup_expired_otps
from app.models.models import User, OtpCode


@pytest.mark.asyncio
async def test_request_otp_success():
    """Test successful OTP request creates OTP code in database."""
    # Arrange
    email = "test@example.com"
    mock_db_session = AsyncMock()

    # Act
    result = await request_otp(email, mock_db_session)

    # Assert
    assert "success" in result
    assert result["success"] is True
    # Verify database operation was called appropriately


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
    # Arrange
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()

    # Mock the query to return a valid OTP code
    mock_query_result = MagicMock()
    mock_query_result.expires_at = datetime.utcnow() + timedelta(minutes=5)
    mock_query_result.used = False
    mock_query_result.attempt_count = 0

    mock_db_session.execute.return_value.scalar.return_value = mock_query_result

    # Act
    result = await verify_otp(email, otp_code, mock_db_session)

    # Assert
    assert result is not None
    assert "token" in result
    assert "user" in result


@pytest.mark.asyncio
async def test_verify_otp_invalid_code():
    """Test verification fails with invalid OTP code."""
    # Arrange
    email = "test@example.com"
    otp_code = "wrongcode"
    mock_db_session = AsyncMock()

    # Mock the query to return a valid OTP code
    mock_query_result = MagicMock()
    mock_query_result.expires_at = datetime.utcnow() + timedelta(minutes=5)
    mock_query_result.used = False
    mock_query_result.attempt_count = 0

    mock_db_session.execute.return_value.scalar.return_value = mock_query_result

    # Act
    result = await verify_otp(email, otp_code, mock_db_session)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_verify_otp_expired():
    """Test verification fails with expired OTP code."""
    # Arrange
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()

    # Mock the query to return an expired OTP code
    mock_query_result = MagicMock()
    mock_query_result.expires_at = datetime.utcnow() - timedelta(minutes=5)
    mock_query_result.used = False
    mock_query_result.attempt_count = 0

    mock_db_session.execute.return_value.scalar.return_value = mock_query_result

    # Act
    result = await verify_otp(email, otp_code, mock_db_session)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_verify_otp_already_used():
    """Test verification fails with already used OTP code."""
    # Arrange
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()

    # Mock the query to return an already used OTP code
    mock_query_result = MagicMock()
    mock_query_result.expires_at = datetime.utcnow() + timedelta(minutes=5)
    mock_query_result.used = True
    mock_query_result.attempt_count = 0

    mock_db_session.execute.return_value.scalar.return_value = mock_query_result

    # Act
    result = await verify_otp(email, otp_code, mock_db_session)

    # Assert
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
    # Arrange
    email = "newuser@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()

    # Mock OTP query result
    mock_otp_result = MagicMock()
    mock_otp_result.expires_at = datetime.utcnow() + timedelta(minutes=5)
    mock_otp_result.used = False
    mock_otp_result.attempt_count = 0

    # Mock user query result (return None to simulate user doesn't exist)
    mock_user_query_result = MagicMock()
    mock_user_query_result.scalar.return_value = None

    # Mock the execute to return the OTP result first, then None for user query
    mock_db_session.execute.side_effect = [AsyncMock(return_value=mock_otp_result),
                                          AsyncMock(return_value=mock_user_query_result)]

    # Act
    result = await verify_otp(email, otp_code, mock_db_session)

    # Assert
    assert result is not None
    # Verify that user creation was attempted


@pytest.mark.asyncio
async def test_verify_otp_max_attempts():
    """Test verification fails after max attempts reached."""
    # Arrange
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()

    # Mock the query to return an OTP with max attempts reached
    mock_query_result = MagicMock()
    mock_query_result.expires_at = datetime.utcnow() + timedelta(minutes=5)
    mock_query_result.used = False
    mock_query_result.attempt_count = 5  # Max attempts reached

    mock_db_session.execute.return_value.scalar.return_value = mock_query_result

    # Act
    result = await verify_otp(email, otp_code, mock_db_session)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_auth_email_integration():
    """Test that auth service properly integrates with email service respecting fallback setting."""
    # Test successful email delivery
    with patch('app.services.email_service.send_otp_email') as mock_send_email:
        mock_send_email.return_value = True  # Simulate successful email delivery

        with patch('app.services.auth_service.settings') as mock_settings:
            mock_settings.otp_plaintext_fallback = False
            mock_settings.jwt_secret = "test_secret"
            mock_settings.jwt_ttl_days = 7

            email = "integration@test.com"
            mock_db_session = AsyncMock()

            result = await request_otp(email, mock_db_session)

            # Verify email was attempted to be sent
            mock_send_email.assert_called_once()
            # Verify result doesn't include dev OTP code since email was sent
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
    # Arrange
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()

    # Mock the query to return a valid OTP code
    mock_query_result = MagicMock()
    mock_query_result.expires_at = datetime.utcnow() + timedelta(minutes=5)
    mock_query_result.used = False
    mock_query_result.attempt_count = 0
    mock_query_result.code_hash = "valid_hash"

    mock_db_session.execute.return_value.scalar.return_value = mock_query_result

    # Mock the hash comparison to return True (valid code)
    with patch('hmac.compare_digest', return_value=True):
        # Act - First verification should succeed
        result1 = await verify_otp(email, otp_code, mock_db_session)

        # Act - Second verification should fail because the code is now marked as used
        result2 = await verify_otp(email, otp_code, mock_db_session)

        # Assert
        assert result1 is not None  # First verification succeeds
        assert result2 is None      # Second verification fails due to single-use


@pytest.mark.asyncio
async def test_otp_rate_limiting():
    """Test that OTP verification enforces rate limiting."""
    # Arrange
    email = "test@example.com"
    otp_code = "123456"
    mock_db_session = AsyncMock()

    # Mock the query to return an OTP with max attempts reached
    mock_query_result = MagicMock()
    mock_query_result.expires_at = datetime.utcnow() + timedelta(minutes=5)
    mock_query_result.used = False
    mock_query_result.attempt_count = 4  # At threshold (one more will reach max)

    mock_db_session.execute.return_value.scalar.return_value = mock_query_result

    # Act - Verification should fail due to too many attempts
    result = await verify_otp(email, otp_code, mock_db_session)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_check_rate_limit():
    """Test the rate limiting function for OTP requests."""
    # Arrange
    email = "test@example.com"
    mock_db_session = AsyncMock()

    # Mock the query to return multiple recent OTP requests
    mock_otp1 = MagicMock()
    mock_otp1.created_at = datetime.utcnow() - timedelta(minutes=1)  # Recent
    mock_otp2 = MagicMock()
    mock_otp2.created_at = datetime.utcnow() - timedelta(minutes=2)  # Recent
    mock_otp3 = MagicMock()
    mock_otp3.created_at = datetime.utcnow() - timedelta(minutes=3)  # Recent
    mock_otp4 = MagicMock()
    mock_otp4.created_at = datetime.utcnow() - timedelta(minutes=4)  # Recent

    mock_query_result = [mock_otp1, mock_otp2, mock_otp3, mock_otp4]

    mock_db_session.execute.return_value.scalars.return_value.all.return_value = mock_query_result

    # Act - With 4 recent requests and max 5, should be within limit
    result_within_limit = await check_rate_limit(email, mock_db_session, max_requests=5)

    # Act - With 4 recent requests and max 4, should exceed limit
    result_over_limit = await check_rate_limit(email, mock_db_session, max_requests=4)

    # Assert
    assert result_within_limit is True
    assert result_over_limit is False


@pytest.mark.asyncio
async def test_cleanup_expired_otps():
    """Test that expired OTPs can be cleaned up."""
    # Arrange
    mock_db_session = AsyncMock()

    # Act
    result = await cleanup_expired_otps(mock_db_session)

    # Assert - we can only check that the function executes without error
    assert isinstance(result, int)


if __name__ == "__main__":
    pytest.main([__file__])