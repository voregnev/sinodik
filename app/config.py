"""
Pydantic settings — single source of truth for configuration.

All values can be overridden via environment variables
with the SINODIK_ prefix (e.g. SINODIK_DATABASE_URL).
"""

from typing import Union, List
from pydantic import field_validator, Field
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

    # Auth
    jwt_secret: str                        # required — no default → ValidationError if unset
    jwt_ttl_days: int = 7                  # SINODIK_JWT_TTL_DAYS
    admin_emails: Union[str, List[str]] = Field(default=[])  # SINODIK_ADMIN_EMAILS (comma-separated)
    otp_plaintext_fallback: bool = False   # SINODIK_OTP_PLAINTEXT_FALLBACK
    superuser_email: str = "admin@example.com"   # SINODIK_SUPERUSER_EMAIL
    superuser_password: str | None = None         # SINODIK_SUPERUSER_PASSWORD (optional)
    # When X-Remote-User (from nginx basic auth) equals superuser_email, request is treated as admin

    # SMTP
    smtp_host: str = "localhost"           # SINODIK_SMTP_HOST
    smtp_port: int = 587                   # SINODIK_SMTP_PORT
    smtp_username: str = ""                # SINODIK_SMTP_USERNAME
    smtp_password: str = ""                # SINODIK_SMTP_PASSWORD
    smtp_from_address: str = "noreply@sinodic.local"  # SINODIK_SMTP_FROM_ADDRESS
    smtp_use_tls: bool = True              # SINODIK_SMTP_USE_TLS
    smtp_use_ssl: bool = False             # SINODIK_SMTP_USE_SSL
    smtp_validate_certs: bool = True       # SINODIK_SMTP_VALIDATE_CERTS
    smtp_timeout: int = 30                 # SINODIK_SMTP_TIMEOUT (seconds)

    @field_validator("admin_emails", mode="before")
    @classmethod
    def parse_admin_emails(cls, v):
        if isinstance(v, str):
            return [e.strip().lower() for e in v.split(",") if e.strip()]
        return [e.lower() for e in v] if v else []

    model_config = {"env_prefix": "SINODIK_"}


settings = Settings()
