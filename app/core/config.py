from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Webhook Relay Service"
    database_url: str = "postgresql+asyncpg://relay:relay@localhost:5432/relay"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
