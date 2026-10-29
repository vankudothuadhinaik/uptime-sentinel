# Uptime Sentinel release checklist

## Current decision

**NOT READY FOR PRODUCTION.** PR #4 was merged into `main`; the current verified head is commit `49907457ebd976229e47a126dd5922ff56c5d9ab`. A free Render test proxy is live at `https://uptime-sentinel-egress-proxy.onrender.com`, but it is internet-reachable and its credentials/protocol/security fixtures are not independently verified. The API and continuous worker are not deployed.

## Implemented and verified by standard CI

- [x] FastAPI API, authentication, ownership-scoped monitor operations, and health endpoints.
- [x] PostgreSQL-compatible Alembic migrations through `0003_lease_tokens`.
- [x] Database-backed scheduler claims with lease tokens and conditional completion.
- [x] Application-side SSRF validation, redirect disabling, and bounded response streaming.
- [x] Production configuration validation for PostgreSQL, strong JWT secret, and `EGRESS_PROXY_URL`.
- [x] Add production validation and client support for `EGRESS_PROXY_USERNAME` and `EGRESS_PROXY_PASSWORD`.
- [x] Ruff lint/format, mypy, pytest, compilation, dependency audit, PostgreSQL concurrency/fencing test, and migration round trips in CI.
- [x] Docker Compose build/start and API liveness smoke test in CI.
- [x] Render blueprint defining an API service and a true continuous background worker.
- [x] Render deployment runbook and explicit release blockers.

## Must be completed before production

- [ ] Configure strong `PROXY_USERNAME` and `PROXY_PASSWORD` in Render for the test proxy; confirm its process starts and authenticated proxy requests work.
- [ ] Restrict proxy exposure using a supported private network/ingress control before production. The current Render test service permits internet ingress and is not production-approved.
- [ ] Deploy/verify controlled fixtures and prove the proxy rejects private destinations and DNS rebinding with explicit HTTP 403 responses; test redirects and invalid TLS behavior.
- [ ] Configure deterministic controlled fixtures and repository Actions secrets: `EGRESS_PROXY_TEST_URL`, `EGRESS_PUBLIC_URL`, `EGRESS_PRIVATE_URL`, `EGRESS_REBIND_URL`, `EGRESS_REDIRECT_URL`, `EGRESS_BAD_TLS_URL`.
- [ ] Manually dispatch CI and verify `proxy-integration` executes and passes. A skipped job is not a pass.
- [ ] Validate/deploy `render.yaml` in the dedicated Uptime Sentinel Render workspace after proxy setup; reuse the existing PostgreSQL database.
- [ ] Securely configure `DATABASE_URL`, a unique random `JWT_SECRET` (at least 32 characters), `EGRESS_PROXY_URL`, `EGRESS_PROXY_USERNAME`, and `EGRESS_PROXY_PASSWORD` for both API and worker.
- [ ] Apply migrations once through a controlled release step.
- [ ] Verify API liveness/readiness and review API/worker logs for errors and secret leakage.
- [ ] Execute disposable end-to-end checks for account registration, monitor creation, worker execution, check/result/incident persistence, recovery after restart, and cleanup.
- [ ] Resolve the existing database's Free-plan expiry (recorded as 2026-11-26) before production continuity depends on it.
- [ ] Update the verification report with actual proxy test results, workflow run ID, deployed service IDs/URLs, migration result, and end-to-end observations.

## Latest CI evidence

- [Run #161 / 40695272332](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40695272332), commit `49907457ebd976229e47a126dd5922ff56c5d9ab`: `checks` and `compose-smoke` passed. `proxy-integration` was skipped because the six controlled fixture secrets are not configured. A skipped proxy job is not a security pass.
- The current `main` head is the merged result of PR #4. No failed or in-progress `main` run was present in the inspected workflow history.
- No Render API or continuous worker deployment has been verified.
- Local Docker Compose configuration validation passed, but image build/start and worker-backed E2E verification were blocked because the Docker daemon was unavailable.
- The existing PostgreSQL Free plan is recorded to expire on 2026-11-26; resolve continuity before relying on it for production.


Do not mark production ready until every unchecked security and deployment gate is genuinely verified.
