# Structure: Sinodic

## Directory Layout

```
sinodic/
├── app/                          # Application source
│   ├── main.py                   # FastAPI app entry point, router registration
│   ├── config.py                 # Pydantic settings (SINODIK_ prefix)
│   ├── database.py               # Async SQLAlchemy engine & session factory
│   ├── api/
│   │   └── routes/
│   │       ├── health.py         # GET /health
│   │       ├── upload.py         # POST /api/v1/upload/csv
│   │       ├── orders.py         # CRUD /api/v1/orders
│   │       ├── names.py          # GET /api/v1/names/{today|search|stats|by-user}
│   │       ├── commemorations.py # CRUD /api/v1/commemorations
│   │       └── persons.py        # GET /api/v1/persons
│   ├── models/
│   │   └── models.py             # Person, Order, Commemoration ORM models
│   ├── services/
│   │   ├── csv_parser.py         # CSV bytes → CsvRow dataclasses
│   │   ├── order_service.py      # Order processing pipeline + Person dedup
│   │   ├── query_service.py      # Complex queries (active today, search, stats)
│   │   ├── embedding_service.py  # OpenAI-compatible embeddings client
│   │   └── period_calculator.py  # Date arithmetic for commemoration periods
│   └── nlp/
│       ├── name_extractor.py     # Two-pass tokenization & resolution (main)
│       ├── patterns.py           # Regex patterns, prefix maps, noise filters
│       ├── names_dict.py         # Church names dictionary + lookup indexes
│       └── llm_client.py         # LLM fallback for unknown names
├── alembic/
│   ├── env.py                    # Alembic configuration
│   └── versions/                 # Migration files (auto-generated)
├── infra/
│   ├── init.sql                  # CREATE EXTENSION vector, pg_trgm
│   ├── nginx.conf                # Production: SPA routing + /api/* proxy
│   └── nginx.dev.conf            # Development nginx config
├── tests/
│   ├── test_name_extractor.py    # 24+ pytest cases for NLP pipeline
│   └── test_llm_client.py        # LLM client tests
├── frontend/
│   └── dist/                     # Pre-built React 18 PWA (static, no Node.js)
├── docker-compose.yml            # Development: db + api + nginx
├── docker-compose.prod.yml       # Production: adds Traefik, auth
├── Dockerfile                    # Python 3.14 API image
└── requirements.txt              # Python dependencies
```

## Key File Locations

| What | Where |
|------|-------|
| App entry point | `app/main.py` |
| Settings | `app/config.py` |
| DB models | `app/models/models.py` |
| Core business logic | `app/services/order_service.py` |
| NLP pipeline | `app/nlp/name_extractor.py` |
| Church names dictionary | `app/nlp/names_dict.py` |
| DB migrations | `alembic/versions/` |
| DB init (extensions) | `infra/init.sql` |

## Where to Add New Code

| Task | Location |
|------|----------|
| New API endpoint | `app/api/routes/` — new file or extend existing |
| New business logic | `app/services/` — new service or extend existing |
| New DB model | `app/models/models.py` + `alembic revision --autogenerate` |
| NLP pattern change | `app/nlp/patterns.py` |
| New church name | `app/nlp/names_dict.py` |
| New test | `tests/` |

## Naming Conventions

- **Files**: snake_case (`order_service.py`, `name_extractor.py`)
- **Classes**: PascalCase (`Person`, `OrderService`, `ParsedName`)
- **Functions**: snake_case (`extract_names`, `find_or_create_person`)
- **Routes**: prefixed with `/api/v1/` (except `/health`)
- **Env vars**: `SINODIK_` prefix, snake_case (`SINODIK_DATABASE_URL`)
- **Migration files**: `000N_description.py` (e.g., `0005_persons_embedding_vector.py`)
