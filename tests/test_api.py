from fastapi.testclient import TestClient

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


def test_invalid_jwt_and_pagination_bounds():
    with TestClient(app) as client:
        assert (
            client.get("/monitors", headers={"Authorization": "Bearer not-a-jwt"}).status_code
            == 401
        )
        headers = auth(client, "bounds@example.com")
        assert client.get("/monitors?limit=0", headers=headers).status_code == 422
        assert client.get("/monitors?limit=101", headers=headers).status_code == 422


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
