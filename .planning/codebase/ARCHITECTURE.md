# Architecture: Sinodic

## Pattern

Layered async web API — no domain event system, no CQRS. Clean separation between:
- **HTTP layer** (`app/api/routes/`) — request parsing, validation, response shaping
- **Service layer** (`app/services/`) — business logic, DB operations
- **NLP layer** (`app/nlp/`) — name extraction pipeline (pure Python, no DB)
- **Data layer** (`app/models/models.py`) — SQLAlchemy ORM, three tables

## Layers

```
HTTP Request
    ↓
app/api/routes/*.py          ← FastAPI routers, Depends(get_db)
    ↓
app/services/*.py            ← Business logic, async DB writes
    ↓
app/nlp/name_extractor.py    ← Pure function, no DB
    ↓
app/models/models.py         ← SQLAlchemy ORM (Person, Order, Commemoration)
    ↓
PostgreSQL 18 (asyncpg)
```

## Data Model

```
Person (dictionary)  ←FK──  Commemoration  ──FK→  Order (metadata)
    id                           id                    id
    canonical_name               person_id             user_email
    genitive_name                order_id              source_channel
    gender                       order_type            source_raw
    name_variants[]              period_type           external_id
    embedding (Vector)           prefix                ordered_at
                                 suffix                created_at
                                 ordered_at
                                 starts_at
                                 expires_at
                                 is_active
```

- **Person**: canonical name dictionary with pgvector embedding + pg_trgm index
- **Order**: one CSV row or form submission (metadata only)
- **Commemoration**: atomic unit — one name per record, with date range

## Primary Data Flows

### CSV Upload → Commemorations
```
POST /api/v1/upload/csv
    → csv_parser.parse_csv()           # bytes → list[CsvRow]
    → order_service.process_csv_upload()
        → for each row: process_row()
            → extract_names(names_raw)  # NLP pipeline
            → llm_parse_names()         # LLM fallback if confidence < 0.5
            → Order() created (flush)
            → for each name: find_or_create_person()
                → exact match → variant match → trigram → vector → CREATE
            → Commemoration() created per name
        → commit() per successful row
```

### Active Names Query
```
GET /api/v1/names/today?type=здравие
    → query_service.get_active_today()
        → JOIN Commemoration + Person + Order
        → WHERE is_active AND starts_at <= today <= expires_at
        → ORDER BY type → period → ordered_at → position
```

### Fuzzy Name Search
```
GET /api/v1/names/search?q=Николай
    → query_service.search_names()
        → 1. trigram similarity > 0.3
        → 2. pgvector cosine similarity (if embedding available)
        → 3. ILIKE prefix fallback
        → merge + sort by score DESC
```

## Entry Points

- `app/main.py` — FastAPI app, lifespan (pg extensions init), router registration
- `CMD` in Dockerfile: `alembic upgrade head && uvicorn app.main:app`

## Error Handling Strategy

- Per-row CSV import: catch exceptions, rollback, add to errors[], continue next row
- DB savepoints (`begin_nested()`) for trigram/vector searches — failures don't break main transaction
- Validation before DB writes: `ValueError` raised before `Order` created
- No global exception handler — FastAPI defaults (422 for validation, 500 for unhandled)

## Cross-Cutting Concerns

- **Session management**: `AsyncSession` via `Depends(get_db)` — one session per request
- **Config**: singleton `settings` from `app/config.py` (pydantic-settings, `SINODIK_` prefix)
- **Logging**: standard `logging` module, `logger = logging.getLogger(__name__)`
- **Deduplication**: hash-based (sha256 of date+content) for Orders; multi-level similarity for Persons
