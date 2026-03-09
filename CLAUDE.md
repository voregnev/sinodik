# Sinodic — Project Guide for Claude

## Project Overview

Sinodic is a church commemoration management system. It processes CSV files from church payment systems, extracts Russian names, and manages commemorative records with date-based queries. The core domain is tracking "commemorations" — prayer requests for living (здравие) or deceased (упокоение) individuals over configurable periods.

## Tech Stack

- **Backend**: Python 3.14, FastAPI 0.115+ (async), SQLAlchemy 2.0+
- **Database**: PostgreSQL 18 with pgvector + pg_trgm extensions
- **Async driver**: asyncpg
- **LLM/Embeddings**: OpenAI-compatible API (configurable provider)
- **Migrations**: Alembic
- **Frontend**: Pre-built React 18 PWA in `frontend/dist/`
- **Infrastructure**: Docker Compose (db + api + nginx)

## Development Commands

```bash
# Start all services
docker compose up -d

# Run tests
pytest tests/ -v

# Run migrations
docker compose exec api alembic upgrade head

# Generate migration after schema changes
docker compose exec api alembic revision --autogenerate -m "description"

# API docs (after startup)
open http://localhost:8000/docs
```

## Project Structure

```
app/
├── main.py              # FastAPI app, routes registration, lifespan hooks
├── config.py            # Pydantic settings (SINODIK_ env prefix)
├── database.py          # Async SQLAlchemy engine & session factory
├── models/models.py     # Person, Order, Commemoration ORM models
├── api/routes/          # FastAPI endpoint handlers
│   ├── health.py        # GET /health
│   ├── upload.py        # POST /api/v1/upload/csv
│   ├── orders.py        # CRUD /api/v1/orders
│   └── names.py         # GET /api/v1/names/{today|search|stats|by-user}
├── services/            # Business logic layer
│   ├── csv_parser.py    # CSV bytes → CsvRow dataclasses
│   ├── order_service.py # Order processing pipeline (CSV → DB)
│   ├── query_service.py # Complex queries (active today, search, stats)
│   ├── embedding_service.py  # OpenAI-compatible embeddings
│   └── period_calculator.py  # Date arithmetic for commemoration periods
└── nlp/                 # Russian church name extraction & parsing
    ├── name_extractor.py    # Two-pass tokenization & resolution
    ├── patterns.py          # Regex patterns, prefix maps, noise filters
    ├── names_dict.py        # Church names dictionary + indexes
    └── llm_client.py        # LLM fallback for unknown names

infra/
├── init.sql             # CREATE EXTENSION vector, pg_trgm (runs at DB init)
└── nginx.conf           # SPA routing + /api/* reverse proxy

alembic/versions/        # Auto-generated migration files
tests/
└── test_name_extractor.py  # 24 pytest cases for NLP pipeline
```

## Data Model

Three entities with a specific relationship — **Commemoration** is the atomic unit:

```
Person (dictionary) ←─FK─ Commemoration ─FK→ Order (metadata)
```

- **Person**: Canonical church name with genitive form, gender, variants, embedding. Used for lookup/deduplication — no business logic.
- **Order**: One CSV row or form submission. Stores submitter email, channel (csv/form/api), external transaction ID. One Order → Many Commemorations.
- **Commemoration** (main table): One name = one record. Has `ordered_at`, `starts_at`, `expires_at` (calculated from period type), `is_active` flag.

**Commemoration types**:
- `order_type`: `здравие` (living) | `упокоение` (deceased)
- `period`: `разовое` (1 day) | `сорокоуст` (40 days) | `полгода` (182 days) | `год` (365 days)
- `prefix`: воин, отрок, мл., нп., р.Б., болящий, болящей

## NLP Pipeline (Critical Logic)

Two-pass Russian name extraction in `app/nlp/`:

1. **Tokenization**: Clean noise (email, phone, payment IDs), split by `, ; / \n \t`, detect prefixes and gender markers `(жен.)/(муж.)`
2. **Resolution**: Use unambiguous names to determine gender context, normalize genitive→nominative, look up in church names dictionary (100+ names), fallback to LLM

**Three-level name search** (`query_service.py`):
1. Exact `canonical_name` match
2. pg_trgm trigram similarity (threshold 0.3) — handles typos
3. pgvector cosine similarity — semantic fuzzy matching

## Environment Configuration

All env vars use **`SINODIK_` prefix** (defined in `app/config.py`):

| Variable | Purpose |
|----------|---------|
| `SINODIK_DATABASE_URL` | Async DB URL (`postgresql+asyncpg://...`) |
| `SINODIK_DATABASE_URL_SYNC` | Sync URL for Alembic |
| `SINODIK_CORS_ORIGINS` | JSON array of allowed origins |
| `SINODIK_OPENAI_BASE_URL` | OpenAI-compatible API base URL |
| `SINODIK_OPENAI_MODEL` | LLM model name |
| `SINODIK_OPENAI_API_KEY` | LLM API key |
| `SINODIK_EMBEDDING_URL` | Embedding service base URL |
| `SINODIK_EMBEDDING_MODEL` | Embedding model name |
| `SINODIK_EMBEDDING_API_KEY` | Embedding API key |
| `SINODIK_EMBEDDING_DIM` | Vector dimension (default: 384) |
| `SINODIK_DEDUP_THRESHOLD` | Cosine similarity dedup threshold (default: 0.85) |

## Docker Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| db | `pgvector/pgvector:pg18` | 5432 | PostgreSQL 18 with extensions |
| api | Built from Dockerfile | 8000 | FastAPI (uvicorn, 2 workers) |
| nginx | `nginx:alpine` | 80 | SPA + reverse proxy |

The `infra/init.sql` runs at database initialization to create required extensions.

## Key Conventions

- All database operations are **async** (use `AsyncSession`, `await`)
- DB sessions injected via FastAPI `Depends()` — never instantiate directly
- Database tables auto-created on API startup via lifespan hook; Alembic for production migrations
- The frontend is **pre-built** — `frontend/dist/` is static; no Node.js toolchain in the repo
- Settings accessed as `from app.config import settings` (singleton Pydantic model)
- The LLM fallback in `nlp/llm_client.py` is optional — pipeline works without it using dictionary only
