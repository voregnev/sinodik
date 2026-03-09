from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Order
from app.services.order_service import create_manual_order

router = APIRouter()


class OrderCreate(BaseModel):
    order_type: str
    period_type: str
    names: str
    user_email: str | None = None


@router.post("/orders")
async def create_order(body: OrderCreate, db: AsyncSession = Depends(get_db)):
    comms = await create_manual_order(
        db,
        order_type=body.order_type,
        period_type_raw=body.period_type,
        names_text=body.names,
        user_email=body.user_email,
    )
    return {
        "order_id": comms[0].order_id if comms else None,
        "commemorations_created": len(comms),
    }


@router.get("/orders")
async def list_orders(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).order_by(Order.created_at.desc()).offset(offset).limit(limit)
    )
    orders = result.scalars().all()
    return [
        {
            "id": o.id,
            "user_email": o.user_email,
            "source_channel": o.source_channel,
            "external_id": o.external_id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]


@router.delete("/orders/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
    await db.commit()
    return {"deleted": order_id}
