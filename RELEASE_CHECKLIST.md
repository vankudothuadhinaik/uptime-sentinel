# Uptime Sentinel release checklist

## Current decision

**NOT READY FOR PRODUCTION.** The fail-closed proxy authentication fix is merged into `main` (PR [#6](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/6)). Standard CI and Compose smoke tests passed in [run #40697076205](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40697076205). The controlled proxy is live at https://uptime-sentinel-egress-proxy.onrender.com, but it still allows ingress from `0.0.0.0/0`; live authenticated/unauthenticated requests and controlled security fixtures have not been independently verified. The API and continuous worker are not deployed.

## Implemented and verified by standard CI

- [x] FastAPI API, authentication, ownership-scoped monitor operations, and health endpoints.
- [x] PostgreSQL-compatible Alembic migrations through `0003_lease_tokens`.
- [x] Database-backed scheduler claims with lease tokens and conditional completion.
- [x] Application-side SSRF validation, redirect disabling, and bounded response streaming.
- [x] Production configuration validation for PostgreSQL, strong JWT secret, controlled egress proxy URL, and proxy credentials.
- [x] Proxy authentication fails closed if username or password is missing/empty; regression coverage is merged.
- [x] Proxy rejects non-public destination IP ranges and pins sockets to validated DNS answers.
- [x] Ruff lint/format, mypy, pytest, compilation, dependency audit, PostgreSQL concurrency/fencing test, and migration round trips in standard CI.
- [x] Docker Compose build/start and API liveness smoke test in CI.
- [x] Render blueprint defines an API service and a genuine continuous background worker.
- [x] Render deployment runbook and explicit release blockers.

## Remaining production blockers

### Proxy security and integration

- [ ] Restrict proxy ingress using a supported private-network/ingress control before production. Current allowlist is `0.0.0.0/0`; authentication is an additional control, not a substitute for network isolation.
- [ ] Independently verify a valid authenticated proxy request succeeds and missing/invalid credentials receive HTTP 407. Do not expose or print the credentials in logs or reports.
- [ ] Deploy controlled test fixtures and prove private destinations and DNS-rebinding destinations receive explicit HTTP 403 responses. Also test public HTTPS, redirect non-following, and invalid TLS rejection.
- [ ] Configure and verify the six GitHub Actions repository secrets only after the fixtures are deployed and validated: `EGRESS_PROXY_TEST_URL`, `EGRESS_PUBLIC_URL`, `EGRESS_PRIVATE_URL`, `EGRESS_REBIND_URL`, `EGRESS_REDIRECT_URL`, `EGRESS_BAD_TLS_URL`.
- [ ] Manually dispatch CI and verify `proxy-integration` executes and passes. A skipped job is not a pass.

### Deployment and database continuity

- [ ] Deploy `render.yaml` in the dedicated Uptime Sentinel Render workspace, reusing the existing PostgreSQL database. The connected Render API tool does not expose a blueprint-deploy or background-worker-create action; use Render's supported Blueprint workflow rather than substituting a cron job or public web service for a continuous worker.
- [ ] Securely configure `DATABASE_URL`, unique random `JWT_SECRET` (at least 32 characters), `EGRESS_PROXY_URL`, `EGRESS_PROXY_USERNAME`, and `EGRESS_PROXY_PASSWORD` for both API and worker.
- [ ] Apply migrations once through a controlled release step.
- [ ] Verify API liveness/readiness and inspect API/worker logs for errors and accidental secret leakage.
- [ ] Resolve the existing PostgreSQL Free-plan expiry recorded as **2026-11-26**. Review the cost and backup/restore options before any paid upgrade; test a restore before production reliance.
- [ ] Configure monitoring/alerts, document rollback, and establish a tested recovery procedure.

### End-to-end verification

- [ ] Execute disposable end-to-end checks for account registration/login, monitor creation, worker execution, check/result/incident persistence, incident recovery, restart/lease recovery, and retention cleanup.
- [ ] Verify actual alert delivery if alerting is configured.
- [ ] Update this checklist with real test evidence, workflow run ID, deployed service IDs/URLs, migration result, and end-to-end observations.

## Latest verified evidence

- Standard CI run [#40697076205](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40697076205): `checks` and `compose-smoke` passed; `proxy-integration` was skipped because it is opt-in and controlled fixtures/secrets are not configured.
- Render proxy service: `srv-dbguqv6tlv9c73den9t0`, URL https://uptime-sentinel-egress-proxy.onrender.com. Latest observed live deployment: `dep-dbgvhljbc2fs73bnct00`, commit `e7f5c547a034c051cc4d35afbefc23b93a78dc86`. Render reports ingress allowlist `0.0.0.0/0`.
- Render Postgres: `dpg-dbghkmc9v7es73dns2ig-a`, status available, Free plan, Singapore, expiry `2026-11-26T21:40:41.74375Z`. External query access is not configured (empty IP allowlist).
- Render currently lists no API or continuous worker service.
- A direct HTTP check from the available execution container could not run because that environment could not resolve external DNS; no live proxy behavior is claimed as tested here.

Do not mark production ready until every unchecked security, continuity, and deployment gate is genuinely verified.
