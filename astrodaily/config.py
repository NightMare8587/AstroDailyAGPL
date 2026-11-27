"""Backend configuration, read from environment variables (see .env.example)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    # The chat model is configuration, never hard-coded in logic.
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_api_key: str | None = None
    database_url: str | None = None
    ephemeris_path: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
