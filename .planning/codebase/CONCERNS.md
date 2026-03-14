# Concerns: Sinodic

## Active Issues

### 1. Missing `starts_at` = Silent Inactivation
**Risk: High**

Commemorations are only "active" when `starts_at` and `expires_at` are both set. CSV imports leave these as `NULL` — records exist in DB but don't appear in any active queries. There's a `bulk_set_starts_at` endpoint but no automated flow. Easy to forget, hard to detect.

`app/services/order_service.py:233` — `starts_at = starts_at_override  # None = не назначено`

### 2. No Integration Tests
**Risk: Medium**

Only the NLP pipeline has tests. Zero coverage for:
- CSV upload → DB persistence
- Active today queries with date arithmetic
- Person deduplication (trigram/vector paths)
- API route validation

A refactor or migration bug could go undetected until production.

### 3. CSV Parser Robustness
**Risk: Medium** (`app/services/csv_parser.py`)

CSV files are from church payment systems with inconsistent formatting. The parser has delimiter normalization but real-world files likely have edge cases not covered by the current implementation. The modified file is unstaged (`M app/services/csv_parser.py` in git status).

### 4. Embedding Service Optional but Silently Degraded
**Risk: Medium**

If `SINODIK_EMBEDDING_URL` is not configured, `embed_name_async()` returns `None` and vector similarity is skipped. This is by design, but means deduplication quality silently degrades. No health check exposes this gap.

`app/services/embedding_service.py` — no error when embedding not configured

### 5. `datetime.utcnow()` Deprecated
**Risk: Low**

`datetime.utcnow()` is deprecated in Python 3.12+. Used in multiple places in models and services. Should be `datetime.now(UTC)` or `datetime.now(timezone.utc)`.

Occurs in: `app/models/models.py:76`, `app/services/order_service.py:354`

### 6. No Pagination on `get_active_today`
**Risk: Low**

`query_service.get_active_today()` returns all active commemorations with no limit. A church with large historical imports could return thousands of records in one query. `get_commemorations()` has pagination but not the main active-today endpoint.

### 7. LLM Fallback Without Rate Limiting
**Risk: Low**

When NLP pipeline confidence < 0.5, `llm_parse_names()` is called. For a large CSV upload with many unknown names, this could trigger many sequential LLM calls without throttling or circuit breaking.

`app/services/order_service.py:239-241`

## Technical Debt

### Uncommitted Migration
`alembic/versions/0005_persons_embedding_vector.py` is untracked (in git status `??`). This migration exists locally but isn't committed — could cause schema drift between environments.

### Docker Port Exposure
`docker-compose.yml` and `docker-compose.prod.yml` have modified port mappings (both in git status `M`). PostgreSQL and Ollama ports are commented out in prod config — correct for security, but the dev config may differ unexpectedly.

### `infra/nginx.dev.conf` and `infra/rebuild_persons_embedding.sh` Untracked
Both new files are untracked. The rebuild script suggests embedding regeneration may be a recurring operational task with no automated trigger.

## Security Notes

- Nginx config uses htpasswd basic auth (referenced in recent commit) — credentials file not in git
- CORS origins configurable via env — defaults allow localhost only
- No SQL injection risk: SQLAlchemy parameterized queries throughout
- `external_id` uniqueness enforced at DB level prevents replay attacks on CSV upload
