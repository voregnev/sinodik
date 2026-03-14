"""Auth HTTP endpoints: request-otp, verify-otp, me."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.models import User
from services.auth_service import request_otp, verify_otp
from api.deps import get_current_user

router = APIRouter()


class RequestOtpBody(BaseModel):
    email: str


class VerifyOtpBody(BaseModel):
    email: str
    code: str


@router.post("/auth/request-otp", status_code=202)
async def request_otp_endpoint(body: RequestOtpBody, db: AsyncSession = Depends(get_db)):
    """Request OTP for the given email. Returns 202 with message; 429 on rate limit; 400 on invalid email."""
    try:
        result = await request_otp(body.email, db)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email format")
    if not result["success"]:
        msg = result.get("message", "Bad request")
        if "Rate limit" in msg:
            raise HTTPException(status_code=429, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    response = {"message": result["message"]}
    if "dev_otp_code" in result:
        response["dev_otp_code"] = result["dev_otp_code"]
    return response


@router.post("/auth/verify-otp")
async def verify_otp_endpoint(body: VerifyOtpBody, db: AsyncSession = Depends(get_db)):
    """Verify OTP code; returns token and user on success, 401 if invalid or expired."""
    result = await verify_otp(body.email, body.code, db)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired code")
    return {"token": result["token"], "user": result["user"]}


@router.get("/auth/me")
async def me(current_user: User = Depends(get_current_user)):
    """Return current user from JWT. 401 if missing or expired."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
