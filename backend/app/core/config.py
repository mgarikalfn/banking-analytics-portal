import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Banking Analytics Portal"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Dedicated PostgreSQL Application Database
    # NOTE: Never point this to bank_dwh_real.
    # When connecting from Windows host to Docker Compose Postgres, use host port 5433.
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/banking_portal_db"

    # Security & Tokens
    SECRET_KEY: str = "insecure-dev-secret-key-replace-in-production-32-chars-min"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Session Cookies (HTTP-only)
    SESSION_COOKIE_NAME: str = "portal_session"
    COOKIE_SECURE: bool = False  # Set to True in production HTTPS
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str = ""

    # CSRF Protection
    CSRF_SECRET_KEY: str = "insecure-dev-csrf-secret-key-32-chars-long"
    CSRF_COOKIE_NAME: str = "portal_csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # Superset Embedded Integration (Optional until integration is configured)
    SUPERSET_BASE_URL: str = "http://localhost:8088"
    SUPERSET_ADMIN_USERNAME: Optional[str] = None
    SUPERSET_ADMIN_PASSWORD: Optional[str] = None
    SUPERSET_GUEST_TOKEN_TIMEOUT_SECS: int = 300

    # Initial Administrator Configuration
    # Requires explicit, secure configuration when initializing a fresh database.
    FIRST_SUPERUSER_EMAIL: Optional[str] = None
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None
    FIRST_SUPERUSER_FULL_NAME: str = "System Administrator"


settings = Settings()
