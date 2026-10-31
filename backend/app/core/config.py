import json
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_KEY_PATTERNS = [
    "insecure",
    "placeholder",
    "replace-in-production",
    "change-this",
    "changethis",
    "configure_random",
    "dev-secret",
    "test-secret",
    "your_strong",
    "secret_key",
    "example",
]


def validate_signing_key(key_name: str, key_value: Optional[str]) -> str:
    """Validate that a signing key is configured, meets length requirements, and is not a placeholder."""
    if not key_value or not key_value.strip():
        raise ValueError(
            f"{key_name} is required. Please set a cryptographically random key (at least 32 characters) in your environment."
        )

    cleaned = key_value.strip()
    if len(cleaned) < 32:
        raise ValueError(
            f"{key_name} is too short ({len(cleaned)} characters). Minimum required length is 32 characters."
        )

    lower = cleaned.lower()
    for pattern in INSECURE_KEY_PATTERNS:
        if pattern in lower:
            raise ValueError(
                f"{key_name} contains known insecure or placeholder pattern '{pattern}'. "
                "Please configure a cryptographically random 32+ character key (e.g., using 'openssl rand -hex 32')."
            )

    return cleaned


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

    # Security & Tokens (Explicit environment configuration required - no insecure fallbacks)
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Session Cookies (HTTP-only)
    SESSION_COOKIE_NAME: str = "portal_session"
    COOKIE_SECURE: bool = False  # Set to True in production HTTPS
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str = ""

    # CSRF Protection (Explicit environment configuration required - no insecure fallbacks)
    CSRF_SECRET_KEY: Optional[str] = None
    CSRF_COOKIE_NAME: str = "portal_csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # Superset Embedded Integration (Optional until integration is configured)
    # Backend-to-Superset URL. In Docker this is typically host.docker.internal.
    SUPERSET_BASE_URL: str = "http://localhost:8088"
    # Browser-to-Superset URL used by the Embedded SDK.
    SUPERSET_BROWSER_URL: str = "http://localhost:8088"
    SUPERSET_ADMIN_USERNAME: Optional[str] = None
    SUPERSET_ADMIN_PASSWORD: Optional[str] = None
    SUPERSET_GUEST_TOKEN_TIMEOUT_SECS: int = 300

    # Initial Administrator Configuration
    # Requires explicit, secure configuration when initializing a fresh database.
    FIRST_SUPERUSER_EMAIL: Optional[str] = None
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None
    FIRST_SUPERUSER_FULL_NAME: str = "System Administrator"

    def validate_security_keys(self) -> None:
        """Strictly validate that production signing keys are configured, sufficiently long, and non-default."""
        validate_signing_key("SECRET_KEY", self.SECRET_KEY)
        validate_signing_key("CSRF_SECRET_KEY", self.CSRF_SECRET_KEY)


settings = Settings()
