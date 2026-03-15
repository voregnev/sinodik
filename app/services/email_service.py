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
from config import settings


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

            # use_ssl=True → port 465 implicit TLS (no STARTTLS).
            # use_ssl=False, use_tls=True → port 587; aiosmtplib auto-upgrades via STARTTLS on connect — do NOT call starttls() manually or we get "Connection already using TLS".
            use_tls = settings.smtp_use_tls
            use_ssl = settings.smtp_use_ssl

            timeout = settings.smtp_timeout

            if use_ssl:
                # Port 465: TLS from the start. Many servers prefer 587+STARTTLS; if 465 times out, use port 587 and SINODIK_SMTP_USE_SSL=false.
                smtp_client = aiosmtplib.SMTP(
                    hostname=smtp_host,
                    port=smtp_port,
                    use_tls=True,
                    validate_certs=settings.smtp_validate_certs,
                    timeout=timeout,
                )
            else:
                # Port 587: plain connect, STARTTLS is done automatically by aiosmtplib on connect when server advertises it
                smtp_client = aiosmtplib.SMTP(
                    hostname=smtp_host,
                    port=smtp_port,
                    use_tls=False,
                    start_tls=use_tls,
                    validate_certs=settings.smtp_validate_certs,
                    timeout=timeout,
                )

            async with smtp_client:
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