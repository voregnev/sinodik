"""
Order processing service v2.

Создаёт Commemoration — одна запись на одно имя.

Flow:
  CSV row / form → Order (метаданные)
                 → parse names
                 → для каждого имени:
                     find_or_create Person
                     create Commemoration (атомарная единица)
"""

import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Person, Order, Commemoration
from app.nlp import extract_names, ParsedName, llm_parse_names
from app.services.csv_parser import CsvRow, parse_csv
from app.services.period_calculator import (
    calculate_expires_at,
    normalize_period_type,
    normalize_order_type,
)
from app.services.embedding_service import embed_name
from app.config import settings

logger = logging.getLogger(__name__)


# ─── Person deduplication ───────────────────────────────────────────

async def find_or_create_person(
    db: AsyncSession,
    parsed: ParsedName,
) -> Person:
    """
    Find existing person by name, or create new.

    Search priority:
    1. Exact match on canonical_name
    2. pg_trgm similarity > 0.6
    3. pgvector cosine similarity > threshold
    4. Create new
    """
    canonical = parsed.canonical

    # 1. Exact match
    result = await db.execute(
        select(Person).where(Person.canonical_name == canonical)
    )
    person = result.scalar_one_or_none()
    if person:
        return person

    # 2. Trigram similarity
    try:
        result = await db.execute(
            select(Person)
            .where(text("similarity(canonical_name, :name) > 0.6"))
            .params(name=canonical)
            .order_by(text("similarity(canonical_name, :name) DESC"))
            .params(name=canonical)
            .limit(1)
        )
        person = result.scalar_one_or_none()
        if person:
            if canonical not in (person.name_variants or []):
                person.name_variants = list(person.name_variants or []) + [canonical]
            return person
    except Exception:
        pass

    # 3. Vector similarity
    embedding = embed_name(canonical)
    if embedding:
        try:
            result = await db.execute(
                select(Person)
                .where(text(
                    "embedding IS NOT NULL AND "
                    "1 - (embedding <=> :vec::vector) > :threshold"
                ))
                .params(vec=str(embedding), threshold=settings.dedup_threshold)
                .limit(1)
            )
            person = result.scalar_one_or_none()
            if person:
                if canonical not in (person.name_variants or []):
                    person.name_variants = list(person.name_variants or []) + [canonical]
                return person
        except Exception as e:
            logger.debug(f"Vector search failed: {e}")

    # 4. Create new
    person = Person(
        canonical_name=canonical,
        genitive_name=parsed.genitive if hasattr(parsed, 'genitive') else None,
        gender=parsed.gender if hasattr(parsed, 'gender') else None,
        name_variants=[parsed.raw] if parsed.raw != canonical else [],
        embedding=embedding,
    )
    db.add(person)
    await db.flush()
    return person


# ─── Process single CSV row → Order + N Commemorations ─────────────

async def process_row(
    db: AsyncSession,
    row: CsvRow,
) -> list[Commemoration]:
    """
    Обработка одной строки CSV.

    Одна строка → один Order + N Commemoration (по числу имён).
    Каждый Commemoration = одно имя с полным набором дат.
    """
    # Dedup заказов по external_id
    if row.external_id:
        existing = await db.execute(
            select(Order).where(Order.external_id == row.external_id)
        )
        if existing.scalar_one_or_none():
            logger.debug(f"Order {row.external_id} already exists — skip")
            return []

    # ── Нормализация ──
    order_type = normalize_order_type(row.order_type)
    period_type = normalize_period_type(row.period_raw)

    # ── Даты ──
    ordered_at = row.date
    starts_at = ordered_at                              # пока starts_at = ordered_at
    expires_at = calculate_expires_at(starts_at, period_type)

    # ── Извлечение имён ──
    names = extract_names(row.names_raw)

    if row.names_raw and (not names or any(n.confidence < 0.5 for n in names)):
        llm_names = await llm_parse_names(row.names_raw)
        if llm_names:
            names = llm_names

    # ── Создание Order (метаданные) ──
    order = Order(
        user_email=row.email,
        source_channel="csv",
        source_raw=row.names_raw,
        external_id=row.external_id,
    )
    db.add(order)
    await db.flush()

    # ── Создание Commemoration для каждого имени ──
    commemorations: list[Commemoration] = []

    for parsed_name in names:
        person = await find_or_create_person(db, parsed_name)

        comm = Commemoration(
            person_id=person.id,
            order_id=order.id,
            order_type=order_type,
            period_type=period_type,
            prefix=parsed_name.prefix,
            ordered_at=ordered_at,
            starts_at=starts_at,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(comm)
        commemorations.append(comm)

    return commemorations


# ─── Process full CSV upload ────────────────────────────────────────

async def process_csv_upload(
    db: AsyncSession,
    content: bytes,
    delimiter: str = ";",
) -> dict:
    """
    Полный pipeline импорта CSV.

    Returns:
        {total_rows, orders_created, commemorations_created, skipped, errors}
    """
    rows = parse_csv(content, delimiter=delimiter)

    stats = {
        "total_rows": len(rows),
        "orders_created": 0,
        "commemorations_created": 0,
        "skipped": 0,
        "errors": 0,
    }

    for row in rows:
        try:
            comms = await process_row(db, row)
            if comms:
                stats["orders_created"] += 1
                stats["commemorations_created"] += len(comms)
            else:
                stats["skipped"] += 1
        except Exception as e:
            logger.error(f"Error processing row: {e}")
            stats["errors"] += 1

    await db.commit()
    logger.info(f"CSV import: {stats}")
    return stats


# ─── Manual order creation ──────────────────────────────────────────

async def create_manual_order(
    db: AsyncSession,
    order_type: str,
    period_type_raw: str,
    names_text: str,
    user_email: str | None = None,
    ordered_at: datetime | None = None,
    starts_at: datetime | None = None,
) -> list[Commemoration]:
    """
    Создание заказа из формы (ручной ввод).

    Returns: list of created Commemoration records.
    """
    if ordered_at is None:
        ordered_at = datetime.utcnow()
    if starts_at is None:
        starts_at = ordered_at

    otype = normalize_order_type(order_type)
    ptype = normalize_period_type(period_type_raw)
    exp = calculate_expires_at(starts_at, ptype)

    names = extract_names(names_text)

    # Order (метаданные)
    order = Order(
        user_email=user_email,
        source_channel="form",
        source_raw=names_text,
    )
    db.add(order)
    await db.flush()

    # Commemorations
    commemorations: list[Commemoration] = []
    for parsed_name in names:
        person = await find_or_create_person(db, parsed_name)

        comm = Commemoration(
            person_id=person.id,
            order_id=order.id,
            order_type=otype,
            period_type=ptype,
            prefix=parsed_name.prefix,
            ordered_at=ordered_at,
            starts_at=starts_at,
            expires_at=exp,
            is_active=True,
        )
        db.add(comm)
        commemorations.append(comm)

    await db.commit()
    return commemorations
