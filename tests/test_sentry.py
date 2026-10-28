from sentry_sdk.integrations.fastapi import FastApiIntegration

from app import sentry


def test_sentry_is_disabled_without_dsn(monkeypatch):
    calls = []
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setattr(sentry, "_initialized", False)
    monkeypatch.setattr(sentry.sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))

    sentry.initialize_sentry()

    assert calls == []


def test_sentry_initializes_with_privacy_defaults(monkeypatch):
    calls = []
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
    monkeypatch.setattr(sentry, "_initialized", False)
    monkeypatch.setattr(sentry.sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))

    sentry.initialize_sentry()

    assert len(calls) == 1
    options = calls[0]
    assert options["dsn"] == "https://public@example.invalid/1"
    assert options["send_default_pii"] is False
    assert options["request_bodies"] == "never"
    assert options["include_local_variables"] is False
    assert len(options["integrations"]) == 1
    assert isinstance(options["integrations"][0], FastApiIntegration)

    event = {
        "request": {
            "url": "https://example.test/health?token=do-not-send",
            "headers": {"authorization": "******"},
            "cookies": {"session": "secret"},
            "data": {"password": "secret"},
            "query_string": "token=do-not-send",
        },
        "breadcrumbs": [{"message": "request body"}],
    }
    scrubbed = options["before_send"](event, {})
    assert scrubbed["request"] == {"url": "https://example.test/health"}
    assert "breadcrumbs" not in scrubbed


def test_sentry_initializes_only_once(monkeypatch):
    calls = []
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.invalid/1")
    monkeypatch.setattr(sentry, "_initialized", False)
    monkeypatch.setattr(sentry.sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))

    sentry.initialize_sentry()
    sentry.initialize_sentry()

    assert len(calls) == 1
