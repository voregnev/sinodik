from datetime import datetime

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_current_user_optional, require_admin
from database import get_db
from models import Order, Commemoration, Person
from models.models import User
from services.order_service import create_manual_order, refill_order_commemorations

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
async def create_order(
    body: OrderCreate,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    link_email = current_user.email if current_user is not None else body.user_email
    try:
        comms = await create_manual_order(
            db,
            order_type=body.order_type,
            period_type_raw=body.period_type,
            names_text=body.names_text,
            user_email=link_email,
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
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Order).order_by(Order.created_at.desc()).offset(offset).limit(limit)
    if current_user.role != "admin":
        stmt = stmt.where(Order.user_email == current_user.email)
    result = await db.execute(stmt)
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


@router.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get one order with source_raw and list of extracted commemorations (names with prefix/suffix). Admin only."""
    order_result = await db.execute(select(Order).where(Order.id == order_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    comm_result = await db.execute(
        select(Commemoration, Person.canonical_name, Person.genitive_name)
        .join(Person, Person.id == Commemoration.person_id)
        .where(Commemoration.order_id == order_id)
        .order_by(Commemoration.position.asc().nullslast(), Commemoration.id.asc())
    )
    comm_list = [
        {
            "id": c.id,
            "canonical_name": name or "",
            "genitive_name": genitive,
            "prefix": c.prefix,
            "suffix": c.suffix,
            "order_type": c.order_type,
            "period_type": c.period_type,
            "position": c.position,
            "starts_at": c.starts_at.isoformat() if c.starts_at else None,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        }
        for c, name, genitive in comm_result.all()
    ]

    return {
        "id": order.id,
        "user_email": order.user_email,
        "source_channel": order.source_channel,
        "source_raw": order.source_raw,
        "external_id": order.external_id,
        "need_receipt": order.need_receipt,
        "ordered_at": order.ordered_at.isoformat() if order.ordered_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "commemorations": comm_list,
    }


@router.patch("/orders/{order_id}")
async def update_order(
    order_id: int,
    body: OrderUpdate,
    _admin: User = Depends(require_admin),
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

    # Если у записки нет поминовений, но есть source_raw — парсим заново и добавляем имена
    refilled = await refill_order_commemorations(db, order)
    if refilled:
        await db.commit()

    return {
        "id": order.id,
        "user_email": order.user_email,
        "ordered_at": order.ordered_at.isoformat() if order.ordered_at else None,
        "need_receipt": order.need_receipt,
        "commemorations_refilled": len(refilled),
    }


@router.delete("/orders/{order_id}")
async def delete_order(
    order_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # Каскадно удаляем все поминовения этой записки (работает и до применения миграции CASCADE)
    await db.execute(Commemoration.__table__.delete().where(Commemoration.order_id == order_id))
    await db.delete(order)
    await db.commit()
    return {"deleted": order_id}
