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

    # Most birth profiles one account may keep (the user's own plus family).
    max_profiles_per_user: int = 5

    # Rate limiting, requests per minute per client IP (sliding window, in memory).
    rate_limit_enabled: bool = True
    rate_limit_panchang_per_minute: int = 60
    rate_limit_auth_per_minute: int = 10
    rate_limit_default_per_minute: int = 120
    # Header holding the real client IP, set by the platform's proxy. Railway overwrites any value the
    # client sends in X-Real-IP, so it is safe to trust there. Default: x-real-ip in production, none locally.
    client_ip_header: str | None = None

    def ip_header(self) -> str | None:
        if self.client_ip_header is not None:
            return self.client_ip_header.strip().lower() or None
        return "x-real-ip" if self.app_env == "production" else None

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
