"""Admin-only endpoints: list users with counts, PATCH user role/is_active with last-admin guard."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin
from database import get_db
from models.models import User
from models import Order, Commemoration

router = APIRouter(prefix="/admin", tags=["admin"])


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
    ]
