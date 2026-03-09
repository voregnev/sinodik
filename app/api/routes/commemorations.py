from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Commemoration
from app.services.query_service import get_commemorations, bulk_set_starts_at
from app.services.period_calculator import calculate_expires_at

router = APIRouter()


class CommemorationUpdate(BaseModel):
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    order_type: str | None = None
    period_type: str | None = None
    prefix: str | None = None


class BulkUpdateRequest(BaseModel):
    ids: list[int]
    starts_at: datetime


@router.get("/commemorations")
async def list_commemorations(
    no_start_date: bool = Query(default=False),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List commemorations, optionally filtered to those without a start date."""
    items = await get_commemorations(db, no_start_date=no_start_date, limit=limit, offset=offset)
    return {"items": items, "count": len(items)}


@router.patch("/commemorations/{commemoration_id}")
async def update_commemoration(
    commemoration_id: int,
    body: CommemorationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update one or more fields of a commemoration inline."""
    result = await db.execute(
        select(Commemoration).where(Commemoration.id == commemoration_id)
    )
    comm = result.scalar_one_or_none()
    if not comm:
        raise HTTPException(status_code=404, detail="Commemoration not found")

    if body.order_type is not None:
        comm.order_type = body.order_type
    if body.period_type is not None:
        comm.period_type = body.period_type
        # Recalculate expires_at when period changes and starts_at is known
        effective_starts = body.starts_at or comm.starts_at
        if effective_starts:
            comm.expires_at = calculate_expires_at(effective_starts, comm.period_type)
    if body.prefix is not None:
        comm.prefix = body.prefix
    if body.starts_at is not None:
        comm.starts_at = body.starts_at
        if comm.expires_at is None or body.period_type is not None:
            comm.expires_at = calculate_expires_at(comm.starts_at, comm.period_type)
    if body.expires_at is not None:
        comm.expires_at = body.expires_at

    await db.commit()
    await db.refresh(comm)

    return {
        "id": comm.id,
        "order_type": comm.order_type,
        "period_type": comm.period_type,
        "prefix": comm.prefix,
        "starts_at": comm.starts_at.isoformat() if comm.starts_at else None,
        "expires_at": comm.expires_at.isoformat() if comm.expires_at else None,
    }


@router.post("/commemorations/bulk-update")
async def bulk_update_starts_at(
    body: BulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Bulk set starts_at (and recalculate expires_at) for a list of commemorations."""
    if not body.ids:
        raise HTTPException(status_code=400, detail="ids must not be empty")
    count = await bulk_set_starts_at(db, body.ids, body.starts_at)
    return {"updated": count}
