# Uptime Sentinel verification report

Run date: 2026-10-28

## Final decision

**PUBLISHED / NOT READY FOR PRODUCTION**: implementation, local verification,
CI configuration, release hygiene, and documentation are complete on the
published `main` branch. Production remains blocked until the controlled
egress-proxy security tests and deployed API/worker gates pass in CI or staging.

## Source reconciliation

The reviewed project was retained as the base. The attached candidate was inspected but not copied wholesale: its `0003_lease_ownership_token.py` would conflict with the reviewed `0003_lease_tokens.py`, and its monitoring implementation used unbounded `get()` responses and exposed exception text. Its useful production proxy URL validation and proxy-use regression ideas were merged into the reviewed implementation.

## Observed checks

All commands below were run from the project root in the local `.venv` unless noted.

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pip install -e ".[dev]"` | Passed; declared dependencies installed from available cache/index. |
| `.venv\Scripts\python.exe -m pytest -q` | Passed: 20 tests, 6 opt-in infrastructure tests skipped (PostgreSQL/proxy unavailable), 3 deprecation warnings. |
| `.venv\Scripts\python.exe -m ruff check .` | Passed. |
| `.venv\Scripts\python.exe -m ruff format --check .` | Passed; 25 files formatted. |
| `.venv\Scripts\python.exe -m mypy app worker.py migrations tests` | Passed: no issues in 19 source files. |
| `.venv\Scripts\python.exe -m compileall -q app worker.py tests migrations` | Passed. |
| Clean isolated environment install | BLOCKED by the 120-second command limit; the existing environment remains dependency-consistent (`pip check` passed). |
| `DATABASE_URL=sqlite:///./final_candidate_reconcile.db alembic upgrade head` | Passed. |
| `... alembic downgrade base` | Passed. |
| `... alembic upgrade head` | Passed. |
| `.venv\Scripts\python.exe -m pip_audit --skip-editable` | Passed: no known vulnerabilities. |
| Direct login rate-limit smoke test | Passed: statuses 401 x10, then 429. |
| Workflow and Compose structural assertions | Passed: PostgreSQL 16 service, migration/test steps, explicit `pip check`, Docker Compose smoke job, manual fail-closed proxy job, health dependencies, and API-gated worker startup verified. |
| Worker stop-event smoke test | Passed: pre-set stop event exits without polling. |
| `scripts\compose-smoke.ps1` PowerShell syntax | Passed; runtime execution is blocked because Docker is unavailable. |
| Local infrastructure probe | Docker, Podman, PostgreSQL, Redis, `gh`, and proxy environment variables unavailable; bounded WSL Ubuntu start timed out after 10 seconds. GitHub/PyPI TCP reachability was available, but no authorized CI service was configured. |
| GitHub Actions run `40590812969` for commit `3fe82b318095326b572b8c4eb2fb15be69ca1591` | Passed: `checks` and `compose-smoke` succeeded; `proxy-integration` was not executed because the workflow is manual-only and controlled fixture secrets are not configured. |

The migration head is `0003_lease_tokens`. Fresh SQLite migration round trips were successful. PostgreSQL locking/concurrency was not claimed from SQLite.

## Blocked checks

- Docker Compose build/startup: Docker is not installed. Run `docker compose build` and `docker compose up` on a Docker host.
- PostgreSQL multi-worker verification: PostgreSQL client/service is unavailable. Start PostgreSQL, set `DATABASE_URL=postgresql+psycopg://...`, run the Alembic round trip, then execute the scheduler concurrency tests against separate worker sessions.
- PostgreSQL/Redis/Compose tooling is absent in this Windows environment; PostgreSQL concurrency, Redis, and Compose runtime checks remain blocked. CI now provisions PostgreSQL and runs the concurrency test.
- Egress-proxy integration: no controlled proxy or fixture endpoints were available. The new opt-in test module covers public reachability, private-IP blocking, DNS rebinding, redirects, and invalid TLS certificates when explicitly configured. See `EGRESS_PROXY_TESTING.md`; no proxy result is claimed here.
- CI execution: GitHub Actions run `40590812969` passed the automatic PostgreSQL, dependency, quality, migration, and Compose jobs. The manual `workflow_dispatch` proxy job was not executed because controlled fixture secrets were not configured; it fails closed when invoked without them.

## GitHub status

The confirmed project directory is the local checkout of `https://github.com/vankudothuadhinaik/uptime-sentinel.git` on `main`. Local `HEAD` is fast-forwarded to `3fe82b318095326b572b8c4eb2fb15be69ca1591`, matching `origin/main`; no force-push or remote overwrite was used.
