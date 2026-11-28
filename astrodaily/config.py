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
    # Shown on the public Terms and Privacy pages as the address for questions and complaints.
    legal_contact_email: str | None = None

    # Postgres. Railway provides DATABASE_URL as postgresql://...
    database_url: str | None = None

    # Google Sign-In: comma-separated OAuth client IDs (web, Android, iOS) allowed as token audience.
    google_client_ids: str = ""

    # Session tokens issued by this backend.
    jwt_secret: str | None = None
    access_token_minutes: int = 15
    # The home-screen widget refreshes in the background with its own narrow token (it can only read the widget card).
    widget_token_days: int = 30
    refresh_token_days: int = 60

    # Content library: show draft (unreviewed) wording. Keep false in production until a reviewer approves.
    content_allow_draft: bool = False
    # Meaning texts on the Chart tab (planets, houses, Lagna). Shown while still draft; set false to show only reviewed.
    chart_meanings_allow_draft: bool = True

    # Push notifications (Firebase Cloud Messaging). The service-account JSON, as one string. Without it the
    # dispatcher only logs what it would send.
    fcm_service_account_json: str | None = None
    # Longest a daily message may be late (cron down, restarts) before the day is skipped, in minutes.
    notify_max_late_minutes: int = 180

    # Subscriptions. "none": purchases are refused; "fake": a stand-in store for testing (never with real users).
    billing_provider: str = "none"
    # What a person without a subscription gets.
    chat_free_daily_message_limit: int = 5    # user messages per rolling 24 hours; paying users get chat_daily_message_limit
    free_calendar_days_ahead: int = 1         # days after today a free account can open (1 = today and tomorrow)
    daily_horoscope_requires_premium: bool = True  # the written paragraph, the planet cards and the time windows

    # AI chat. Cost and safety limits, all adjustable without a release.
    chat_daily_message_limit: int = 30        # user messages per rolling 24 hours, per account
    chat_max_message_chars: int = 1000
    chat_history_messages: int = 12           # most recent messages sent to the model as history
    chat_compact_keep_messages: int = 4       # when history reaches the limit, older messages are summarised and this many stay
    chat_max_output_tokens: int = 600
    chat_timeout_seconds: int = 30
    chat_max_conversations: int = 50          # per account; the oldest are not auto-deleted, new ones are refused

    # Written daily horoscope (Gemini, saved per profile, day and language). 0 free limit = no limit (everything free).
    daily_horoscope_free_limit: int = 0       # days of written horoscope one account gets free; later days need Pro
    daily_horoscope_max_output_tokens: int = 900
    # The early-morning job that writes today's horoscope for people who used the app recently.
    daily_horoscope_active_days: int = 7      # "active" = the app signed in or refreshed within this many days
    daily_horoscope_build_workers: int = 4    # model calls in parallel
    daily_horoscope_build_max_errors: int = 20  # stop the run after this many failures (outage or quota)

    # Most birth profiles one account may keep (the user's own plus family).
    max_profiles_per_user: int = 5

    # Rate limiting, requests per minute per client IP (sliding window, in memory).
    rate_limit_enabled: bool = True
    rate_limit_panchang_per_minute: int = 60
    rate_limit_auth_per_minute: int = 10
    rate_limit_default_per_minute: int = 120
    rate_limit_chat_per_minute: int = 10
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
