"""Authentication service with OTP and JWT functionality.

Implements:
- AUTH-02: User can request a one-time code by providing their email address
- AUTH-03: User can verify the OTP code and receive a JWT session token
- AUTH-04: Account is created automatically on first successful OTP verification
"""

import secrets
import hashlib
import hmac
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from app.models.models import User, OtpCode
from app.config import settings


def is_valid_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


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

    # Generate 6-digit OTP
    otp_code = f"{secrets.randbelow(1_000_000):06d}"

    # Hash the OTP code
    otp_hash = hashlib.sha256(otp_code.encode()).hexdigest()

    # Set expiration time (10 minutes from now)
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Create new OTP code record
    otp_record = OtpCode(
        email=email.lower(),
        code_hash=otp_hash,
        expires_at=expires_at
    )

    # Add to session and commit
    try:
        db_session.add(otp_record)
        await db_session.commit()

        # For development, we might want to output the code depending on settings
        if settings.otp_plaintext_fallback:
            print(f"[DEV] OTP for {email}: {otp_code}")

        return {
            "success": True,
            "message": "OTP sent successfully",
            "dev_otp_code": otp_code if settings.otp_plaintext_fallback else None
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
        "exp": datetime.utcnow() + timedelta(days=settings.jwt_ttl_days),  # Expiration
        "iat": datetime.utcnow()  # Issued at
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token