# Conventions: Sinodic

## Language

- **Backend**: Python 3.14 with modern type hints (`str | None`, `list[dict]`, etc.)
- **Domain**: Russian strings are first-class — column values, keys, literals all in Russian
  - `"здравие"`, `"упокоение"`, `"разовое"`, `"сорокоуст"` are canonical enum values

## Async Pattern

All DB operations are `async`/`await`. Never use sync SQLAlchemy in route handlers.

```python
# Correct
async def get_active_today(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Commemoration)...)
    return result.scalars().all()

# Wrong — never do this
session.execute(...)  # sync
```

## Session Injection

Sessions always come from FastAPI `Depends(get_db)` — never instantiate directly.

```python
@router.get("/today")
async def names_today(db: AsyncSession = Depends(get_db)):
    return await query_service.get_active_today(db)
```

## Settings Access

Import the singleton, never instantiate `Settings()` directly.

```python
from config import settings
# Use: settings.embedding_dim, settings.dedup_threshold
```

## Return Types from Services

Services return `list[dict]` for query results — not ORM objects. Dicts are serialized inline with explicit field selection.

```python
return [
    {
        "commemoration_id": r.id,
        "canonical_name": r.canonical_name,
        "ordered_at": r.ordered_at.isoformat() if r.ordered_at else None,
    }
    for r in result.all()
]
```

## Error Handling

- Validate inputs **before** any DB writes — raise `ValueError` early
- Per-row CSV import: catch exceptions per row, rollback that row, continue
- Use `db.begin_nested()` (savepoints) for queries that might fail (trigram, vector) so failures don't break the outer transaction

```python
try:
    async with db.begin_nested():
        result = await db.execute(trigram_query)
except Exception as e:
    logger.warning("Trigram search failed: %s", e)
```

## Logging

Standard `logging` module, module-level logger.

```python
logger = logging.getLogger(__name__)
logger.info("CSV import: %s", stats)
logger.warning("Trigram similarity search failed: %s", e)
logger.error("Error processing row: %s", e)
```

## Database Deduplication

Two-level dedup strategy:
1. **Order-level**: hash `sha256(date|content)[:64]` stored as `external_id` — prevents duplicate CSV rows
2. **Person-level**: exact → variant → trigram (0.8 threshold) → vector (configurable threshold) → create new

## Concurrent Insert Safety

Use `INSERT ... ON CONFLICT DO NOTHING ... RETURNING` + fallback `SELECT` for concurrent-safe upserts:

```python
stmt = (
    insert(Person)
    .values(...)
    .on_conflict_do_nothing(index_elements=[Person.canonical_name])
    .returning(Person)
)
result = await db.execute(stmt)
person = result.scalar_one_or_none()
if not person:
    result = await db.execute(select(Person).where(...))
    person = result.scalar_one()
```

## NLP Pipeline Style

- Pure functions only in `app/nlp/` — no DB access, no side effects
- `ParsedName` dataclass for all name results
- Confidence score: 1.0 exact dict match, 0.95 variant match, 0.9 context-resolved ambiguous, 0.5 heuristic
- LLM fallback only when `confidence < 0.5` or no names found

## Module Imports

Imports use the `app/` directory as root (set in Dockerfile via `WORKDIR /code/app` or similar):

```python
from config import settings           # not from app.config
from models import Person, Order      # not from app.models.models
from services.order_service import …  # not from app.services
```

## Docstrings

Modules have top-level docstrings explaining design decisions (often in Russian). Functions have brief English docstrings. Comments explaining "why" are common, especially for complex dedup/NLP logic.
