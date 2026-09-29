from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.
    Values are loaded from the .env file.
    """

    APP_NAME: str = "Stock Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"

    # Comma-separated list of allowed frontend origins, e.g.
    # "http://localhost:3000,https://app.example.com". Kept as a
    # plain string (rather than list[str]) because pydantic-settings'
    # default env-parsing for list fields expects JSON, which is an
    # awkward thing to hand-write in a .env file; CORS_ORIGINS is
    # split into a real list by the `cors_origins` property below.
    CORS_ORIGINS: str = "http://localhost:3000"

    DATABASE_URL: str

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    LOG_LEVEL: str = "INFO"

    DATA_DIRECTORY: str = "data/candles"

    # Optional daily automated sync (upload still has to happen
    # separately; this just runs the processing pipeline on a
    # schedule instead of requiring a manual POST /market-data/sync).
    SYNC_SCHEDULE_ENABLED: bool = False
    SYNC_SCHEDULE_HOUR: int = 18
    SYNC_SCHEDULE_MINUTE: int = 0
    SYNC_SCHEDULE_TIMEZONE: str = "UTC"

    # How long after the daily sync job to run alert evaluation.
    # Alerts need to run against freshly-synced data, so this should
    # comfortably exceed how long a sync actually takes -- if the
    # sync is still running when alerts kick off, alerts will just
    # see yesterday's snapshot and catch up on the next run.
    ALERT_SCHEDULE_DELAY_MINUTES: int = 15

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Where the frontend's "reset password" page lives -- the link
    # emailed to a user is built from this + PASSWORD_RESET_PATH +
    # the raw token, e.g. "http://localhost:3000/reset-password?token=...".
    FRONTEND_URL: str = "http://localhost:3000"
    PASSWORD_RESET_PATH: str = "/reset-password"

    # SMTP delivery for transactional email (currently: password
    # reset links). Left blank by default: when SMTP_HOST is empty,
    # app.core.email logs the message instead of sending it, so
    # forgot-password works out of the box in local/dev setups
    # without requiring real mail credentials. Set these (e.g. to
    # your provider's SMTP relay -- SES, SendGrid, Postmark, or a
    # plain Gmail app-password relay) to actually deliver email.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "no-reply@stockintelligence.local"
    SMTP_FROM_NAME: str = "Stock Intelligence Platform"

    # Backs the login rate limiter (see app/auth/rate_limiter.py) so
    # limits are shared across every worker process/instance and
    # survive restarts. Left blank, the limiter falls back to an
    # in-memory store -- fine for local dev, not safe for anything
    # running more than one worker.
    REDIS_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()