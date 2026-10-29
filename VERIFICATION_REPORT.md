# Uptime Sentinel verification report

Run date: 2026-10-29

## Active P0 hardening PR — 2026-10-29

PR #12: https://github.com/vankudothuadhinaik/uptime-sentinel/pull/12

The current PR branch hardens manual/scheduled check deduplication, whole-request timeout including slow response streams, PATCH null validation, lease/result persistence fencing, incident uniqueness/concurrency, quota serialization, and bounded stable pagination. [CI run #283](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40892273614) for commit `cc170dc97f9afe0a68d85a5fd8399d2f5c9bc878` passed the required `checks`, `compose-smoke`, and `proxy-local-integration` jobs.

The external `proxy-integration` job was skipped because external controlled fixture URLs/secrets are not configured. That skip is not a security pass. PR #12 remains open and no release tag was created.

## Project decision

**Portfolio scope: free GitHub repository, CI, and local Docker Compose demo.** Paid hosting and production uptime guarantees are out of scope. This report distinguishes automated evidence from checks that have not been run.

## Latest completed end-to-end CI evidence

[PR #12 run #283](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40892273614) completed successfully on 2026-10-29 for commit `cc170dc97f9afe0a68d85a5fd8399d2f5c9bc878`.

| Job | Result | What it establishes |
|---|---|---|
| `checks` | **PASS** | Dependency consistency, Ruff lint/format, mypy, PostgreSQL concurrency tests, pytest/coverage, Codecov upload, compileall, dependency audit, and PostgreSQL/SQLite migration checks passed. |
| `compose-smoke` | **PASS** | Compose configuration validation, container build/start, API liveness, registration/login, monitor creation, worker check persistence, and public status all passed. |
| `proxy-local-integration` | **PASS** | Deterministic local proxy security tests passed. |
| `proxy-integration` | **SKIPPED** | Controlled proxy fixture URLs/secrets are not configured. This is not a security pass. |

Run #283 is the latest successful PR validation. The external proxy job remains skipped.

The final PR branch adds deterministic proxy request-validation and cleanup regression coverage. Its checks job passed the full suite, PostgreSQL concurrency test, migrations, dependency audit, compilation, and formatting/type checks. Its Compose job passed the registration-to-worker E2E flow. The external proxy job remained skipped because the six controlled fixture secrets are not configured.

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

- CI run [#283](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40892273614) on PR #12 completed successfully on 2026-10-29. `checks`, `compose-smoke`, and `proxy-local-integration` passed; the separate opt-in `proxy-integration` job was skipped because external controlled fixture URLs/secrets were not configured.
- A separate local Docker Compose run was completed on 2026-10-29 using an isolated Compose project (`uptime-sentinel-audit`); the real registration-to-worker E2E flow passed. See **Local Docker Compose verification (2026-10-29)** below.
- The external controlled-proxy integration job is an explicit opt-in on manual workflow dispatch (`run_external_proxy_tests`) and remains unverified until independently operated fixture URLs/configuration are supplied. These six values are not passwords and cannot be safely invented. Do not treat a skip as a pass or as evidence about an external/production proxy. The repository's controlled local proxy suite is required in CI and passed in run #283.
- The old public test proxy has not passed the controlled security suite and must not be used for sensitive or production traffic.
- The final local run on the PR branch reported **60 passed, 8 skipped**, and two existing SlowAPI deprecation warnings. The skips are the five opt-in external proxy tests, the PostgreSQL concurrency tests without a local `POSTGRES_TEST_URL`, and the local invalid-TLS fixture when certificate tooling is unavailable.
- A static source search for common private-key, GitHub token, AWS access-key, and live Stripe-key markers returned no matches. This is not equivalent to GitHub's private secret-scanning alerts or a full credential audit.

## Free-only completion status

- [x] Standard CI code checks and migration tests pass.
- [x] Docker Compose health smoke test passes.
- [x] Automated end-to-end Compose smoke verifies registration/login, monitor creation, worker check persistence, and public status.
- [x] README, profile README, and release checklist explain the free-only scope.
- [x] Paid Render blueprint removed; historical deployment notes clearly say deployment is out of scope.
- [x] External proxy integration limitations clearly documented.
- [x] Run the complete demo locally with Docker Compose, including worker-backed check persistence (2026-10-29; isolated project and preserved existing resources).
- [x] Review GitHub Secret scanning → Alerts in the GitHub UI (user-provided screenshot dated 2026-10-29 shows 0 open and 0 closed alerts); a separate Advanced Security screenshot dated 2026-10-29 shows Push Protection On.
- [x] Run deterministic local proxy regressions in CI for mixed DNS answers, DNS failures, request authentication, unsupported methods/ports, target credentials, resolver pinning, unsafe redirects, and TLS verification. PR #12 run #283's `proxy-local-integration` job passed. These verify the repository's proxy implementation and deterministic fixtures, not an independently operated external proxy.

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
| Regression suite | **PASS** — 60 passed, 8 skipped locally |
| Ruff lint / format, mypy, diff check | **PASS** |

The temporary audit containers and network were stopped with `docker compose down --remove-orphans`; the audit named volume was intentionally retained. Pre-existing containers remained running. No production resources were touched and no application code fix was required.

Skipped tests remain explicit: five controlled proxy integration tests require fixture URLs/credentials, and one PostgreSQL concurrency test requires `POSTGRES_TEST_URL`. These skips are not counted as passes.

## GitHub secret-scanning alert review (2026-10-29)

The user-provided screenshot of the repository's **Secret scanning alerts** page showed **0 Open**, **0 Closed**, and “No secrets found.” A separate Advanced Security screenshot dated 2026-10-29 showed **Push protection On**. These screenshots verify the displayed settings at that time; they do not prove that no secret was ever present or that GitHub detects every possible secret.

## Final assessment

**Portfolio project with passing automated CI, end-to-end Compose smoke, and required local proxy security regression tests; not represented as production-ready.** CI run #283 passed `checks`, `compose-smoke`, and `proxy-local-integration`. The separate external controlled-proxy integration suite remains unverified because its dedicated fixture secrets are not configured. Local fixtures validate the repository's proxy behavior but do not certify an independently operated production proxy. No production deployment is claimed.
