"""
Синодик — система хранения записок для поминовения.
FastAPI backend entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import engine
from api.routes import upload, orders, names, health, commemorations, persons, auth, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure extensions exist. Schema is managed by Alembic migrations (run at container start)."""
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.execute(
            __import__("sqlalchemy").text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
        )
    yield
    await engine.dispose()


app = FastAPI(
    title="Синодик API",
    description="Система записок для поминовения — о здравии и об упокоении",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(health.router, tags=["health"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(orders.router, prefix="/api/v1", tags=["orders"])
app.include_router(names.router, prefix="/api/v1", tags=["names"])
app.include_router(commemorations.router, prefix="/api/v1", tags=["commemorations"])
app.include_router(persons.router, prefix="/api/v1", tags=["persons"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
