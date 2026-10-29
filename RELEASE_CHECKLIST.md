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

- [x] Verify [PR CI run #293](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40906489226): `checks`, `compose-smoke`, `proxy-local-integration`, and `codecov/patch` passed. The optional external proxy job was skipped because controlled fixtures are not configured.
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

PR #12 was merged into `main` on 2026-10-29 as commit `aa7fc8e64a5f9f3a7cdb5a8a74313e9e26ea23ce`. [PR CI run #293](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40906489226) passed `checks`, `compose-smoke`, `proxy-local-integration`, and `codecov/patch`. The external proxy job remains skipped because controlled fixtures are not configured.

- [x] Shared manual/scheduled lease protocol, persisted-result fencing, wall-clock request deadline, PATCH explicit-null 422 validation.
- [x] PostgreSQL guard for one open incident per monitor; regression test for concurrent failure transitions.
- [x] Concurrency-safe monitor quota check and stable bounded incident/check pagination.
- [x] Slow-stream timeout regression, full test suite, PostgreSQL concurrency, formatting/type/lint, dependency audit, and PostgreSQL/SQLite migration round-trips passed in run #285. The final local suite reported 60 passed and 8 skipped.
- [ ] External controlled-proxy integration: **not run** because controlled fixture endpoints/secrets have not been configured.
- [x] Shared rate-limit backend is configurable via `RATE_LIMIT_STORAGE_URI`; default `memory://` is single-process only. Set a protected Redis URL before running multiple API replicas.\n- [x] Added `/metrics` Prometheus text endpoint for overdue checks, expired leases, open incidents, and retained failed-check history. Scheduler errors remain structured logs, not a durable counter.\n- [x] Bounded proxy concurrent sessions with `PROXY_MAX_CONNECTIONS` (default 128), overload 503/Retry-After response, and a bounded listen backlog.
- [x] PR #12 merged into `main` as `aa7fc8e64a5f9f3a7cdb5a8a74313e9e26ea23ce`.
- [ ] Release tag: **not created**.

## Latest verified evidence and remaining work

- The final PR validation is [run #293](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40906489226). `checks`, `compose-smoke`, `proxy-local-integration`, and `codecov/patch` passed. The optional external `proxy-integration` job was skipped because external controlled fixture URLs/configuration were not available.
- Proxy fail-closed authentication regression was merged in [PR #6](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/6).
- A free Render test proxy exists at https://uptime-sentinel-egress-proxy.onrender.com, but its inbound allowlist is `0.0.0.0/0`; it is a test service, not a production security boundary.
- The Render PostgreSQL free instance has a recorded expiry of 2026-11-26. This does not affect local Docker Compose or GitHub-only portfolio completion; do not depend on it for persistent production data.
- The API and continuous worker are not deployed in Render. That is intentional for the free-only portfolio scope.
- PR CI run #293 passed `checks`, `compose-smoke`, `proxy-local-integration`, and `codecov/patch`. External proxy integration remains unverified; it requires an independently operated controlled proxy and fixtures. The PR was merged to `main` as `aa7fc8e64a5f9f3a7cdb5a8a74313e9e26ea23ce`.

No paid resources are required for the project goal. Do not label this deployment production-ready; it is a portfolio project with local demo and CI verification.
