from secrets import token_urlsafe
from typing import Any, cast

import pytest

from app.config import Settings


def valid_production_settings(**overrides: str) -> Settings:
    values = {
        "app_env": "production",
        "database_url": "postgresql+psycopg://uptime:random-password@db.internal:5432/uptime",
        "jwt_secret": token_urlsafe(48),
        "egress_proxy_url": "http://proxy.internal:3128",
        "egress_proxy_username": token_urlsafe(12),
        "egress_proxy_password": token_urlsafe(48),
    }
    values.update(overrides)
    return cast(Any, Settings)(**values)


def test_accepts_production_configuration_with_generated_secrets() -> None:
    settings = valid_production_settings()
    assert settings.app_env == "production"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("jwt_secret", "REPLACE_WITH_AT_LEAST_32_RANDOM_CHARACTERS"),
        ("jwt_secret", "your-long-random-secret-value-that-is-not-real"),
        ("egress_proxy_url", "http://your-private-proxy.internal:3128"),
        ("egress_proxy_username", "REPLACE_WITH_RANDOM_PROXY_USERNAME"),
        ("egress_proxy_password", "REPLACE_WITH_RANDOM_PROXY_PASSWORD_AT_LEAST_32_CHARS"),
    ],
)
def test_rejects_production_placeholder_values(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        valid_production_settings(**{field: value})
