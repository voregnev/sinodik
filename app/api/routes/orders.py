from datetime import datetime

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Order
from app.services.order_service import create_manual_order

router = APIRouter()
logger = logging.getLogger(__name__)


class OrderCreate(BaseModel):
    order_type: str
    period_type: str
    names_text: str
    user_email: str | None = None
    starts_at: datetime | None = None
    need_receipt: bool = False


class OrderUpdate(BaseModel):
    user_email: str | None = None
    ordered_at: datetime | None = None
    need_receipt: bool | None = None


@router.post("/orders")
async def create_order(body: OrderCreate, db: AsyncSession = Depends(get_db)):
    try:
        comms = await create_manual_order(
            db,
            order_type=body.order_type,
            period_type_raw=body.period_type,
            names_text=body.names_text,
            user_email=body.user_email,
            starts_at=body.starts_at,
            need_receipt=body.need_receipt,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Create order failed")
        raise HTTPException(status_code=500, detail=str(e))

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
            "need_receipt": o.need_receipt,
            "ordered_at": o.ordered_at.isoformat() if o.ordered_at else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]


@router.patch("/orders/{order_id}")
async def update_order(
    order_id: int,
    body: OrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if body.user_email is not None:
        order.user_email = body.user_email
    if body.ordered_at is not None:
        order.ordered_at = body.ordered_at
    if body.need_receipt is not None:
        order.need_receipt = body.need_receipt

    await db.commit()
    await db.refresh(order)

    return {
        "id": order.id,
        "user_email": order.user_email,
        "ordered_at": order.ordered_at.isoformat() if order.ordered_at else None,
        "need_receipt": order.need_receipt,
    }


@router.delete("/orders/{order_id}")
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
    await db.commit()
    return {"deleted": order_id}
