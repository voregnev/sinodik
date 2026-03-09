"""
Names endpoints v2: active commemorations today, search, stats, by-user.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.query_service import get_active_today, search_names, get_stats, get_by_user

router = APIRouter()


@router.get("/names/today")
async def names_today(
    order_type: str | None = Query(default=None, description="Filter: здравие | упокоение"),
    target_date: date | None = Query(default=None, description="Дата (default: сегодня)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Все активные поминовения на сегодня.

    Каждая запись = одно имя (Commemoration).
    Группировка по order_type.
    """
    names = await get_active_today(db, order_type=order_type, target_date=target_date)

    grouped = {"здравие": [], "упокоение": []}
    for n in names:
        otype = n["order_type"]
        if otype not in grouped:
            grouped[otype] = []
        grouped[otype].append(n)

    return {
        "date": (target_date or date.today()).isoformat(),
        "total": len(names),
        "groups": grouped,
    }


@router.get("/names/search")
async def names_search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Fuzzy-поиск по справочнику имён."""
    results = await search_names(db, query=q, limit=limit)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/names/stats")
async def names_stats(db: AsyncSession = Depends(get_db)):
    """Статистика: всего имён, записок, активных сегодня."""
    return await get_stats(db)


@router.get("/names/by-user")
async def names_by_user(
    email: str = Query(..., description="Email заказчика"),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """Все поминовения конкретного пользователя (по email)."""
    results = await get_by_user(db, user_email=email, active_only=active_only)
    return {"user_email": email, "commemorations": results, "count": len(results)}
