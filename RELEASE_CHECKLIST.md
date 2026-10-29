# Uptime Sentinel project checklist

## Project scope

**Goal: a polished, working GitHub portfolio project using free tools only.** Paid hosting and production uptime guarantees are explicitly out of scope. The main deliverable is the source code, automated CI, Docker Compose demo, documentation, and honest security limitations.

## Implemented

- [x] FastAPI uptime-monitoring API with authentication and ownership-scoped monitor operations.
- [x] PostgreSQL-compatible Alembic migrations.
- [x] Database-backed scheduler with leases and fencing to reduce duplicate/stale worker work.
- [x] Bounded HTTP checks, latency/failure history, and incident open/update/recovery lifecycle.
- [x] Application SSRF validation, redirect disabling, and response-size bounds.
- [x] Production configuration validation for database, JWT, and controlled egress proxy credentials.
- [x] Egress proxy authentication fails closed when credentials are absent, with regression coverage merged in [PR #6](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/6).
- [x] CI workflow for lint, formatting, typing, tests, dependency audit, migrations, Docker Compose smoke test, and required controlled local proxy security integration tests.
- [x] README, architecture/lifecycle diagrams, local setup, and this scope-aware checklist.

## Free-only completion gates

- [x] Verify [PR #14 CI run #325](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40924701371): required jobs passed for parent commit `4adefa5`; the external proxy job was skipped because controlled fixtures are not configured.
- [x] Run the documented app locally with Docker Compose. On 2026-10-29 an isolated stack built and became healthy; registration, login, monitor creation, worker processing, persisted HTTP 200 check, and public status all passed. Existing stacks/volumes were preserved.
- [x] Search indexed source for common private-key, GitHub-token, AWS-key, and live Stripe-key markers; no matches were returned. This static search is not a substitute for GitHub secret-scanning alerts or rotating any credential that may have been exposed.
- [x] Review GitHub Secret scanning → Alerts in the UI. The user's screenshot dated 2026-10-29 showed 0 open and 0 closed alerts and “No secrets found.” A separate Advanced Security screenshot dated 2026-10-29 showed Secret Protection → Push protection **On**.
- [x] Make controlled local proxy security regressions required in ordinary CI; run #285 passed the deterministic local proxy security job covering address policy, DNS resolution/mixed answers, resolver pinning, redirects, authentication, unsupported requests, and TLS verification.
- [x] Clearly document that the separate external proxy integration remains opt-in and requires independently controlled fixture URLs/secrets; its skip is not counted as a pass for an external or production proxy.
- [x] Keep the Render public test proxy out of production use. It allows public ingress and has not completed independent live security verification; it is explicitly marked as test-only in the docs.
- [x] Keep instructions for local development aligned with the free-only scope; no paid hosting is required to clone, test, or demonstrate the project.

The external proxy workflow is now an explicit opt-in on manual dispatch (`run_external_proxy_tests`). The six `EGRESS_*` values are fixture URLs/configuration, not passwords; only set them when you control the proxy and fixtures. Normal CI requires no such values and runs the local proxy security suite.

## Optional, explicitly out of scope

- Paid Render API/background-worker hosting.
- Production database upgrades, paid backups, high availability, and production SLOs.
- External proxy fixture infrastructure and live internet security testing requiring controlled hosts and repository secrets.
- Public production deployment and production readiness claims.

## Active PR hardening status — 2026-10-29

PR #14 is open from `hardening/ops-metrics-proxy-limits-recovery` at commit `273dba7`. CI run #325 passed for parent commit `4adefa5`; the external proxy job remains blocked without controlled fixtures. CI for `273dba7` is pending.

- [x] Shared manual/scheduled lease protocol, persisted-result fencing, wall-clock request deadline, PATCH explicit-null 422 validation.
- [x] PostgreSQL guard for one open incident per monitor; regression test for concurrent failure transitions.
- [x] Concurrency-safe monitor quota check and stable bounded incident/check pagination.
- [x] Local final suite: 72 passed, 8 skipped, 3 warnings; Ruff, formatting, configured mypy, compileall, pip check, pip-audit, and diff check passed.
- [x] Docker PostgreSQL 16 migrations and real two-session concurrency/fencing tests passed (2 tests).
- [x] Docker Compose smoke passed, including API migrations/readiness, authentication, worker persistence, and public status.
- [ ] External controlled-proxy integration: **not run** because controlled fixture endpoints/secrets have not been configured.
- [x] Shared rate-limit backend is configurable via `RATE_LIMIT_STORAGE_URI`; default `memory://` is single-process only. Set a protected Redis URL before running multiple API replicas.
- [x] Added `/metrics` Prometheus text endpoint with current-state gauges for overdue checks, expired leases, open incidents, and retained failed-check history. Scheduler errors remain structured logs, not a durable counter.
- [x] Bounded proxy concurrent sessions with `PROXY_MAX_CONNECTIONS` (default 128), overload 503/Retry-After response, and a bounded listen backlog.
- [ ] PR #14 merge: intentionally not performed.
- [ ] Release tag: **not created**.

## Latest verified evidence and remaining work

- The final completed PR validation is run #325 for `4adefa5`; required jobs passed. The latest `273dba7` push still requires a completed workflow. The external `proxy-integration` job is blocked because external controlled fixture URLs/configuration are unavailable.
- Proxy fail-closed authentication regression was merged in [PR #6](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/6).
- A free Render test proxy exists at https://uptime-sentinel-egress-proxy.onrender.com, but its inbound allowlist is `0.0.0.0/0`; it is a test service, not a production security boundary.
- The Render PostgreSQL free instance has a recorded expiry of 2026-11-26. This does not affect local Docker Compose or GitHub-only portfolio completion; do not depend on it for persistent production data.
- The API and continuous worker are not deployed in Render. That is intentional for the free-only portfolio scope.
- PR #14 remains unmerged. External proxy integration remains unverified; it requires an independently operated controlled proxy and fixtures. Do not label the project production-ready.

No paid resources are required for the project goal. Do not label this deployment production-ready; it is a portfolio project with local demo and CI verification.
