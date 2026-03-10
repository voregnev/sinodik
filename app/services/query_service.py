"""
Query service v2: works with Commemoration as atomic unit.

Main queries:
  - get_active_today()    — все активные поминовения на сегодня
  - search_names()        — fuzzy-поиск по справочнику имён
  - get_stats()           — дашборд статистика
  - get_by_user()         — все заказы конкретного пользователя
  - get_commemorations()  — список поминовений для управления БД
  - bulk_set_starts_at()  — массовая установка даты начала
"""

from datetime import date, datetime

from sqlalchemy import select, func, text, and_, case, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Person, Order, Commemoration
from app.services.embedding_service import embed_name_async
from app.services.period_calculator import calculate_expires_at


# ═══════════════════════════════════════════════════════════
#  ACTIVE NAMES TODAY
# ═══════════════════════════════════════════════════════════

async def get_active_today(
    db: AsyncSession,
    order_type: str | None = None,
    target_date: date | None = None,
) -> list[dict]:
    """
    Все активные поминовения на указанную дату.

    Сортировка: тип (здравие → упокоение) → период (год→полгода→сорокоуст→разовое)
               → дата заказа ASC → позиция ASC.

    Записи с NULL starts_at или expires_at исключаются (ещё не начались).
    """
    if target_date is None:
        target_date = date.today()

    target_dt = datetime.combine(target_date, datetime.min.time())

    type_order = case(
        (Commemoration.order_type == "здравие", 1),
        (Commemoration.order_type == "упокоение", 2),
        else_=3,
    )
    period_order = case(
        (Commemoration.period_type == "год", 1),
        (Commemoration.period_type == "полгода", 2),
        (Commemoration.period_type == "сорокоуст", 3),
        (Commemoration.period_type == "разовое", 4),
        else_=5,
    )

    stmt = (
        select(
            Commemoration.id,
            Commemoration.order_type,
            Commemoration.period_type,
            Commemoration.prefix,
            Commemoration.suffix,
            Commemoration.ordered_at,
            Commemoration.starts_at,
            Commemoration.expires_at,
            Commemoration.is_active,
            Commemoration.position,
            Person.id.label("person_id"),
            Person.canonical_name,
            Person.genitive_name,
            Order.id.label("order_id"),
            Order.user_email,
        )
        .join(Person, Person.id == Commemoration.person_id)
        .outerjoin(Order, Order.id == Commemoration.order_id)
        .where(
            and_(
                Commemoration.is_active == True,
                Commemoration.starts_at.isnot(None),
                Commemoration.expires_at.isnot(None),
                Commemoration.starts_at <= target_dt,
                Commemoration.expires_at >= target_dt,
            )
        )
        .order_by(
            type_order,
            period_order,
            Commemoration.ordered_at.asc(),
            Commemoration.position.asc().nulls_last(),
        )
    )

    if order_type:
        stmt = stmt.where(Commemoration.order_type == order_type)

    result = await db.execute(stmt)

    return [
        {
            "commemoration_id": r.id,
            "person_id": r.person_id,
            "canonical_name": r.canonical_name,
            "genitive_name": r.genitive_name or r.canonical_name,
            "prefix": r.prefix,
            "suffix": r.suffix,
            "order_type": r.order_type,
            "period_type": r.period_type,
            "ordered_at": r.ordered_at.isoformat() if r.ordered_at else None,
            "starts_at": r.starts_at.isoformat() if r.starts_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "order_id": r.order_id,
            "user_email": r.user_email,
            "position": r.position,
        }
        for r in result.all()
    ]


# ═══════════════════════════════════════════════════════════
#  SEARCH (fuzzy)
# ═══════════════════════════════════════════════════════════

