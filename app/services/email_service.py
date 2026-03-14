"""
Email service for sending OTP codes via SMTP.
"""
import asyncio
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import aiosmtplib
from app.config import settings


class EmailService:
    """Service for sending emails via SMTP with fallback options."""

    def __init__(self):
        """Initialize the email service with configuration."""
        pass

    async def send_otp_email(self, recipient_email: str, otp_code: str) -> bool:
        """
        Send an OTP code to the specified email address via SMTP.

        Args:
            recipient_email: The email address to send the OTP to
            otp_code: The OTP code to send

        Returns:
            True if email was sent successfully, False otherwise

        Raises:
            Exception: If SMTP delivery fails and fallback is not enabled
        """
        subject = "Your OTP Code"
        body_text = f"""Hello,

Your OTP code is: {otp_code}

Please use this code to complete your authentication.

This code will expire in 10 minutes.

Best regards,
Sinodic Team
"""

        msg = MIMEMultipart()
        msg['From'] = settings.smtp_from_address
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Add plain text part
        msg.attach(MIMEText(body_text, 'plain'))

        try:
            # Determine SMTP host and port from settings
            smtp_host = settings.smtp_host
            smtp_port = settings.smtp_port
            smtp_username = settings.smtp_username
            smtp_password = settings.smtp_password

            # Determine if SSL/TLS should be used
            use_tls = settings.smtp_use_tls
            use_ssl = settings.smtp_use_ssl

            # Create SMTP client based on configuration
            if use_ssl:
                smtp_client = aiosmtplib.SMTP(
                    hostname=smtp_host,
                    port=smtp_port,
                    use_tls=True,
                    validate_certs=settings.smtp_validate_certs
                )
            else:
                smtp_client = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port)

            async with smtp_client:
                if use_tls and not use_ssl:
                    await smtp_client.starttls(validate_certs=settings.smtp_validate_certs)

                if smtp_username and smtp_password:
                    await smtp_client.login(smtp_username, smtp_password)

                await smtp_client.send_message(msg)

            logging.info(f"OTP email successfully sent to {recipient_email}")
            return True

        except aiosmtplib.SMTPException as e:
            # Log the error for debugging
            logging.error(f"SMTP error occurred while sending email to {recipient_email}: {str(e)}")

            # Check if plaintext fallback is enabled
            if getattr(settings, 'otp_plaintext_fallback', False):
                # Fallback to plaintext mechanism - this could be logging to console,
                # saving to a file, or any other plaintext mechanism configured
                logging.warning(f"[PLAINTEXT FALLBACK] OTP for {recipient_email}: {otp_code}")
                return True
            else:
                # Re-raise the exception if no fallback is configured
                raise Exception(f"Failed to send OTP email: {str(e)}")

        except Exception as e:
            logging.error(f"Unexpected error occurred while sending email to {recipient_email}: {str(e)}")

            # Check if plaintext fallback is enabled
            if getattr(settings, 'otp_plaintext_fallback', False):
                logging.warning(f"[PLAINTEXT FALLBACK] OTP for {recipient_email}: {otp_code}")
                return True
            else:
                raise


# Global instance for easy access
email_service = EmailService()


async def send_otp_email(recipient_email: str, otp_code: str) -> bool:
    """
    Convenience function to send an OTP email.

    Args:
        recipient_email: The email address to send the OTP to
        otp_code: The OTP code to send

    Returns:
        True if email was sent successfully, False otherwise
    """
    return await email_service.send_otp_email(recipient_email, otp_code)