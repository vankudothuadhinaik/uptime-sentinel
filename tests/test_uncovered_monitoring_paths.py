import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.main import app
from app.models import Incident, Monitor, User
from app.monitoring import _request_with_deadline, _request_with_injected_client, perform_check


def _auth(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "correct horse battery staple"},
    )
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_create_monitor_rejects_quota_limit(monkeypatch):
    from app.main import limiter

    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr("app.main.get_settings", lambda: Settings(max_monitors_per_user=0))
    with TestClient(app) as client:
        headers = _auth(client, "quota-limit@example.com")
        response = client.post(
            "/monitors",
            headers=headers,
            json={"name": "blocked", "url": "https://example.com"},
        )
    assert response.status_code == 429
    assert response.json()["detail"] == "monitor limit reached"


def test_create_monitor_converts_integrity_error_to_conflict(monkeypatch, db_session):
    from app.main import limiter

    monkeypatch.setattr(limiter, "enabled", False)
    with TestClient(app) as client:
        headers = _auth(client, "quota-conflict@example.com")

        def fail_commit():
            raise IntegrityError("insert monitor", {}, RuntimeError("duplicate"))

        monkeypatch.setattr(db_session, "commit", fail_commit)
        response = client.post(
            "/monitors",
            headers=headers,
            json={"name": "conflict", "url": "https://example.com"},
        )
    assert response.status_code == 409


def test_manual_check_rejects_an_existing_lease(monkeypatch, db_session):
    from app.main import limiter

    monkeypatch.setattr(limiter, "enabled", False)
    with TestClient(app) as client:
        headers = _auth(client, "claimed-check@example.com")
        created = client.post(
            "/monitors",
            headers=headers,
            json={"name": "claimed", "url": "https://example.com"},
        )
        monitor = db_session.get(Monitor, created.json()["id"])
        monitor.lease_until = datetime.now(timezone.utc) + timedelta(minutes=1)
        db_session.commit()
        response = client.post(f"/monitors/{monitor.id}/check", headers=headers)
    assert response.status_code == 409


def test_async_request_reports_size_redirect_and_http_failures(monkeypatch):
    from app import monitoring

    monkeypatch.setattr("app.monitoring.validate_target", lambda _: None)
    monkeypatch.setattr("app.monitoring.get_settings", lambda: Settings(max_response_bytes=4))

    class Response:
        def __init__(self, status_code, chunks):
            self.status_code = status_code
            self._chunks = chunks

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def aiter_bytes(self):
            for chunk in self._chunks:
                yield chunk

    class Client:
        response = None

        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def stream(self, *args, **kwargs):
            return self.response

    monitor = Monitor(name="async", url="https://example.com", timeout_seconds=1)
    for response, expected in (
        (Response(200, [b"12345"]), "response_too_large"),
        (Response(302, [b""]), "unsafe_redirect"),
        (Response(503, [b""]), "http_error"),
    ):
        Client.response = response
        monkeypatch.setattr(monitoring.httpx, "AsyncClient", Client)
        result = asyncio.run(_request_with_deadline(monitor))
        assert result[2] == expected

    class FailingClient(Client):
        def stream(self, *args, **kwargs):
            raise httpx.ConnectError("connection failed")

    monkeypatch.setattr(monitoring.httpx, "AsyncClient", FailingClient)
    assert asyncio.run(_request_with_deadline(monitor))[2] == "request_error"

    monkeypatch.setattr(
        "app.monitoring.validate_target",
        lambda _: (_ for _ in ()).throw(RuntimeError("resolver failure")),
    )
    assert asyncio.run(_request_with_deadline(monitor))[2] == "internal_error"


def test_injected_client_handles_timeout_http_and_internal_errors(monkeypatch):
    from app import monitoring

    monitor = Monitor(name="injected", url="https://example.com", timeout_seconds=1)

    class Response:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def iter_bytes(self):
            yield b"ok"

    class Client:
        def stream(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("app.monitoring.validate_target", lambda _: None)
    times = iter((0.0, 2.0))
    monkeypatch.setattr(monitoring.time, "monotonic", lambda: next(times))
    assert _request_with_injected_client(monitor, Client())[2] == "timeout"
    monkeypatch.setattr(monitoring.time, "monotonic", lambda: 0.0)

    class HttpFailureClient:
        def stream(self, *args, **kwargs):
            raise httpx.ConnectError("connection failed")

    assert _request_with_injected_client(monitor, HttpFailureClient())[2] == "request_error"

    class InternalFailureClient:
        def stream(self, *args, **kwargs):
            raise RuntimeError("transport bug")

    assert _request_with_injected_client(monitor, InternalFailureClient())[2] == "internal_error"

    monkeypatch.setattr(
        "app.monitoring.validate_target",
        lambda _: (_ for _ in ()).throw(RuntimeError("resolver failure")),
    )
    assert _request_with_injected_client(monitor, Client())[2] == "internal_error"


def test_consecutive_failure_increments_existing_incident(db_session, monkeypatch):
    user = User(email="incident-increment@example.com", password_hash="test-hash")
    monitor = Monitor(
        owner=user,
        name="incident",
        url="https://example.com",
        interval_seconds=60,
        timeout_seconds=5,
    )
    db_session.add(monitor)
    db_session.commit()
    monkeypatch.setattr("app.monitoring.validate_target", lambda _: None)
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    with httpx.Client(transport=transport) as client:
        perform_check(db_session, monitor, client)
        perform_check(db_session, monitor, client)
    incident = db_session.scalar(select(Incident).where(Incident.monitor_id == monitor.id))
    assert incident is not None
    assert incident.failure_count == 2
