# Uptime Sentinel release checklist

## Current decision

**PUBLISHED FOR REVIEW / NOT READY FOR PRODUCTION.** Branch `integration/sentry-doppler` is pushed and PR #4 is open against `main`. The real egress-proxy security gate and deployed API/worker end-to-end checks remain blocked.

## Implemented and verified by standard CI

- [x] FastAPI API, authentication, ownership-scoped monitor operations, and health endpoints.
- [x] PostgreSQL-compatible Alembic migrations through `0003_lease_tokens`.
- [x] Database-backed scheduler claims with lease tokens and conditional completion.
- [x] Application-side SSRF validation, redirect disabling, and bounded response streaming.
- [x] Production configuration validation for PostgreSQL, strong JWT secret, and `EGRESS_PROXY_URL`.
- [x] Ruff lint/format, mypy, pytest, compilation, dependency audit, PostgreSQL concurrency/fencing test, and migration round trips in CI.
- [x] Docker Compose build/start and API liveness smoke test in CI.
- [x] Render blueprint defining an API service and a true continuous background worker.
- [x] Render deployment runbook and explicit release blockers.

## Must be completed before production

- [ ] Deploy an isolated private egress proxy that validates the actual destination IP at connection time and enforces safe DNS, IPv4/IPv6, redirect, metadata, and TLS policy.
- [ ] Configure deterministic controlled fixtures and repository Actions secrets: `EGRESS_PROXY_TEST_URL`, `EGRESS_PUBLIC_URL`, `EGRESS_PRIVATE_URL`, `EGRESS_REBIND_URL`, `EGRESS_REDIRECT_URL`, `EGRESS_BAD_TLS_URL`.
- [ ] Manually dispatch CI and verify `proxy-integration` executes and passes. A skipped job is not a pass.
- [ ] Validate/deploy `render.yaml` in the dedicated Uptime Sentinel Render workspace after proxy setup; reuse the existing PostgreSQL database.
- [ ] Securely configure `DATABASE_URL`, a unique random `JWT_SECRET` (at least 32 characters), and `EGRESS_PROXY_URL` for API and worker.
- [ ] Apply migrations once through a controlled release step.
- [ ] Verify API liveness/readiness and review API/worker logs for errors and secret leakage.
- [ ] Execute disposable end-to-end checks for account registration, monitor creation, worker execution, check/result/incident persistence, recovery after restart, and cleanup.
- [ ] Resolve the existing database's Free-plan expiry (recorded as 2026-11-26) before production continuity depends on it.
- [ ] Update the verification report with actual proxy test results, workflow run ID, deployed service IDs/URLs, migration result, and end-to-end observations.

## Latest CI evidence

- [Run #62 / 40629653385](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40629653385), commit `ee553fea243b544bc15a54dd416c4ea30f1ce14f`: `checks` PASS; `compose-smoke` PASS; `proxy-integration` SKIPPED because controlled fixture secrets are missing.
- Latest local verification: 23 tests passed, 6 infrastructure-gated tests skipped; Ruff, mypy (21 files), compileall, pip check, pip-audit, and SQLite migration round trip passed.
- No Render API or worker deployment has been verified.

Do not mark production ready until every unchecked security and deployment gate is genuinely verified.
