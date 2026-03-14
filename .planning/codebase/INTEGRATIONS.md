# External Integrations

**Analysis Date:** 2026-03-14

## APIs & External Services

**LLM (Language Model):**
- OpenAI-compatible API (configurable provider)
  - Service: Name parsing fallback for Russian church names not matched by regex pipeline
  - SDK/Client: `openai>=1.0` (AsyncOpenAI)
  - Base URL: `SINODIK_OPENAI_BASE_URL` env var (e.g., `https://api.openai.com/v1`, `http://ollama:11434/v1`)
  - Model: `SINODIK_OPENAI_MODEL` (e.g., `gpt-4o-mini`, `qwen2.5:3b`)
  - Auth: `SINODIK_OPENAI_API_KEY` (Bearer token)
  - Implementation: `app/nlp/llm_client.py` - Optional fallback; pipeline works without it using dictionary only
  - Usage: Extracts church names from CSV comment fields when regex patterns don't match; requires system prompt with detailed parsing rules

**Embedding Service:**
- OpenAI-compatible embedding API (configurable provider)
  - Service: Generate vector embeddings for semantic name matching (fuzzy search fallback)
  - Client: `httpx` async HTTP requests with OpenAI-compatible `/embeddings` endpoint
  - Base URL: `SINODIK_EMBEDDING_URL` (e.g., `https://api.openai.com/v1`, `http://ollama:11434/v1`)
  - Model: `SINODIK_EMBEDDING_MODEL` (e.g., `text-embedding-3-small`, `qwen3-embedding:0.6b`)
  - API Key: `SINODIK_EMBEDDING_API_KEY` (Bearer token)
  - Vector Dimension: `SINODIK_EMBEDDING_DIM` (default: 384)
  - Implementation: `app/services/embedding_service.py` - Optional; disabled when `embedding_url` is not configured
  - Usage: Semantic similarity search for names via pgvector cosine similarity

## Data Storage

**Databases:**
- PostgreSQL 18 (with pgvector and pg_trgm extensions)
  - Connection async: `SINODIK_DATABASE_URL` (e.g., `postgresql+asyncpg://sinodik:sinodik@db:5432/sinodik`)
  - Connection sync: `SINODIK_DATABASE_URL_SYNC` (e.g., `postgresql://sinodik:sinodik@db:5432/sinodik`)
  - Async client: `asyncpg>=0.30`
  - ORM: SQLAlchemy 2.0+ with async support
  - Extensions created at startup (`app/main.py` lifespan) and init (`infra/init.sql`):
    - `vector` - For pgvector semantic search on embeddings
    - `pg_trgm` - Trigram similarity search for typo-tolerant matching
  - Tables: `persons` (names dictionary), `orders` (CSV submissions), `commemorations` (main unit of work)
  - Migrations: Managed by Alembic; run automatically at container startup

**File Storage:**
- Local filesystem only
  - CSV uploads: Processed in-memory (bytes → CsvRow dataclasses)
  - Frontend assets: Static files served from `frontend/dist/`
  - Nginx logs: Mounted volume at `infra/nginx-logs/`
  - Database data: Docker volume `pgdata:/var/lib/postgresql`
  - Ollama models cache: Docker volume `ollamadata:/root/.ollama` (optional, for local LLM)

**Caching:**
- None configured - No Redis, Memcached, or other cache layer

## Authentication & Identity

**Auth Provider:**
- Custom/None - Application has no built-in user authentication
- Basic HTTP Auth: Nginx provides optional basic auth via `htpasswd` file (`infra/htpasswd`)
- CORS: FastAPI middleware configured via `SINODIK_CORS_ORIGINS` env var (JSON array)

## Monitoring & Observability

**Error Tracking:**
- None detected - No integration with Sentry, DataDog, or similar services

**Logs:**
- Console logging via Python standard library
- Nginx access/error logs: Written to `infra/nginx-logs/` (mounted volume)
- Log levels configurable in `alembic.ini` (WARN for sqlalchemy/root, INFO for alembic)

## CI/CD & Deployment

**Hosting:**
- Docker Compose (local/staging)
- Kubernetes-ready (services containerized)
- Traefik + Let's Encrypt (optional production SSL/TLS)

**CI Pipeline:**
- None detected - No GitHub Actions, GitLab CI, or similar service configured

**Deployment:**
- Docker Compose - `docker compose up -d` for development
- Docker Compose with profiles - `docker compose --profile prod up -d` for production (Traefik enabled)
- Traefik service (production only): Reverse proxy with automatic SSL certificate provisioning
  - Let's Encrypt email: `ACME_EMAIL` env var
  - Domain: `SINODIK_HOST` env var (defaults to `sinodik.spyridon.ru`)
  - HTTP to HTTPS redirect enabled

## Environment Configuration

**Required env vars (production):**
- `SINODIK_DATABASE_URL` - Async PostgreSQL connection string
- `SINODIK_DATABASE_URL_SYNC` - Sync PostgreSQL connection string (Alembic)
- `SINODIK_OPENAI_BASE_URL` - LLM API base URL (optional; disables LLM fallback if empty)
- `SINODIK_OPENAI_MODEL` - LLM model name (optional)
- `SINODIK_OPENAI_API_KEY` - LLM API key (optional)
- `SINODIK_EMBEDDING_URL` - Embedding service base URL (optional; disables embeddings if empty)
- `SINODIK_EMBEDDING_MODEL` - Embedding model name (optional)
- `SINODIK_EMBEDDING_API_KEY` - Embedding API key (optional)
- `SINODIK_EMBEDDING_DIM` - Vector dimension (default: 384)
- `SINODIK_DEDUP_THRESHOLD` - Cosine similarity threshold for deduplication (default: 0.85)
- `SINODIK_CORS_ORIGINS` - JSON array of allowed CORS origins
- `ACME_EMAIL` - Email for Let's Encrypt certificate (production only)
- `SINODIK_HOST` - Domain name for Traefik routing (production only)

**Secrets location:**
- `.env` file (gitignored) - Local development
- Environment variables injected at container runtime (production)
- Htpasswd file: `infra/htpasswd` (for Nginx basic auth, optional)

## Webhooks & Callbacks

**Incoming:**
- POST `/api/v1/upload/csv` - CSV file upload endpoint for church payment system integrations
  - Accepts multipart form data with optional query parameters for delimiter and start date
  - Returns processing statistics

**Outgoing:**
- None detected - No outbound webhooks to external services

## Special Integrations

**Ollama (Optional Local LLM):**
- Service: `ollama` (Docker Compose, optional profile `ollama`)
- Images: `ollama/ollama`
- Models: `qwen2.5:3b` (LLM), `qwen3-embedding:0.6b` (embeddings)
- Connection: Container-to-container via `http://ollama:11434/v1`
- Used when: `SINODIK_OPENAI_BASE_URL` = `http://ollama:11434/v1`
- Initialization: `ollama-init` service pulls models on first run (profile: `init`)

**Timeweb Cloud AI Support:**
- Special header handling in `app/nlp/llm_client.py`:
  - If `openai_base_url` contains `timeweb.cloud`, adds `x-proxy-source` header
  - Supports `SINODIK_OPENAI_X_PROXY_SOURCE` configuration

---

*Integration audit: 2026-03-14*
