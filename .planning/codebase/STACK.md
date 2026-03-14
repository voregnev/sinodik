# Technology Stack

**Analysis Date:** 2026-03-14

## Languages

**Primary:**
- Python 3.14 - Backend API and all server-side logic

**Secondary:**
- SQL - PostgreSQL database schema and extensions
- JavaScript/TypeScript - Pre-built React 18 PWA frontend (static assets in `frontend/dist/`)

## Runtime

**Environment:**
- Python 3.14 (slim-trixie Debian base image)

**Package Manager:**
- pip
- Lockfile: `requirements.txt` (present, pinned versions)

## Frameworks

**Core:**
- FastAPI 0.115+ - Web framework, async HTTP server with auto-generated OpenAPI docs
- Uvicorn 0.34+ - ASGI server (2 workers in production)

**ORM & Database:**
- SQLAlchemy 2.0+ - Async ORM with `asyncio` support
- asyncpg 0.30+ - PostgreSQL async driver
- Alembic 1.14+ - Database migrations

**HTTP Client:**
- httpx 0.28+ - Async HTTP requests (used for embedding API calls)
- OpenAI SDK 1.0+ - OpenAI-compatible LLM client

**Testing:**
- pytest 8.0+ - Test runner (configured in `pyproject.toml` with pythonpath)

**PDF/Document Generation:**
- reportlab 4.0+ - PDF rendering (may be used for commemoration documents)

**Middleware & Parsing:**
- python-multipart 0.0.18+ - Multipart form data handling (file uploads)
- pydantic 2.0+ - Data validation and settings
- pydantic-settings 2.0+ - Configuration management

## Key Dependencies

**Critical:**
- `sqlalchemy[asyncio]` - Core ORM; application cannot function without it
- `asyncpg` - PostgreSQL async driver; only way to communicate with database
- `fastapi` - Web framework and routing; no alternatives used
- `pydantic` - Request/response validation throughout API layer
- `openai` - LLM client for name parsing fallback (`app/nlp/llm_client.py`)

**Infrastructure:**
- `pgvector` - PostgreSQL vector extension client (required for semantic search)
- `psycopg2-binary` - Sync PostgreSQL driver (used by Alembic migrations only)
- `httpx` - Async HTTP client for embedding service calls (`app/services/embedding_service.py`)

## Configuration

**Environment:**
- All configuration via `SINODIK_`-prefixed environment variables (defined in `app/config.py`)
- Settings loaded via Pydantic `BaseSettings` into singleton `settings` object
- Configuration injected into application at runtime from `docker-compose.yml` or `.env`

**Build:**
- `pyproject.toml` - Project metadata and pytest configuration
- `requirements.txt` - All Python dependencies with versions
- `Dockerfile` - Multi-stage build (builder + runtime)
- `alembic.ini` - Database migration configuration

## Platform Requirements

**Development:**
- Docker and Docker Compose (all services containerized)
- Python 3.14+ (if running locally outside containers)
- PostgreSQL 18 (via container) with pgvector extension

**Production:**
- Docker Compose or Kubernetes orchestration
- PostgreSQL 18+ with pgvector and pg_trgm extensions
- OpenAI-compatible LLM API (configurable provider via `SINODIK_OPENAI_BASE_URL`)
- OpenAI-compatible embedding API (configurable provider via `SINODIK_EMBEDDING_URL`)
- Traefik reverse proxy (for Let's Encrypt SSL/TLS)
- Nginx (SPA routing + API reverse proxy)

---

*Stack analysis: 2026-03-14*
