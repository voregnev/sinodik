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

import hashlib
import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Person, Order, Commemoration
from app.nlp import extract_names, ParsedName, llm_parse_names
from app.services.csv_parser import CsvRow, parse_csv
from app.services.period_calculator import (
    calculate_expires_at,
    normalize_period_type,
    normalize_order_type,
)
from app.services.embedding_service import embed_name_async
from app.config import settings

logger = logging.getLogger(__name__)


# ─── Dedup helpers ──────────────────────────────────────────────────

def _make_external_id(date_str: str, content: str) -> str:
    """Deterministic hash for deduplication: sha256(date|content)[:64]."""
    payload = f"{date_str}|{content.strip()}"
    return hashlib.sha256(payload.encode()).hexdigest()[:64]


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
    embedding = await embed_name_async(canonical)
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

    # 4. Create new (safe against concurrent inserts)
    genitive = parsed.genitive if hasattr(parsed, "genitive") else None
    gender = parsed.gender if hasattr(parsed, "gender") else None
    variants = [parsed.raw] if parsed.raw != canonical else []

    stmt = (
        insert(Person)
        .values(
            canonical_name=canonical,
            genitive_name=genitive,
            gender=gender,
            name_variants=variants,
            embedding=embedding,
        )
        .on_conflict_do_nothing(index_elements=[Person.canonical_name])
        .returning(Person)
    )

    result = await db.execute(stmt)
    person = result.scalar_one_or_none()

    if not person:
        # Another transaction inserted this person concurrently — fetch it.
        result = await db.execute(
            select(Person).where(Person.canonical_name == canonical)
        )
        person = result.scalar_one()

    return person


# ─── Process single CSV row → Order + N Commemorations ─────────────

async def process_row(
    db: AsyncSession,
    row: CsvRow,
    starts_at_override: datetime | None = None,
) -> list[Commemoration]:
    """
    Обработка одной строки CSV.

    Одна строка → один Order + N Commemoration (по числу имён).
    Каждый Commemoration = одно имя с полным набором дат.

    Raises ValueError if:
      - order_type or names_raw is empty
      - no valid names found in names_raw
    """
    # ── Validation (before any DB writes) ──
    if not row.order_type or not row.order_type.strip():
        raise ValueError("order_type is required")
    if not row.names_raw or not row.names_raw.strip():
        raise ValueError("names_raw is required")

    # ── Dedup by external_id (use hash if not provided) ──
    ext_id = row.external_id or _make_external_id(
        row.date.strftime("%Y-%m-%d"), row.names_raw
    )
    existing = await db.execute(
        select(Order).where(Order.external_id == ext_id)
    )
    if existing.scalar_one_or_none():
        logger.debug(f"Order {ext_id} already exists — skip")
        return []

    # ── Нормализация ──
    order_type = normalize_order_type(row.order_type)
    period_type = normalize_period_type(row.period_raw)

    # ── Даты ──
    ordered_at = row.date
    starts_at = starts_at_override  # None = не назначено
    expires_at = calculate_expires_at(starts_at, period_type) if starts_at else None

    # ── Извлечение имён (до создания Order, чтобы не создавать "пустые" записи) ──
    names = extract_names(row.names_raw)

    if row.names_raw and (not names or any(n.confidence < 0.5 for n in names)):
        llm_names = await llm_parse_names(row.names_raw)
        if llm_names:
            names = llm_names

    if not names:
        raise ValueError(f"No valid names found in: {row.names_raw!r}")

    # ── Создание Order (метаданные) ──
    order = Order(
        user_email=row.email,
        source_channel="csv",
        source_raw=row.names_raw,
        external_id=ext_id,
    )
    db.add(order)
    await db.flush()

    # ── Создание Commemoration для каждого имени ──
    commemorations: list[Commemoration] = []

    for idx, parsed_name in enumerate(names, start=1):
        person = await find_or_create_person(db, parsed_name)

        comm = Commemoration(
            person_id=person.id,
            order_id=order.id,
            order_type=order_type,
            period_type=period_type,
            prefix=parsed_name.prefix,
            suffix=parsed_name.suffix,
            ordered_at=ordered_at,
            starts_at=starts_at,
            expires_at=expires_at,
            is_active=True,
            position=idx,
        )
        db.add(comm)
        commemorations.append(comm)

    return commemorations


# ─── Process full CSV upload ────────────────────────────────────────

async def process_csv_upload(
    db: AsyncSession,
    content: bytes,
    delimiter: str = ";",
    starts_at: datetime | None = None,
) -> dict:
    """
    Полный pipeline импорта CSV.

    Returns:
        {total_rows, orders_created, commemorations_created, skipped, errors}
        errors is now a list[str] with per-row error messages.
    """
    rows = parse_csv(content, delimiter=delimiter)

    stats: dict = {
        "total_rows": len(rows),
        "orders_created": 0,
        "commemorations_created": 0,
        "skipped": 0,
        "errors": [],
    }

    for row in rows:
        try:
            comms = await process_row(db, row, starts_at_override=starts_at)
            if comms:
                stats["orders_created"] += 1
                stats["commemorations_created"] += len(comms)
            else:
                stats["skipped"] += 1
        except Exception as e:
            logger.error(f"Error processing row: {e}")
            stats["errors"].append(str(e))
            await db.rollback()
            continue

        # Фиксируем успешную строку отдельно, чтобы ошибки
        # в последующих строках не откатывали уже созданные записи.
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
    need_receipt: bool = False,
) -> list[Commemoration]:
    """
    Создание заказа из формы (ручной ввод).

    Returns: list of created Commemoration records.
    Raises ValueError if order_type/names_text is empty or no names found.
    """
    # ── Validation ──
    if not order_type or not order_type.strip():
        raise ValueError("order_type is required")
    if not names_text or not names_text.strip():
        raise ValueError("names_text is required")

    if ordered_at is None:
        ordered_at = datetime.utcnow()

    otype = normalize_order_type(order_type)
    ptype = normalize_period_type(period_type_raw)
    # starts_at stays None if not provided — means "not yet started"
    exp = calculate_expires_at(starts_at, ptype) if starts_at else None

    # ── Extract names before creating Order ──
    names = extract_names(names_text)
    if not names:
        raise ValueError(f"No valid names found in: {names_text!r}")

    # ── Dedup by hash ──
    ext_id = _make_external_id(ordered_at.isoformat(), names_text)
    existing = await db.execute(select(Order).where(Order.external_id == ext_id))
    if existing.scalar_one_or_none():
        raise ValueError("Duplicate order: identical content already submitted")

    # ── Order (метаданные) ──
    order = Order(
        user_email=user_email,
        source_channel="form",
        source_raw=names_text,
        external_id=ext_id,
        need_receipt=need_receipt,
    )
    db.add(order)
    await db.flush()

    # ── Commemorations ──
    commemorations: list[Commemoration] = []
    for idx, parsed_name in enumerate(names, start=1):
        person = await find_or_create_person(db, parsed_name)

        comm = Commemoration(
            person_id=person.id,
            order_id=order.id,
            order_type=otype,
            period_type=ptype,
            prefix=parsed_name.prefix,
            suffix=parsed_name.suffix,
            ordered_at=ordered_at,
            starts_at=starts_at,
            expires_at=exp,
            is_active=True,
            position=idx,
        )
        db.add(comm)
        commemorations.append(comm)

    await db.commit()
    return commemorations
