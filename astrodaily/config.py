"""Backend configuration, read from environment variables (see .env.example)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    # The chat model is configuration, never hard-coded in logic.
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_api_key: str | None = None
    ephemeris_path: str | None = None

    # Postgres. Railway provides DATABASE_URL as postgresql://...
    database_url: str | None = None

    # Google Sign-In: comma-separated OAuth client IDs (web, Android, iOS) allowed as token audience.
    google_client_ids: str = ""

    # Session tokens issued by this backend.
    jwt_secret: str | None = None
    access_token_minutes: int = 15
    refresh_token_days: int = 60

    @property
    def google_client_id_list(self) -> list[str]:
        return [c.strip() for c in self.google_client_ids.split(",") if c.strip()]

    def require_jwt_secret(self) -> str:
        if self.jwt_secret:
            return self.jwt_secret
        if self.app_env == "local":
            return _DEV_JWT_SECRET
        raise RuntimeError("JWT_SECRET must be set when APP_ENV is not 'local'")


@lru_cache
def get_settings() -> Settings:
    return Settings()
