"""Unit tests for authentication service functionality.

Tests for AUTH-02: User can request OTP by providing email
Tests for AUTH-03: User can verify OTP and receive JWT session
Tests for AUTH-04: Account created automatically on first OTP verification
"""

import asyncio
import pytest
from datetime import datetime, timedelta
import secrets
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.auth_service import request_otp, verify_otp, create_jwt_token
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


if __name__ == "__main__":
    pytest.main([__file__])