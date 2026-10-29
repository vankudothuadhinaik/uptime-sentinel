from fastapi.testclient import TestClient
import pytest

from app.main import app


def auth(client, email):
    response = client.post(
        "/auth/register", json={"email": email, "password": "correct horse battery staple"}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_and_auth():
    with TestClient(app) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        headers = auth(client, "alice@example.com")
        assert client.get("/monitors", headers=headers).status_code == 200
        assert (
            client.post(
                "/auth/login", json={"email": "alice@example.com", "password": "wrong password"}
            ).status_code
            == 401
        )


def test_cross_user_isolation_and_public_status():
    with TestClient(app) as client:
        alice = auth(client, "alice2@example.com")
        bob = auth(client, "bob@example.com")
        created = client.post(
            "/monitors",
            headers=alice,
            json={"name": "Docs", "url": "https://example.com", "public": True},
        )
        assert created.status_code == 201
        monitor_id = created.json()["id"]
        assert client.get(f"/monitors/{monitor_id}", headers=bob).status_code == 404
        public = client.get(f"/status/{monitor_id}")
        assert public.status_code == 200 and set(public.json()) == {"name", "status", "last_check"}


def test_validation_and_pause_update():
    with TestClient(app) as client:
        headers = auth(client, "carol@example.com")
        assert (
            client.post(
                "/monitors", headers=headers, json={"name": "bad", "url": "ftp://example.com"}
            ).status_code
            == 422
        )
        created = client.post(
            "/monitors", headers=headers, json={"name": "Docs", "url": "https://example.com"}
        ).json()
        response = client.patch(
            f"/monitors/{created['id']}", headers=headers, json={"is_paused": True}
        )
        assert response.status_code == 200 and response.json()["is_paused"] is True


@pytest.mark.parametrize(
    "field",
    ["name", "url", "interval_seconds", "timeout_seconds", "is_paused", "public"],
)
def test_patch_rejects_explicit_null_for_non_nullable_fields(field):
    with TestClient(app) as client:
        headers = auth(client, f"null-{field}@example.com")
        created_response = client.post(
            "/monitors",
            headers=headers,
            json={"name": "non-null", "url": "https://example.com"},
        )
        assert created_response.status_code == 201
        response = client.patch(
            f"/monitors/{created_response.json()['id']}",
            headers=headers,
            json={field: None},
        )
        assert response.status_code == 422


def test_invalid_jwt_and_pagination_bounds():
    with TestClient(app) as client:
        assert (
            client.get("/monitors", headers={"Authorization": "Bearer not-a-jwt"}).status_code
            == 401
        )
        headers = auth(client, "bounds@example.com")
        assert client.get("/monitors?limit=0", headers=headers).status_code == 422
        assert client.get("/monitors?limit=101", headers=headers).status_code == 422
        created = client.post(
            "/monitors",
            headers=headers,
            json={"name": "bounded", "url": "https://example.com"},
        )
        assert created.status_code == 201
        monitor_id = created.json()["id"]
        assert (
            client.get(f"/monitors/{monitor_id}/incidents?limit=0", headers=headers).status_code
            == 422
        )
        assert (
            client.get(f"/monitors/{monitor_id}/incidents?limit=101", headers=headers).status_code
            == 422
        )


def test_incident_history_has_stable_paginated_response(db_session):
    from datetime import datetime, timedelta, timezone

    from app.models import Incident, Monitor

    with TestClient(app) as client:
        headers = auth(client, "incident-history@example.com")
        created = client.post(
            "/monitors",
            headers=headers,
            json={"name": "history", "url": "https://example.com"},
        )
        assert created.status_code == 201
        monitor_id = created.json()["id"]
        monitor = db_session.get(Monitor, monitor_id)
        now = datetime.now(timezone.utc)
        db_session.add_all(
            [
                Incident(monitor_id=monitor.id, started_at=now, failure_count=1),
                Incident(monitor_id=monitor.id, started_at=now, failure_count=2),
                Incident(monitor_id=monitor.id, started_at=now - timedelta(seconds=1), failure_count=3),
            ]
        )
        db_session.commit()

        page_one = client.get(f"/monitors/{monitor_id}/incidents?limit=2", headers=headers)
        page_two = client.get(
            f"/monitors/{monitor_id}/incidents?limit=2&offset=2", headers=headers
        )
        assert page_one.status_code == page_two.status_code == 200
        ids_one = [item["id"] for item in page_one.json()]
        ids_two = [item["id"] for item in page_two.json()]
        assert len(ids_one) == 2 and len(ids_two) == 1
        assert ids_one[0] > ids_one[1] > ids_two[0]


def test_public_status_does_not_expose_private_fields():
    with TestClient(app) as client:
        headers = auth(client, "public@example.com")
        created = client.post(
            "/monitors",
            headers=headers,
            json={"name": "Public", "url": "https://example.com", "public": True},
        )
        body = client.get(f"/status/{created.json()['id']}").json()
        assert "owner_id" not in body
        assert "url" not in body


def test_manual_check_claims_and_fences_lease(monkeypatch):
    from app import main as main_module
    from app.monitoring import StaleLease

    with TestClient(app) as client:
        headers = auth(client, "manual-check@example.com")
        created = client.post(
            "/monitors",
            headers=headers,
            json={"name": "Manual", "url": "https://example.com"},
        )
        assert created.status_code == 201
        monitor_id = created.json()["id"]
        observed = {}

        def stale_check(db, monitor, client=None, *, lease_token=None):
            observed["token"] = lease_token
            raise StaleLease("synthetic stale lease")

        monkeypatch.setattr(main_module, "perform_check", stale_check)
        response = client.post(f"/monitors/{monitor_id}/check", headers=headers)
        assert response.status_code == 409
        assert observed["token"]
