"""Admin-only endpoints: list users with counts, PATCH user role/is_active with last-admin guard."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from api.deps import require_admin
from config import settings
from database import get_db
from models.models import User
from models import Order, Commemoration

router = APIRouter(prefix="/admin", tags=["admin"])


class UserPatchBody(BaseModel):
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None


def _today_start_utc():
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("/users")
async def list_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all user accounts with orders_count and active_commemoration_count. Admin only."""
    today_start = _today_start_utc()
    orders_subq = (
        select(func.count(Order.id))
        .where(Order.user_email == User.email)
        .scalar_subquery()
    )
    active_comm_subq = (
        select(func.count(Commemoration.id))
        .select_from(Commemoration)
        .join(Order, Commemoration.order_id == Order.id)
        .where(
            Order.user_email == User.email,
            Commemoration.is_active == True,
            Commemoration.expires_at >= today_start,
        )
        .scalar_subquery()
    )
    stmt = select(User, orders_subq.label("orders_count"), active_comm_subq.label("active_commemoration_count"))
    result = await db.execute(stmt)
    rows = result.all()
    superuser_lower = settings.superuser_email.lower()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "orders_count": oc,
            "active_commemoration_count": acc,
        }
        for u, oc, acc in rows
        if u.email.lower() != superuser_lower
    ]


@router.patch("/users/{user_id}", status_code=200)
async def patch_user(
    user_id: int,
    body: UserPatchBody,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user role and/or is_active. Returns 400 when demoting or disabling the last admin."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.email.lower() == settings.superuser_email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify or disable the superuser account",
        )
    if body.role is not None or body.is_active is not None:
        if body.role == "user" or body.is_active is False:
            count_result = await db.execute(
                select(func.count(User.id)).where(
                    User.role == "admin",
                    User.is_active == True,
                )
            )
            active_admin_count = count_result.scalar() or 0
            if active_admin_count == 1 and user.id is not None and user.role == "admin" and user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote or disable the last admin",
                )
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete user by id. Returns 400 for superuser. Admin only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.email.lower() == settings.superuser_email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the superuser account",
        )
    count_result = await db.execute(
        select(func.count(User.id)).where(
            User.role == "admin",
            User.is_active == True,
        )
    )
    active_admin_count = count_result.scalar() or 0
    if active_admin_count == 1 and user.role == "admin" and user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last admin",
        )
    await db.delete(user)
    await db.commit()
    return None
