import socket
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models import CheckResult, Incident, Monitor, User
from app.monitoring import perform_check
from app.ssrf import UnsafeTarget, validate_target


def test_ssrf_rejects_loopback_and_private(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )
    with pytest.raises(UnsafeTarget):
        validate_target("http://example.com")


def test_production_rejects_default_or_short_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret="development-only-change-me")
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret="short")
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(app_env="production", jwt_secret="a" * 48, database_url="sqlite:///./unsafe.db")
    with pytest.raises(ValidationError, match="EGRESS_PROXY_URL"):
        Settings(
            app_env="production",
            jwt_secret="a" * 48,
            database_url="postgresql+psycopg://user:pass@db/app",
        )
    for proxy in ("ftp://proxy:3128", "http://user:pass@proxy:3128", "http://proxy:99999"):
        with pytest.raises(ValidationError, match="EGRESS_PROXY_URL"):
            Settings(
                app_env="production",
                jwt_secret="a" * 48,
                database_url="postgresql+psycopg://user:pass@db/app",
                egress_proxy_url=proxy,
            )
    settings = Settings(
        app_env="production",
        jwt_secret="a" * 48,
        database_url="postgresql+psycopg://user:pass@db/app",
        egress_proxy_url="http://egress-proxy:8080",
    )
    assert settings.app_env == "production"


def test_check_records_failure_and_recovery(db_session, monkeypatch):
    user = User(email="monitor-test@example.com", password_hash="test-hash")
    db_session.add(user)
    db_session.commit()
    monitor = Monitor(
        owner_id=user.id,
        name="test",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
    )
    db_session.add(monitor)
    db_session.commit()
    db_session.refresh(monitor)
    monkeypatch.setattr("app.monitoring.validate_target", lambda _: None)

    down = httpx.MockTransport(lambda request: httpx.Response(503))
    with httpx.Client(transport=down) as client:
        perform_check(db_session, monitor, client)
    up = httpx.MockTransport(lambda request: httpx.Response(200))
    with httpx.Client(transport=up) as client:
        perform_check(db_session, monitor, client)

    assert len(monitor.incidents) == 1
    assert monitor.incidents[0].resolved_at is not None


def test_worker_respects_monitor_interval(monkeypatch, db_session):
    from worker import run_once

    user = User(email="scheduler-test@example.com", password_hash="test-hash")
    db_session.add(user)
    db_session.commit()
    monitor = Monitor(
        owner_id=user.id,
        name="scheduled",
        url="https://example.com",
        interval_seconds=300,
        timeout_seconds=5,
    )
    db_session.add(monitor)
    db_session.commit()
    db_session.refresh(monitor)
    monitor_id = monitor.id

    monkeypatch.setattr("worker.SessionLocal", lambda: db_session)
    calls = []
    monkeypatch.setattr("worker.perform_check", lambda db, item: calls.append(item.id))
    now = datetime.now(timezone.utc)
    monitor.next_check_at = now + timedelta(seconds=280)
    db_session.add(
        CheckResult(monitor_id=monitor.id, checked_at=now - timedelta(seconds=20), is_up=True)
    )
    db_session.commit()

    assert run_once(now=now) == 0
    assert calls == []
    assert run_once(now=now + timedelta(seconds=301)) == 1
    assert calls == [monitor_id]


def test_worker_skips_paused_and_claimed_monitors(monkeypatch, db_session):
    from worker import run_once

    user = User(email="paused@example.com", password_hash="test-hash")
    db_session.add(user)
    db_session.commit()
    paused = Monitor(
        owner_id=user.id,
        name="paused",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
        is_paused=True,
    )
    leased = Monitor(
        owner_id=user.id,
        name="leased",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
        lease_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db_session.add_all([paused, leased])
    db_session.commit()
    monkeypatch.setattr("worker.SessionLocal", lambda: db_session)
    calls = []
    monkeypatch.setattr("worker.perform_check", lambda db, item: calls.append(item.name))
    assert run_once() == 0
    assert calls == []


def test_worker_claim_is_exclusive_and_expired_claim_can_be_reclaimed(db_session):
    from worker import _claim_due, _finish_claim

    user = User(email="claims@example.com", password_hash="test-hash")
    monitor = Monitor(
        owner=user,
        name="claims",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
        next_check_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db_session.add(monitor)
    db_session.commit()
    now = datetime.now(timezone.utc)

    first = _claim_due(db_session, now)
    assert first is not None
    _, first_token = first
    assert _claim_due(db_session, now) is None

    current = db_session.get(Monitor, monitor.id)
    current.lease_until = now - timedelta(seconds=1)
    db_session.commit()
    second = _claim_due(db_session, now)
    assert second is not None
    _, second_token = second
    assert second_token != first_token
    assert _finish_claim(db_session, monitor.id, first_token, now) is False
    assert db_session.get(Monitor, monitor.id).lease_token == second_token


def test_worker_slow_check_keeps_claim_until_completion(monkeypatch, db_session):
    from worker import run_once

    user = User(email="slow@example.com", password_hash="test-hash")
    monitor = Monitor(
        owner=user,
        name="slow",
        url="https://example.com",
        interval_seconds=30,
        timeout_seconds=10,
    )
    db_session.add(monitor)
    db_session.commit()
    monitor_id = monitor.id
    monkeypatch.setattr("worker.SessionLocal", lambda: db_session)
    observed = []

    def slow_check(db, item):
        observed.append((item.lease_token, item.lease_until))

    monkeypatch.setattr("worker.perform_check", slow_check)
    assert run_once(now=datetime.now(timezone.utc)) == 1
    assert observed[0][0] is not None
    assert observed[0][1] is not None
    assert db_session.get(Monitor, monitor_id).lease_token is None


def test_stale_worker_cannot_finish_newer_lease(db_session):
    from worker import _finish_claim

    user = User(email="fencing@example.com", password_hash="test-hash")
    db_session.add(user)
    db_session.commit()
    monitor = Monitor(
        owner_id=user.id,
        name="fenced",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
        lease_token="new-owner",
    )
    db_session.add(monitor)
    db_session.commit()
    monitor_id = monitor.id
    assert _finish_claim(db_session, monitor_id, "old-owner", datetime.now(timezone.utc)) is False
    current = db_session.get(Monitor, monitor_id)
    assert current.lease_token == "new-owner"


def test_worker_exception_releases_claim(monkeypatch, db_session):
    from worker import run_once

    user = User(email="exception@example.com", password_hash="test-hash")
    db_session.add(user)
    db_session.commit()
    monitor = Monitor(
        owner_id=user.id,
        name="exception",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
    )
    db_session.add(monitor)
    db_session.commit()
    monitor_id = monitor.id
    monkeypatch.setattr("worker.SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        "worker.perform_check", lambda db, item: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    with pytest.raises(RuntimeError, match="boom"):
        run_once(now=datetime.now(timezone.utc))
    current = db_session.get(Monitor, monitor_id)
    assert current.lease_token is None
    assert current.next_check_at is not None


def test_ssrf_rejects_mapped_and_mixed_dns(monkeypatch):
    mixed = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443)),
    ]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: mixed)
    with pytest.raises(UnsafeTarget):
        validate_target("https://example.com")
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::ffff:127.0.0.1", 443, 0, 0))
        ],
    )
    with pytest.raises(UnsafeTarget):
        validate_target("https://example.com")


