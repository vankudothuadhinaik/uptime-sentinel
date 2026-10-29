# Uptime Sentinel verification report

Run date: 2026-10-29

## Project decision

**Portfolio scope: free GitHub repository, CI, and local Docker Compose demo.** Paid hosting and production uptime guarantees are out of scope. This report distinguishes automated evidence from checks that have not been run.

## Latest completed end-to-end CI evidence

[Run #200](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40837738417) on commit `91ac1b553664aedc139c52c11b16ccdfc841018f` completed successfully.

| Job | Result | What it establishes |
|---|---|---|
| `checks` | **PASS** | Dependency consistency, Ruff lint/format, mypy, PostgreSQL concurrency tests, pytest/coverage, Codecov upload, compileall, dependency audit, and PostgreSQL/SQLite migration checks passed. |
| `compose-smoke` | **PASS** | Compose configuration validation, container build/start, API liveness, registration/login, monitor creation, worker check persistence, and public status all passed. |
| `proxy-integration` | **SKIPPED** | Controlled proxy fixture URLs/secrets are not configured. This is not a security pass. |

Run #197 also validates the CI concurrency optimization that cancels superseded runs and conserves free runner minutes.

## Implemented project capabilities

- FastAPI API with registration/login, authenticated monitor management, and ownership-scoped monitor/check/incident queries.
- PostgreSQL-compatible Alembic migrations and a database-backed worker with lease/fencing logic.
- HTTP/HTTPS checks with bounded response reads, timeouts, latency/failure history, and incident open/update/recovery behavior.
- Application-side SSRF checks, URL credential rejection, redirects disabled, and production startup validation.
- Unit and PostgreSQL concurrency tests, dependency auditing, migration checks, Docker Compose smoke CI, and automated registration-to-worker end-to-end smoke.
- Architecture/lifecycle diagrams and setup, troubleshooting, security, and release documentation.
- Proxy authentication fail-closed fix merged in [PR #6](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/6).
- Paid Render blueprint removed. No hosted API, worker, or database is required for the intended portfolio project.

## Verification limits

- The latest confirmed successful CI run #200 verifies the repository workflow. Earlier run #197 verified readiness, registration/login, monitor creation, worker check persistence, and public status against `https://example.com`. The controlled proxy-integration job remains skipped because its dedicated fixture URLs/secrets are not configured.
- A separate local Docker Compose run was completed on 2026-10-29 using an isolated Compose project (`uptime-sentinel-audit`); the real registration-to-worker E2E flow passed. See **Local Docker Compose verification (2026-10-29)** below.
- External proxy integration tests remain skipped because controlled fixtures/secrets are not configured. Do not treat the skip as a pass.
- The old public test proxy has not passed the controlled security suite and must not be used for sensitive or production traffic.
- Historical local verification notes from 2026-10-28 reported 38 tests passed, six infrastructure-gated tests skipped, and 69% coverage. Those are historical notes, not a fresh local run in this session.
- A static source search for common private-key, GitHub token, AWS access-key, and live Stripe-key markers returned no matches. This is not equivalent to GitHub's private secret-scanning alerts or a full credential audit.

## Free-only completion status

- [x] Standard CI code checks and migration tests pass.
- [x] Docker Compose health smoke test passes.
- [x] Automated end-to-end Compose smoke verifies registration/login, monitor creation, worker check persistence, and public status.
- [x] README, profile README, and release checklist explain the free-only scope.
- [x] Paid Render blueprint removed; historical deployment notes clearly say deployment is out of scope.
- [x] External proxy integration limitations clearly documented.
- [x] Run the complete demo locally with Docker Compose, including worker-backed check persistence (2026-10-29; isolated project and preserved existing resources).
- [x] Review GitHub Secret scanning → Alerts in the UI (screenshot dated 2026-10-29 shows 0 open and 0 closed alerts).
- [x] Verify GitHub push protection is enabled (user-provided Advanced Security screenshot dated 2026-10-29 shows Secret Protection / Push protection **On**).

## Production-only work — intentionally out of scope

Production use would require a private controlled egress proxy that independently validates destination IPs at connection time, controlled public/private/DNS-rebinding/redirect/invalid-TLS fixtures, a successful real proxy integration run, deployment and database continuity planning, and further production-focused verification. None of that is claimed complete, and no paid service should be created for this portfolio goal.


## Local Docker Compose verification (2026-10-29)

A local run was performed after Docker Desktop's Linux engine became available. The audit used a separate Compose project name, a temporary host-port override (API on port 8001), and an isolated named volume. Existing stacks and their volumes were preserved.

| Check | Result |
|---|---|
| Docker Engine / Compose | 29.9.2 / 5.6.1 |
| Compose config validation | **PASS** |
| API and worker image build | **PASS** |
| PostgreSQL and Redis health | **PASS** |
| API readiness | **PASS** — HTTP 200 |
| Registration | **PASS** — HTTP 201 |
| Login | **PASS** — HTTP 200 |
| Monitor creation | **PASS** — HTTP 201 |
| Worker processed check | **PASS** |
| Persisted result | **PASS** — `is_up=True`, HTTP status 200 |
| Public status | **PASS** — HTTP 200, status `up`, `last_check` populated |
| Regression suite | **PASS** — 23 passed, 6 skipped |
| Ruff lint / format, mypy, diff check | **PASS** |

The temporary audit containers and network were stopped with `docker compose down --remove-orphans`; the audit named volume was intentionally retained. Pre-existing containers remained running. No production resources were touched and no application code fix was required.

Skipped tests remain explicit: five controlled proxy integration tests require fixture URLs/credentials, and one PostgreSQL concurrency test requires `POSTGRES_TEST_URL`. These skips are not counted as passes.

## GitHub secret-scanning alert review (2026-10-29)

The user-provided screenshot of the repository's **Secret scanning alerts** page showed **0 Open**, **0 Closed**, and “No secrets found.” A separate user-provided Advanced Security settings screenshot dated 2026-10-29 shows **Secret Protection → Push protection: On**. These screenshots verify the visible settings at capture time; they do not prove that no secret was ever present or that GitHub detects every possible secret.


## Local controlled-proxy supplemental checks (2026-10-29)

The local audit ran the repository's actual authenticated proxy implementation (proxy/proxy.py) on loopback with disposable test credentials. No public proxy was created or used.

| Direct proxy check | Result |
|---|---|
| Loopback destination 127.0.0.1 | **PASS** — HTTP 403 |
| RFC1918 private destination 10.0.0.1 | **PASS** — HTTP 403 |
| Link-local / metadata destination 169.254.169.254 | **PASS** — HTTP 403 |
| IPv4-mapped IPv6 loopback | **PASS** — HTTP 403 using a direct proxy-protocol request |
| Valid public HTTPS to https://example.com/ | **PASS** — HTTP 200 |
| Invalid proxy credentials | **PASS** — HTTP 407 |

These are supplemental direct checks, not a substitute for the formal fixture-backed integration suite. The formal suite tests/test_egress_proxy_integration.py remains **5 skipped** because dedicated fixture endpoints are absent. DNS rebinding (controlled public-then-private resolution), unsafe redirect behavior against the fixture, and invalid upstream TLS fixture behavior therefore remain **unverified**. Do not claim full egress-proxy security verification.

The local audit reported the following from the repository worktree: full pytest **38 passed, 6 skipped**; proxy/security selection **30 passed, 5 skipped**; Ruff lint, Ruff format check, mypy, and git diff --check all passed. The 6 infrastructure-gated skips and 5 proxy fixture skips are not counted as passes.

## Push protection setting

The user's screenshot of GitHub Settings → Advanced Security dated 2026-10-29 shows **Secret Protection → Push protection: On**. This closes the earlier verification gap for the visible repository setting. Secret scanning alerts showed 0 open and 0 closed alerts in the separate screenshot. Neither observation guarantees that all possible secrets will be detected.

## Final assessment

**Portfolio project with a passing automated CI and end-to-end Compose baseline; not represented as production-ready.** Remaining manual/security checks are explicitly identified rather than silently marked complete.
