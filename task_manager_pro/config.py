"""
config.py

Single source of truth for runtime configuration.

Every tunable (database URL, JWT secret, bcrypt cost, CORS origins, SMTP
credentials, rate limits, observability switches) is declared once here as a
typed, validated ``pydantic-settings`` model. Values are read from the process
environment and, if present, a ``.env`` file in the working directory.

Access the configuration through :func:`get_settings`, which caches a single
``Settings`` instance for the lifetime of the process. Tests that need to
change configuration call :func:`reset_settings` after mutating ``os.environ``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Historical placeholder that shipped in early ``.env.template`` files. Refusing
# it explicitly guards against copy-pasted templates reaching production.
_INSECURE_PLACEHOLDER = "your-secret-key-change-in-production"
MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    """Validated application settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -----------------------------------------------------
    app_name: str = "Task Manager PRO API"
    environment: Literal["development", "test", "production"] = "development"
    host: str = "127.0.0.1"
    port: int = Field(8000, ge=1, le=65535)
    # Comma-separated list; see :attr:`cors_origin_list`.
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # --- Persistence -----------------------------------------------------
    database_url: str = "sqlite:///./tasks.db"
    sql_echo: bool = False

    # --- Security --------------------------------------------------------
    secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(30, ge=1)
    # bcrypt work factor. 12 is the production default; tests lower it to 4
    # so the suite is not dominated by password hashing.
    bcrypt_rounds: int = Field(12, ge=4, le=31)
    rate_limit_enabled: bool = True
    # Sliding-window budget for the unauthenticated auth endpoints, per client.
    auth_rate_limit_per_minute: int = Field(20, ge=1)

    # --- Observability ---------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = False
    metrics_enabled: bool = True

    # --- Email reminders -------------------------------------------------
    email_user: Optional[str] = None
    email_pass: Optional[SecretStr] = None
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = Field(587, ge=1, le=65535)

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not raw or raw == _INSECURE_PLACEHOLDER:
            raise ValueError(
                "SECRET_KEY is not set (or is still the placeholder value). "
                "Refusing to start with an insecure JWT signing key. Generate "
                "one with `openssl rand -hex 32` and set it as SECRET_KEY."
            )
        if len(raw) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters "
                f"(got {len(raw)}). Generate one with `openssl rand -hex 32`."
            )
        return value

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError(f"Unsupported LOG_LEVEL: {value}")
        return level

    @property
    def cors_origin_list(self) -> List[str]:
        """CORS origins as a list, ignoring blanks."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def email_configured(self) -> bool:
        return bool(self.email_user and self.email_pass)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached :class:`Settings` instance."""
    return Settings()  # type: ignore[call-arg]  # secret_key comes from env


def reset_settings() -> None:
    """Drop the cached settings so the next :func:`get_settings` re-reads env."""
    get_settings.cache_clear()
