"""
Pydantic settings — single source of truth for configuration.

All values can be overridden via environment variables
with the SINODIK_ prefix (e.g. SINODIK_DATABASE_URL).
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sinodik:sinodik@localhost:5432/sinodik"
    database_url_sync: str = "postgresql://sinodik:sinodik@localhost:5432/sinodik"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    openai_base_url: str = ""
    openai_model: str = ""
    openai_api_key: str = ""

    embedding_url: str = ""
    embedding_model: str = ""
    embedding_api_key: str = ""
    embedding_dim: int = 384
    dedup_threshold: float = 0.85

    model_config = {"env_prefix": "SINODIK_"}


settings = Settings()
