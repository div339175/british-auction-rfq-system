from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "British Auction RFQ System"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database configuration (defaults to SQLite for frictionless local testing, overridden by env var for PostgreSQL)
    DATABASE_URL: str = "sqlite:///./british_auction.db"

    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
