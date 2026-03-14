"""
Tests for email service functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.email_service import send_otp_email


@pytest.mark.asyncio
async def test_send_otp_email():
    """
    Test that OTP emails can be sent successfully.
    """
    # Mock the aiosmtplib.SMTP class
    with patch('aiosmtplib.SMTP') as mock_smtp_class:
        mock_smtp_instance = AsyncMock()
        mock_smtp_class.return_value.__aenter__.return_value = mock_smtp_instance
        mock_smtp_instance.starttls = AsyncMock()
        mock_smtp_instance.login = AsyncMock()
        mock_smtp_instance.send_message = AsyncMock()

        # Mock settings
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
async def test_smtp_fallback_mechanism():
    """
    Test that SMTP fallback mechanism works when SMTP fails and fallback is enabled.
    """
    # Mock the aiosmtplib.SMTP class to raise an exception
    with patch('aiosmtplib.SMTP') as mock_smtp_class:
        mock_smtp_instance = AsyncMock()
        mock_smtp_class.return_value.__aenter__.return_value = mock_smtp_instance
        mock_smtp_instance.starttls = AsyncMock()
        mock_smtp_instance.login = AsyncMock()
        mock_smtp_instance.send_message = AsyncMock(side_effect=Exception("SMTP Failed"))

        # Capture print statements using a custom mock
        captured_outputs = []
        original_print = print

        def mock_print(*args, **kwargs):
            captured_outputs.append(" ".join(str(arg) for arg in args))

        import builtins
        builtins.print = mock_print

        try:
            # Mock settings with fallback enabled
            with patch('app.services.email_service.settings') as mock_settings:
                mock_settings.smtp_host = "smtp.example.com"
                mock_settings.smtp_port = 587
                mock_settings.smtp_username = "test_user"
                mock_settings.smtp_password = "test_pass"
                mock_settings.smtp_from_address = "noreply@example.com"
                mock_settings.smtp_use_tls = True
                mock_settings.smtp_use_ssl = False
                mock_settings.smtp_validate_certs = True
                mock_settings.otp_plaintext_fallback = True  # Enable fallback

                result = await send_otp_email("test@example.com", "123456")

                assert result is True  # Should return True due to fallback
                assert len(captured_outputs) > 0
                # Check if the fallback message was printed
                fallback_messages = [msg for msg in captured_outputs if "PLAINTEXT FALLBACK" in msg]
                assert len(fallback_messages) > 0
        finally:
            # Restore original print
            builtins.print = original_print