def test_ssrf_rejects_malformed_targets():
    for target in (
        "ftp://example.com",
        "https://user:password@example.com",
        "https://example.com:99999",
        "https://example.com/\nforbidden",
    ):
        with pytest.raises(UnsafeTarget):
            validate_target(target)


def test_redirect_is_recorded_as_down(db_session, monkeypatch):
    user = User(email="redirect@example.com", password_hash="test-hash")
    db_session.add(user)
    db_session.commit()
    monitor = Monitor(
        owner_id=user.id,
        name="redirect",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
    )
    db_session.add(monitor)
    db_session.commit()
    monkeypatch.setattr("app.monitoring.validate_target", lambda _: None)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1"})
    )
    with httpx.Client(transport=transport) as client:
        result = perform_check(db_session, monitor, client)
    assert result.is_up is False
    assert result.error_category == "unsafe_redirect"


def test_response_size_limit_is_enforced(db_session, monkeypatch):
    user = User(email="large-response@example.com", password_hash="test-hash")
    db_session.add(user)
    db_session.commit()
    monitor = Monitor(
        owner_id=user.id,
        name="large",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
    )
    db_session.add(monitor)
    db_session.commit()
    monkeypatch.setattr("app.monitoring.validate_target", lambda _: None)
    monkeypatch.setattr("app.monitoring.get_settings", lambda: Settings(max_response_bytes=4))
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"12345"))
    with httpx.Client(transport=transport) as client:
        result = perform_check(db_session, monitor, client)
    assert result.is_up is False
    assert result.error_category == "response_too_large"


def test_monitor_client_uses_configured_proxy(monkeypatch, db_session):
    from app import monitoring

    user = User(email="proxy@example.com", password_hash="test-hash")
    monitor = Monitor(
        owner_id=user.id,
        name="proxy",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
    )
    db_session.add(user)
    db_session.flush()
    monitor.owner_id = user.id
    db_session.add(monitor)
    db_session.commit()
    monkeypatch.setattr("app.monitoring.validate_target", lambda _: None)
    monkeypatch.setattr(
        "app.monitoring.get_settings",
        lambda: Settings(egress_proxy_url="http://proxy.test:3128"),
    )
    captured = {}

    class FakeResponse:
        status_code = 200

        def iter_bytes(self):
            yield b"ok"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def stream(self, *args, **kwargs):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(monitoring.httpx, "Client", FakeClient)
    result = monitoring.perform_check(db_session, monitor)
    assert result.is_up is True
    assert captured["proxy"] == "http://proxy.test:3128"
    assert captured["trust_env"] is False
    assert captured["follow_redirects"] is False


def test_cleanup_old_results_removes_expired_checks_but_keeps_recent_checks_and_incidents(
    monkeypatch, db_session
):
    from worker import cleanup_old_results

    monkeypatch.setattr("worker.get_settings", lambda: Settings(result_retention_days=30))
    now = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
    user = User(email="retention@example.com", password_hash="test-hash")
    db_session.add(user)
    db_session.commit()
    monitor = Monitor(
        owner_id=user.id,
        name="retention",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
    )
    db_session.add(monitor)
    db_session.commit()
    db_session.refresh(monitor)

    expired = CheckResult(
        monitor_id=monitor.id,
        checked_at=now - timedelta(days=31),
        is_up=False,
        error_category="http_error",
    )
    recent = CheckResult(
        monitor_id=monitor.id,
        checked_at=now - timedelta(days=29),
        is_up=True,
    )
    incident = Incident(
        monitor_id=monitor.id,
        started_at=now - timedelta(days=45),
        failure_count=3,
    )
    db_session.add_all([expired, recent, incident])
    db_session.commit()
    expired_id, recent_id, incident_id = expired.id, recent.id, incident.id

    assert cleanup_old_results(db_session, now=now) == 1
    assert db_session.get(CheckResult, expired_id) is None
    assert db_session.get(CheckResult, recent_id) is not None
    assert db_session.get(Incident, incident_id) is not None
    assert cleanup_old_results(db_session, now=now) == 0
