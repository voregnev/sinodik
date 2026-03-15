"""
Tests for email service functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.email_service import send_otp_email


def _mock_smtp_context(mock_smtp_class, mock_instance):
    """Make SMTP() return one mock that is also the async with target; starttls/login/send_message awaitable."""
    mock_smtp_class.return_value = mock_instance
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)
    mock_instance.starttls = AsyncMock()
    mock_instance.login = AsyncMock()
    mock_instance.send_message = AsyncMock()


@pytest.mark.asyncio
async def test_send_otp_email():
    """
    Test that OTP emails can be sent successfully.
    """
    with patch('aiosmtplib.SMTP') as mock_smtp_class:
        mock_smtp_instance = MagicMock()
        _mock_smtp_context(mock_smtp_class, mock_smtp_instance)

        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test_user"
            mock_settings.smtp_password = "test_pass"
            mock_settings.smtp_from_address = "noreply@example.com"
            mock_settings.smtp_use_tls = True
            mock_settings.smtp_use_ssl = False
            mock_settings.smtp_validate_certs = True
            mock_settings.otp_plaintext_fallback = False

            result = await send_otp_email("test@example.com", "123456")

            assert result is True
            mock_smtp_class.assert_called_once()
            mock_smtp_instance.send_message.assert_called_once()


def test_smtp_fallback():
    """
    Test SMTP fallback mechanisms.
    """
    # This test will verify that when SMTP fails and fallback is enabled,
    # the system handles it gracefully
    import asyncio
    from unittest.mock import MagicMock

    # Since we can't easily mock the entire aiosmtplib behavior in a sync test,
    # we'll test the fallback scenario in an async test instead
    pass


@pytest.mark.asyncio
async def test_smtp_fallback_mechanism(caplog):
    """
    Test that SMTP fallback mechanism works when SMTP fails and fallback is enabled.
    """
    with patch('aiosmtplib.SMTP') as mock_smtp_class:
        mock_smtp_instance = MagicMock()
        _mock_smtp_context(mock_smtp_class, mock_smtp_instance)
        mock_smtp_instance.send_message = AsyncMock(side_effect=Exception("SMTP Failed"))

        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test_user"
            mock_settings.smtp_password = "test_pass"
            mock_settings.smtp_from_address = "noreply@example.com"
            mock_settings.smtp_use_tls = True
            mock_settings.smtp_use_ssl = False
            mock_settings.smtp_validate_certs = True
            mock_settings.otp_plaintext_fallback = True

            with caplog.at_level("WARNING"):
                result = await send_otp_email("test@example.com", "123456")

            assert result is True
            assert any("PLAINTEXT FALLBACK" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_smtp_no_fallback_when_disabled():
    """
    Test that SMTP errors are raised when fallback is disabled.
    """
    with patch('aiosmtplib.SMTP') as mock_smtp_class:
        mock_smtp_instance = MagicMock()
        _mock_smtp_context(mock_smtp_class, mock_smtp_instance)
        mock_smtp_instance.send_message = AsyncMock(side_effect=Exception("SMTP Failed"))

        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test_user"
            mock_settings.smtp_password = "test_pass"
            mock_settings.smtp_from_address = "noreply@example.com"
            mock_settings.smtp_use_tls = True
            mock_settings.smtp_use_ssl = False
            mock_settings.smtp_validate_certs = True
            mock_settings.otp_plaintext_fallback = False

            with pytest.raises(Exception, match=r"Failed to send OTP email|SMTP Failed"):
                await send_otp_email("test@example.com", "123456")


@pytest.mark.asyncio
async def test_auth_email_integration():
    """
    Test that auth service properly integrates with email service respecting the plaintext fallback setting.
    """
    with patch('aiosmtplib.SMTP') as mock_smtp_class:
        mock_smtp_instance = MagicMock()
        _mock_smtp_context(mock_smtp_class, mock_smtp_instance)
        mock_smtp_instance.send_message = AsyncMock(side_effect=Exception("SMTP Failed"))

        # Mock settings with fallback enabled
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = ""
            mock_settings.smtp_password = ""
            mock_settings.smtp_from_address = "noreply@example.com"
            mock_settings.smtp_use_tls = False
            mock_settings.smtp_use_ssl = False
            mock_settings.smtp_validate_certs = True
            mock_settings.otp_plaintext_fallback = True  # Enable fallback

            # Should succeed despite SMTP error because of fallback
            result = await send_otp_email("test@example.com", "123456")
            assert result is True