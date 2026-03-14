"""Authentication service with OTP and JWT functionality.

Implements:
- AUTH-02: User can request a one-time code by providing their email address
- AUTH-03: User can verify the OTP code and receive a JWT session token
- AUTH-04: Account is created automatically on first successful OTP verification
- AUTH-07: OTP lifecycle management with expiry and single-use
- AUTH-08: Rate limiting for OTP attempts
- AUTH-09: Integration with email service with fallback mechanism
"""

import secrets
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete

from models.models import User, OtpCode
from config import settings
from .email_service import send_otp_email


def is_valid_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


async def check_rate_limit(email: str, db_session: AsyncSession, time_window_minutes: int = 5, max_requests: int = 5) -> bool:
    """Check if the user has exceeded the OTP request rate limit.

    Args:
        email: User's email address
        db_session: Async database session
        time_window_minutes: Time window to check for requests (default: 5 minutes)
        max_requests: Maximum number of requests allowed in the time window (default: 5)

    Returns:
        True if within rate limit, False if exceeded
    """
    time_threshold = datetime.now(timezone.utc)- timedelta(minutes=time_window_minutes)

    # Count the number of OTP requests in the time window
    stmt = select(OtpCode).where(
        OtpCode.email == email.lower(),
        OtpCode.created_at > time_threshold
    )

    result = await db_session.execute(stmt)
    recent_requests = result.scalars().all()

    # Check if the number of recent requests exceeds the limit
    if len(recent_requests) >= max_requests:
        return False

    return True


async def request_otp(email: str, db_session: AsyncSession) -> Dict[str, Any]:
    """Generate and store a 6-digit OTP code for the given email.

    Args:
        email: User's email address
        db_session: Async database session

    Returns:
        Dictionary with success status and message
    """
    if not is_valid_email(email):
        raise ValueError(f"Invalid email format: {email}")

    # Check rate limit for OTP requests
    within_rate_limit = await check_rate_limit(email, db_session)
    if not within_rate_limit:
        return {
            "success": False,
            "message": "Rate limit exceeded. Please try again later."
        }

    # Generate 6-digit OTP
    otp_code = f"{secrets.randbelow(1_000_000):06d}"

    # Hash the OTP code
    otp_hash = hashlib.sha256(otp_code.encode()).hexdigest()

    # Set expiration time (10 minutes from now)
    expires_at = datetime.now(timezone.utc)+ timedelta(minutes=10)

    # Create new OTP code record
    otp_record = OtpCode(
        email=email.lower(),
        code_hash=otp_hash,
        expires_at=expires_at
    )

    # Add to session and commit
    try:
        db_session.add(otp_record)

        # Attempt to send OTP via email
        try:
            email_sent = await send_otp_email(email.lower(), otp_code)

            if email_sent:
                # Email sent successfully, return success without OTP in response
                await db_session.commit()
                return {
                    "success": True,
                    "message": "OTP sent successfully via email"
                }
            else:
                # Email failed, check if plaintext fallback is enabled
                if settings.otp_plaintext_fallback:
                    await db_session.commit()
                    return {
                        "success": True,
                        "message": "OTP generated successfully",
                        "dev_otp_code": otp_code
                    }
                else:
                    # Rollback and return error if fallback is disabled
                    await db_session.rollback()
                    return {
                        "success": False,
                        "message": "Failed to send OTP via email and plaintext fallback is disabled"
                    }
        except Exception as email_error:
            logging.error(f"Email delivery failed for {email}: {str(email_error)}")

            # Check if plaintext fallback is enabled
            if settings.otp_plaintext_fallback:
                await db_session.commit()
                return {
                    "success": True,
                    "message": "OTP delivery failed, but code provided for development",
                    "dev_otp_code": otp_code
                }
            else:
                # Rollback the database transaction since email delivery failed
                await db_session.rollback()
                return {
                    "success": False,
                    "message": f"Failed to send OTP: {str(email_error)}"
                }

    except Exception as e:
        await db_session.rollback()
        return {
            "success": False,
            "message": f"Failed to generate OTP: {str(e)}"
        }


async def verify_otp(email: str, code: str, db_session: AsyncSession) -> Optional[Dict[str, Any]]:
    """Verify OTP code and return JWT token upon successful verification.

    Args:
        email: User's email address
        code: 6-digit OTP code entered by user
        db_session: Async database session

    Returns:
        Dictionary with JWT token and user info if successful, None otherwise
    """
    if not is_valid_email(email):
        return None

    # Validate code format (should be 6 digits)
    if not re.match(r'^\d{6}$', code):
        return None

    # Hash the provided code for comparison
    provided_code_hash = hashlib.sha256(code.encode()).hexdigest()

    # Find the most recent unexpired, unused OTP for the email
    stmt = select(OtpCode).where(
        OtpCode.email == email.lower(),
        OtpCode.expires_at > datetime.utcnow(),
        OtpCode.used == False,
        OtpCode.attempt_count < 5
    ).order_by(OtpCode.created_at.desc())

    result = await db_session.execute(stmt)
    otp_record = result.scalar_one_or_none()

    if not otp_record:
        return None

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(otp_record.code_hash, provided_code_hash):
        # Increment attempt count
        otp_record.attempt_count += 1
        await db_session.commit()

        # Check if max attempts reached
        if otp_record.attempt_count >= 5:
            # OTP record is now invalid due to too many attempts
            return None
        return None

    # OTP is valid, mark as used
    otp_record.used = True
    await db_session.commit()

    # Find or create user account
    user = await _get_or_create_user(email.lower(), db_session)
    if not user:
        return None

    await db_session.commit()

    # Create JWT token
    token = create_jwt_token(user.email, user.role)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        }
    }


async def _get_or_create_user(email: str, db_session: AsyncSession) -> Optional[User]:
    """Get existing user or create a new one.

    For new users, role is set to 'admin' if email is in settings.admin_emails,
    otherwise 'user'.
    """
    # First, try to find existing user
    stmt = select(User).where(User.email == email)
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        return user

    # User doesn't exist, create new one
    role = "admin" if email.lower() in settings.admin_emails else "user"

    new_user = User(
        email=email,
        role=role,
        is_active=True
    )

    try:
        db_session.add(new_user)
        await db_session.commit()
        await db_session.refresh(new_user)
        return new_user
    except IntegrityError:
        # Handle potential race condition where user was created between check and insert
        await db_session.rollback()
        stmt = select(User).where(User.email == email)
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()


def create_jwt_token(email: str, role: str) -> str:
    """Create a JWT token with email, role, and expiration claims.

    Args:
        email: User's email address
        role: User's role ('user' or 'admin')

    Returns:
        Encoded JWT token string
    """
    payload = {
        "sub": email,  # Subject (user identifier)
        "role": role,  # User role
        "exp": datetime.now(timezone.utc)+ timedelta(days=settings.jwt_ttl_days),  # Expiration
        "iat": datetime.now(timezone.utc) # Issued at
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token


async def cleanup_expired_otps(db_session: AsyncSession) -> int:
    """Remove expired OTP codes from the database to prevent accumulation.

    Args:
        db_session: Async database session

    Returns:
        Number of expired OTPs deleted
    """
    from sqlalchemy import delete

    # Delete all OTP codes that have expired
    stmt = delete(OtpCode).where(OtpCode.expires_at < datetime.utcnow())

    result = await db_session.execute(stmt)
    await db_session.commit()

    deleted_count = result.rowcount
    return deleted_count