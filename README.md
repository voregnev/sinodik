# ☦️ Синодик — Система записок для поминовения

Веб-приложение (PWA) для хранения и управления записками о здравии и упокоении.

## Архитектура

```mermaid
graph LR
    A["PWA (React)<br/>Mobile-first<br/>+ CSV upload"] -->|Nginx :80| B["FastAPI API<br/>Python 3.14<br/>+ NLP parser"]
    B -->|uvicorn :8000| C["PostgreSQL 18<br/>+ pgvector<br/>+ pg_trgm"]
```

Опционально: Ollama (LLM + эмбеддинги) для разбора имён и семантического поиска.

## Быстрый старт

```bash
# 1. Клонировать и настроить
cp .env.example .env
# Опционально: SINODIK_OPENAI_* / SINODIK_EMBEDDING_* или Ollama в docker-compose

# 2. Запустить
docker compose up -d

# 3. При первом запуске (Ollama) — подтянуть модели:
docker compose --profile init up -d

# 4. Открыть
# API docs:  http://localhost:8000/docs
# PWA:       http://localhost
```

Таблицы создаются автоматически при старте (`lifespan`).
Для production-миграций используется Alembic:

```bash
docker compose exec api alembic upgrade head
```

## Структура проекта

```
sinodik/
├── app/
│   ├── main.py                  # FastAPI entry point + lifespan
│   ├── config.py                # Pydantic settings (SINODIK_ env prefix)
│   ├── database.py              # Async SQLAlchemy engine + session
│   ├── api/
│   │   └── routes/
│   │       ├── health.py        # GET /health
│   │       ├── upload.py        # POST /api/v1/upload/csv
│   │       ├── orders.py        # CRUD /api/v1/orders
│   │       ├── commemorations.py # GET/PATCH/DELETE /api/v1/commemorations, bulk-update
│   │       └── names.py         # GET /api/v1/names/today|search|stats|by-user
│   ├── models/
│   │   ├── __init__.py          # re-export Person, Order, Commemoration
│   │   └── models.py            # SQLAlchemy models
│   ├── services/
│   │   ├── csv_parser.py        # CSV bytes → list[CsvRow]
│   │   ├── period_calculator.py # period_type → expires_at
│   │   ├── order_service.py     # CSV row / form → Order + N Commemorations
│   │   ├── query_service.py     # Today's names, fuzzy search, stats
│   │   └── embedding_service.py # OpenAI-compatible embeddings
│   └── nlp/
│       ├── __init__.py          # re-export extract_names
│       ├── patterns.py          # Regex, prefix/suffix maps
│       ├── names_dict.py        # Church names dictionary
│       ├── name_extractor.py    # Two-pass name parsing
│       └── llm_client.py        # LLM fallback (OpenAI-compatible)
├── frontend/
│   ├── SinodikApp.jsx           # React PWA (single-page)
│   └── ModelDiagram.jsx         # Data model + API docs
├── infra/
│   ├── init.sql                 # CREATE EXTENSION vector, pg_trgm
│   └── nginx.conf               # SPA fallback + reverse proxy to API
├── alembic/
│   ├── env.py                   # Migration environment
│   ├── script.py.mako
│   └── versions/
├── tests/
│   └── test_name_extractor.py   # Pytest: NLP pipeline
├── docker-compose.yml           # db + api + nginx (+ ollama, ollama-init profile)
├── Dockerfile                   # Python 3.14-slim
├── requirements.txt
├── alembic.ini
├── .env.example
├── .gitignore
└── .dockerignore
```

## Docker-сервисы

