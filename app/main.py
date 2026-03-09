"""
Синодик — система хранения записок для поминовения.
FastAPI backend entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.api.routes import upload, orders, names, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (dev mode). Use Alembic in production."""
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.execute(
            __import__("sqlalchemy").text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
        )
        await conn.run_sync(Base.metadata.create_all)
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
