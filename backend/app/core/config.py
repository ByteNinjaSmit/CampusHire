"""Application settings (pydantic-settings). All values come from the environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://campushire:campushire@postgres:5432/campushire"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://campushire:campushire@postgres:5432/campushire_test"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    JWT_SECRET: str = "change-me-dev-only-0123456789abcdef0123456789abcdef"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL_SECONDS: int = 900
    REFRESH_TTL_DAYS: int = 7
    COOKIE_SECURE: bool = False
    CORS_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"

    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "campushire"
    MINIO_SECRET_KEY: str = "campushire-secret"
    MINIO_REGION: str = "us-east-1"
    BUCKET_RESUMES: str = "resumes"
    BUCKET_DOCUMENTS: str = "documents"
    BUCKET_REPORTS: str = "reports"

    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    MAIL_FROM: str = "CampusHire <no-reply@campushire.dev>"

    RUN_MIGRATIONS: bool = True
    SEED_DEMO: bool = True
    RATE_LIMIT_ENABLED: bool = True

    # Token lifetimes for e-mail flows
    VERIFY_TOKEN_TTL_HOURS: int = 24
    RESET_TOKEN_TTL_HOURS: int = 1

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def buckets(self) -> list[str]:
        return [self.BUCKET_RESUMES, self.BUCKET_DOCUMENTS, self.BUCKET_REPORTS]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