| Сервис | Образ | Порт | Назначение |
|--------|-------|------|------------|
| **db** | `pgvector/pgvector:pg18` | 5432 | PostgreSQL + pgvector + pg_trgm |
| **api** | `build: .` | 8000 | FastAPI backend (uvicorn, 2 workers) |
| **nginx** | `nginx:alpine` | 80 | Serve PWA + reverse proxy `/api/` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/upload/csv` | Загрузка CSV (query: delimiter, starts_at) |
| POST | `/api/v1/orders` | Создание заказа вручную (body: order_type, period_type, names_text, user_email, need_receipt, starts_at) |
| GET | `/api/v1/orders` | Список заказов (limit, offset) |
| PATCH | `/api/v1/orders/{id}` | Редактирование заказа |
| DELETE | `/api/v1/orders/{id}` | Удаление заказа |
| GET | `/api/v1/commemorations` | Список поминовений для управления (no_start_date, limit, offset) |
| PATCH | `/api/v1/commemorations/{id}` | Редактирование записи (prefix, suffix, period_type, starts_at — expires_at пересчитывается) |
| DELETE | `/api/v1/commemorations/{id}` | Удаление одной записи (одно имя) |
| POST | `/api/v1/commemorations/bulk-update` | Массовая установка starts_at (body: ids, starts_at) |
| GET | `/api/v1/names/today` | Активные имена на сегодня (query: order_type) |
| GET | `/api/v1/names/search?q=` | Fuzzy-поиск по именам |
| GET | `/api/v1/names/stats` | Статистика для дашборда |
| GET | `/api/v1/names/by-user?email=` | Поминовения заказчика по email |

## Модель данных

```
  Person              Order                Commemoration
  ────────            ────────             ──────────────────
  Справочник          Метаданные           ГЛАВНАЯ ТАБЛИЦА
  уникальных          заказа               Одно имя = одна запись
  имён

  id                  id                   id
  canonical_name      user_email           person_id → Person
  genitive_name      need_receipt          order_id  → Order
  gender              source_channel       order_type (здр/уп)
  name_variants[]     source_raw           period_type
  embedding           external_id          prefix, suffix
                       ordered_at           ordered_at / starts_at / expires_at
                       created_at           position, is_active
  Person (1) ←── (M) Commemoration (M) ──→ (1) Order
```

## Парсинг имён

Two-pass pipeline обработки текстового поля:

**Pass 1 — Tokenize:**
1. **Очистка** — удаление email, телефонов, номеров карт, текста о платежах
2. **Разделение** — split по `, ; / \n \t`
3. **Префиксы** — распознавание: воин, мл., отр., нпр., иер., уб., р.Б., болящ. (можно два подряд: иер. уб.)
4. **Суффиксы** — «со чадом» / «со чады» сохраняются в записи
5. **Гендерные маркеры** — `(жен.)`, `(муж.)` в скобках

**Pass 2 — Resolve:**
6. **Контекст падежа** — определение род./им. по неамбигуальным именам
7. **Разрешение амбигуальности** — «Александра» → Александр(м) или Александра(ж) по контексту
8. **Нормализация** — родительный → именительный падеж (Тамары → Тамара)
9. **Валидация** — словарь 100+ церковных имён + heuristic fallback
10. **LLM fallback** — OpenAI-совместимый API для сложных случаев (опционально)

## Поиск имён

Три уровня поиска (от быстрого к умному):

1. **Exact match** — точное совпадение `canonical_name`
2. **pg_trgm** — trigram similarity > 0.3 (опечатки, варианты написания)
3. **pgvector** — cosine similarity embeddings (семантический поиск)

## Конфигурация

Все параметры задаются через переменные окружения с префиксом `SINODIK_`:

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `SINODIK_DATABASE_URL` | `postgresql+asyncpg://sinodik:sinodik@localhost:5432/sinodik` | Async DB URL |
| `SINODIK_DATABASE_URL_SYNC` | `postgresql://sinodik:sinodik@localhost:5432/sinodik` | Sync DB URL (Alembic) |
| `SINODIK_CORS_ORIGINS` | `["http://localhost:5173","http://localhost:3000","http://localhost"]` | CORS origins |
| `SINODIK_OPENAI_BASE_URL` | — | Base URL OpenAI-совместимого LLM (например http://ollama:11434/v1) |
| `SINODIK_OPENAI_MODEL` | — | Модель LLM |
| `SINODIK_OPENAI_API_KEY` | — | API ключ для LLM (для Ollama можно произвольный) |
| `SINODIK_EMBEDDING_URL` | — | Base URL OpenAI-совместимого Embedding API |
| `SINODIK_EMBEDDING_MODEL` | — | Модель эмбеддингов |
| `SINODIK_EMBEDDING_API_KEY` | — | API ключ для эмбеддингов |
| `SINODIK_EMBEDDING_DIM` | `384` | Размерность вектора |
| `SINODIK_DEDUP_THRESHOLD` | `0.85` | Порог дедупликации по косинусной близости |

## Тесты

```bash
# Запуск тестов
pytest tests/ -v

# Только парсер имён
pytest tests/test_name_extractor.py -v
```
