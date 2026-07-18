"""Application settings, loaded from environment variables.

Uses pydantic-settings so every config value is validated at startup.
Missing required secrets fail fast rather than surfacing at request time.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ASYNC_TO_SYNC_DRIVER = {
    "postgresql+asyncpg": "postgresql+psycopg",
    "postgres+asyncpg": "postgresql+psycopg",
    "postgresql": "postgresql+psycopg",
    "postgres": "postgresql+psycopg",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "SCFMS"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)

    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    # Preferred: set DATABASE_URL directly (e.g. postgresql+psycopg://user:pass@host:5432/db,
    # with special characters in the password percent-encoded — "@" as "%40").
    # If unset, the discrete POSTGRES_* fields below are combined instead (used by
    # docker-compose's bundled db service and the test suite).
    DATABASE_URL: str | None = None
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "scfms"
    POSTGRES_PASSWORD: str = "scfms"
    POSTGRES_DB: str = "scfms"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Object storage
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_PUBLIC_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "scfms_minio"
    S3_SECRET_KEY: str = "scfms_minio_password"
    S3_BUCKET: str = "scfms-media"
    S3_REGION: str = "us-east-1"

    # Login protection
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Geofence defaults
    DEFAULT_NEAR_DISTANCE_METERS: int = 300

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            # The app uses sync SQLAlchemy (psycopg3) throughout — see db/session.py.
            # Normalize an asyncpg-style URL to the psycopg driver so a URL copied
            # from async-style docs/examples still works with this codebase.
            url = self.DATABASE_URL
            scheme, _, rest = url.partition("://")
            driver = _ASYNC_TO_SYNC_DRIVER.get(scheme, scheme)
            return f"{driver}://{rest}"
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Import this everywhere config is needed."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
