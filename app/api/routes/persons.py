"""
Словарь имён (Person) — просмотр и правка канонических имён.

Используется для поиска/дедупликации при извлечении имён из записок.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Person

router = APIRouter()


class PersonUpdate(BaseModel):
    canonical_name: str | None = None
    genitive_name: str | None = None
    gender: str | None = None
    name_variants: list[str] | None = None


@router.get("/persons")
async def list_persons(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, description="Поиск по имени"),
    db: AsyncSession = Depends(get_db),
):
    """Список записей словаря имён с опциональным поиском."""
    stmt = select(Person).order_by(Person.canonical_name)
    if q and q.strip():
        qn = q.strip()
        stmt = stmt.where(
            Person.canonical_name.ilike(f"%{qn}%")
            | (Person.genitive_name.isnot(None) & Person.genitive_name.ilike(f"%{qn}%"))
        )
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    persons = result.scalars().all()
    total = await db.scalar(select(func.count(Person.id)))
    return {
        "items": [
            {
                "id": p.id,
                "canonical_name": p.canonical_name,
                "genitive_name": p.genitive_name,
                "gender": p.gender,
                "name_variants": p.name_variants or [],
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in persons
        ],
        "total": total,
        "count": len(persons),
    }


@router.get("/persons/{person_id}")
async def get_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Одна запись словаря по id."""
    result = await db.execute(select(Person).where(Person.id == person_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Person not found")
    return {
        "id": p.id,
        "canonical_name": p.canonical_name,
        "genitive_name": p.genitive_name,
        "gender": p.gender,
        "name_variants": p.name_variants or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.patch("/persons/{person_id}")
async def update_person(
    person_id: int,
    body: PersonUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Изменить запись словаря (имя, родительный падеж, пол, варианты написания)."""
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    if body.canonical_name is not None:
        name = body.canonical_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="canonical_name не может быть пустым")
        existing = await db.execute(
            select(Person).where(Person.canonical_name == name, Person.id != person_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Имя «{name}» уже есть в словаре")
        person.canonical_name = name

    if body.genitive_name is not None:
        person.genitive_name = body.genitive_name.strip() or None

    if body.gender is not None:
        g = body.gender.strip().lower()
        if g and g not in ("м", "ж"):
            raise HTTPException(status_code=400, detail="gender должен быть «м» или «ж»")
        person.gender = g or None

    if body.name_variants is not None:
        person.name_variants = [v.strip() for v in body.name_variants if v and v.strip()]

    await db.commit()
    await db.refresh(person)

    return {
        "id": person.id,
        "canonical_name": person.canonical_name,
        "genitive_name": person.genitive_name,
        "gender": person.gender,
        "name_variants": person.name_variants or [],
    }


@router.delete("/persons/{person_id}")
async def delete_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Удалить запись из словаря имён. Все поминовения с этим именем удалятся каскадно."""
    result = await db.execute(select(Person).where(Person.id == person_id))
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    await db.delete(person)
    await db.commit()
    return {"deleted": person_id}
