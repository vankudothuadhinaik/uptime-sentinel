"""End-to-end smoke test for the running Docker Compose stack.

Uses only the Python standard library so it can run on the GitHub Actions host
without installing extra packages. The worker must execute a real check against
a public HTTPS endpoint; this is a demo smoke test, not proxy-security coverage.
"""

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("UPTIME_SENTINEL_BASE_URL", "http://127.0.0.1:8000")
EMAIL = "compose-smoke@example.com"
PASSWORD = "ci-only-password-12345"
TARGET_URL = "https://example.com"


def request_json(method: str, path: str, payload: dict | None = None, token: str | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}: {details}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"{method} {path} failed: {exc}") from exc


def main() -> None:
    status, health = request_json("GET", "/health/ready")
    assert status == 200 and health == {"status": "ready"}, health

    status, registered = request_json(
        "POST", "/auth/register", {"email": EMAIL, "password": PASSWORD}
    )
    assert status == 201 and registered.get("access_token"), registered

    status, logged_in = request_json(
        "POST", "/auth/login", {"email": EMAIL, "password": PASSWORD}
    )
    assert status == 200 and logged_in.get("access_token"), logged_in
    token = logged_in["access_token"]

    status, monitor = request_json(
        "POST",
        "/monitors",
        {
            "name": "Compose end-to-end smoke",
            "url": TARGET_URL,
            "interval_seconds": 30,
            "timeout_seconds": 8,
            "public": True,
        },
        token,
    )
    assert status == 201 and monitor.get("id"), monitor
    monitor_id = monitor["id"]

    # Wait for the separate worker container to claim and process the due monitor.
    deadline = time.monotonic() + 60
    observed = None
    while time.monotonic() < deadline:
        _, checks = request_json("GET", f"/monitors/{monitor_id}/checks?limit=5", token=token)
        if checks:
            observed = checks[0]
            break
        time.sleep(2)

    assert observed is not None, "worker did not persist a check result within 60 seconds"
    assert observed["is_up"] is True and observed["status_code"] == 200, observed

    _, public_status = request_json("GET", f"/status/{monitor_id}")
    assert public_status["status"] == "up", public_status

    print(
        "Compose end-to-end smoke passed: readiness, registration, login, monitor creation, "
        "worker check persistence, and public status."
    )


if __name__ == "__main__":
    main()