async def search_names(
    db: AsyncSession,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """
    Fuzzy-поиск по справочнику имён (Person).

    Три уровня: trigram → vector → ILIKE prefix.
    """
    results = []

    # 1. Trigram
    try:
        result = await db.execute(
            select(
                Person.id,
                Person.canonical_name,
                func.similarity(Person.canonical_name, query).label("score"),
            )
            .where(text("similarity(canonical_name, :q) > 0.3"))
            .params(q=query)
            .order_by(text("similarity(canonical_name, :q) DESC"))
            .params(q=query)
            .limit(limit)
        )
        for r in result.all():
            results.append({
                "person_id": r.id,
                "canonical_name": r.canonical_name,
                "score": float(r.score),
                "method": "trigram",
            })
    except Exception:
        pass

    # 2. Vector
    embedding = await embed_name_async(query)
    if embedding:
        try:
            result = await db.execute(
                select(
                    Person.id,
                    Person.canonical_name,
                    text("1 - (embedding <=> :vec::vector) AS vec_score"),
                )
                .where(text("embedding IS NOT NULL"))
                .params(vec=str(embedding))
                .order_by(text("embedding <=> :vec::vector"))
                .params(vec=str(embedding))
                .limit(limit)
            )
            existing_ids = {x["person_id"] for x in results}
            for r in result.all():
                if r.id not in existing_ids:
                    results.append({
                        "person_id": r.id,
                        "canonical_name": r.canonical_name,
                        "score": float(r.vec_score),
                        "method": "vector",
                    })
        except Exception:
            pass

    # 3. ILIKE fallback
    if not results:
        result = await db.execute(
            select(Person.id, Person.canonical_name)
            .where(Person.canonical_name.ilike(f"{query}%"))
            .limit(limit)
        )
        for r in result.all():
            results.append({
                "person_id": r.id,
                "canonical_name": r.canonical_name,
                "score": 0.5,
                "method": "prefix",
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


# ═══════════════════════════════════════════════════════════
#  STATS
# ═══════════════════════════════════════════════════════════

async def get_stats(db: AsyncSession) -> dict:
    """Dashboard statistics."""
    today_dt = datetime.combine(date.today(), datetime.min.time())

    total_persons = await db.scalar(select(func.count(Person.id))) or 0
    total_commemorations = await db.scalar(select(func.count(Commemoration.id))) or 0
    total_orders = await db.scalar(select(func.count(Order.id))) or 0

    active_today = await db.scalar(
        select(func.count(Commemoration.id)).where(
            and_(
                Commemoration.is_active == True,
                Commemoration.starts_at.isnot(None),
                Commemoration.expires_at.isnot(None),
                Commemoration.starts_at <= today_dt,
                Commemoration.expires_at >= today_dt,
            )
        )
    ) or 0

    # By type
    type_q = await db.execute(
        select(Commemoration.order_type, func.count(Commemoration.id))
        .where(
            and_(
                Commemoration.is_active == True,
                Commemoration.expires_at.isnot(None),
                Commemoration.expires_at >= today_dt,
            )
        )
        .group_by(Commemoration.order_type)
    )
    by_type = {r[0]: r[1] for r in type_q.all()}

    # By period
    period_q = await db.execute(
        select(Commemoration.period_type, func.count(Commemoration.id))
        .where(
            and_(
                Commemoration.is_active == True,
                Commemoration.expires_at.isnot(None),
                Commemoration.expires_at >= today_dt,
            )
        )
        .group_by(Commemoration.period_type)
    )
    by_period = {r[0]: r[1] for r in period_q.all()}

    return {
        "total_persons": total_persons,
        "total_commemorations": total_commemorations,
        "total_orders": total_orders,
        "active_today": active_today,
        "by_type": by_type,
        "by_period": by_period,
    }


# ═══════════════════════════════════════════════════════════
#  BY USER (email)
# ═══════════════════════════════════════════════════════════

async def get_by_user(
    db: AsyncSession,
    user_email: str,
    active_only: bool = True,
) -> list[dict]:
    """Все поминовения заказанные конкретным пользователем."""
    today_dt = datetime.combine(date.today(), datetime.min.time())

    stmt = (
        select(
            Commemoration.id,
            Commemoration.order_type,
            Commemoration.period_type,
            Commemoration.prefix,
            Commemoration.ordered_at,
            Commemoration.starts_at,
            Commemoration.expires_at,
            Commemoration.is_active,
            Person.canonical_name,
        )
        .join(Person, Person.id == Commemoration.person_id)
        .join(Order, Order.id == Commemoration.order_id)
        .where(Order.user_email == user_email)
        .order_by(Commemoration.ordered_at.desc())
    )

    if active_only:
        stmt = stmt.where(
            and_(
                Commemoration.is_active == True,
                Commemoration.expires_at.isnot(None),
                Commemoration.expires_at >= today_dt,
            )
        )

    result = await db.execute(stmt)

    return [
        {
            "commemoration_id": r.id,
            "canonical_name": r.canonical_name,
            "prefix": r.prefix,
            "order_type": r.order_type,
            "period_type": r.period_type,
            "ordered_at": r.ordered_at.isoformat() if r.ordered_at else None,
            "starts_at": r.starts_at.isoformat() if r.starts_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "is_active": r.is_active,
        }
        for r in result.all()
    ]


# ═══════════════════════════════════════════════════════════
#  DB MANAGEMENT: list commemorations
# ═══════════════════════════════════════════════════════════

async def get_commemorations(
    db: AsyncSession,
    no_start_date: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    Список поминовений для управления БД.

    Если no_start_date=True — только записи без даты начала (starts_at IS NULL).
    """
    stmt = (
        select(
            Commemoration.id,
            Commemoration.order_type,
            Commemoration.period_type,
            Commemoration.prefix,
            Commemoration.suffix,
            Commemoration.ordered_at,
            Commemoration.starts_at,
            Commemoration.expires_at,
            Commemoration.is_active,
            Commemoration.position,
            Commemoration.order_id,
            Person.id.label("person_id"),
            Person.canonical_name,
            Order.user_email,
            Order.need_receipt,
        )
        .join(Person, Person.id == Commemoration.person_id)
        .outerjoin(Order, Order.id == Commemoration.order_id)
        .order_by(Commemoration.id.desc())
        .limit(limit)
        .offset(offset)
    )

    if no_start_date:
        stmt = stmt.where(Commemoration.starts_at.is_(None))

    result = await db.execute(stmt)

    return [
        {
            "id": r.id,
            "person_id": r.person_id,
            "canonical_name": r.canonical_name,
            "order_id": r.order_id,
            "order_type": r.order_type,
            "period_type": r.period_type,
            "prefix": r.prefix,
            "ordered_at": r.ordered_at.isoformat() if r.ordered_at else None,
            "starts_at": r.starts_at.isoformat() if r.starts_at else None,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "is_active": r.is_active,
            "position": r.position,
            "suffix": r.suffix,
            "user_email": r.user_email,
            "need_receipt": r.need_receipt,
        }
        for r in result.all()
    ]


# ═══════════════════════════════════════════════════════════
#  DB MANAGEMENT: bulk set starts_at
# ═══════════════════════════════════════════════════════════

async def bulk_set_starts_at(
    db: AsyncSession,
    ids: list[int],
    starts_at: datetime,
) -> int:
    """
    Массовая установка starts_at для списка поминовений.

    expires_at пересчитывается индивидуально по period_type каждой записи.
    Возвращает количество обновлённых записей.
    """
    if not ids:
        return 0

    result = await db.execute(
        select(Commemoration).where(Commemoration.id.in_(ids))
    )
    comms = result.scalars().all()

    count = 0
    for comm in comms:
        comm.starts_at = starts_at
        comm.expires_at = calculate_expires_at(starts_at, comm.period_type)
        count += 1

    await db.commit()
    return count
