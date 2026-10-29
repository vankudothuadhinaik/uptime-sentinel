from functools import lru_cache
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./uptime_sentinel.db"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_storage_uri: str = "memory://"
    egress_proxy_url: str = ""
    egress_proxy_username: str = ""
    egress_proxy_password: str = ""
    jwt_secret: str = "development-only-change-me-change-this-secret"
    access_token_minutes: int = 60
    check_user_agent: str = "UptimeSentinel/0.1"
    result_retention_days: int = 30
    max_monitors_per_user: int = 50
    max_response_bytes: int = 65536
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.app_env.strip().lower() == "production":
            weak_values = {
                "",
                "development-only-change-me",
                "development-only-change-me-change-this-secret",
                "replace-with-a-long-random-development-secret",
                "change-me",
                "secret",
            }

            def is_placeholder(value: str) -> bool:
                normalized = value.strip().lower()
                markers = (
                    "replace_with",
                    "replace-with",
                    "your-",
                    "your_",
                    "placeholder",
                    "example",
                    "change-me",
                    "changeme",
                )
                return not normalized or any(marker in normalized for marker in markers)

            if (
                self.jwt_secret.strip().lower() in weak_values
                or len(self.jwt_secret) < 32
                or is_placeholder(self.jwt_secret)
            ):
                raise ValueError(
                    "JWT_SECRET must be a unique, randomly generated value of at least 32 "
                    "characters when APP_ENV=production"
                )
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise ValueError("DATABASE_URL must use PostgreSQL when APP_ENV=production")
            if not self.egress_proxy_url.strip() or is_placeholder(self.egress_proxy_url):
                raise ValueError(
                    "EGRESS_PROXY_URL is required when APP_ENV=production; use a controlled "
                    "egress proxy that revalidates destinations"
                )
            if len(self.egress_proxy_username) < 8 or is_placeholder(self.egress_proxy_username):
                raise ValueError(
                    "EGRESS_PROXY_USERNAME must be at least 8 characters in production"
                )
            if len(self.egress_proxy_password) < 32 or is_placeholder(self.egress_proxy_password):
                raise ValueError(
                    "EGRESS_PROXY_PASSWORD must be at least 32 characters in production"
                )
            proxy = self.egress_proxy_url
            if any(ord(char) < 32 or ord(char) == 127 for char in proxy):
                raise ValueError("EGRESS_PROXY_URL contains control characters")
            parsed_proxy = urlparse(proxy)
            try:
                _ = parsed_proxy.port
            except ValueError as exc:
                raise ValueError("EGRESS_PROXY_URL has an invalid port") from exc
            if (
                parsed_proxy.scheme not in {"http", "https"}
                or not parsed_proxy.hostname
                or parsed_proxy.username
                or parsed_proxy.password
            ):
                raise ValueError(
                    "EGRESS_PROXY_URL must be an http(s) proxy URL without credentials"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
