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
- [x] CI workflow for lint, formatting, typing, tests, dependency audit, migrations, and Docker Compose smoke test.
- [x] README, architecture/lifecycle diagrams, local setup, and this scope-aware checklist.

## Free-only completion gates

- [x] Verify the latest GitHub Actions run on `main` completes successfully: [run #187](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40831202247) passed `checks` and `compose-smoke`, including the new registration-to-worker end-to-end smoke.
- [ ] Run the documented app manually on a developer machine with Docker Compose. CI now automates readiness, registration/login, monitor creation, worker check persistence, and public status, but a local manual run has not been performed from this session.
- [x] Search indexed source for common private-key, GitHub-token, AWS-key, and live Stripe-key markers; no matches were returned. This static search is not a substitute for GitHub secret-scanning alerts or rotating any credential that may have been exposed.
- [ ] Review GitHub's repository security/secret-scanning alerts in the GitHub UI; that private security-alert view was not available through the connected tools.
- [x] Clearly document that external proxy integration tests are opt-in and require controlled fixture URLs/secrets; the latest run skipped this job, so it is not counted as passed.
- [x] Keep the Render public test proxy out of production use. It allows public ingress and has not completed independent live security verification; it is explicitly marked as test-only in the docs.
- [x] Keep instructions for local development aligned with the free-only scope; no paid hosting is required to clone, test, or demonstrate the project.

## Optional, explicitly out of scope

- Paid Render API/background-worker hosting.
- Production database upgrades, paid backups, high availability, and production SLOs.
- External proxy fixture infrastructure and live internet security testing requiring controlled hosts and repository secrets.
- Public production deployment and production readiness claims.

## Latest verified evidence and remaining work

- Latest completed end-to-end CI baseline [#187](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40831202247) on commit `e17788aefba0d76d980f4b304432306650db75c1`: `checks` and `compose-smoke` passed, including registration/login, monitor creation, worker check persistence, and public status. `proxy-integration` was skipped because controlled fixture URLs/secrets were not configured.
- Proxy fail-closed authentication regression was merged in [PR #6](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/6).
- A free Render test proxy exists at https://uptime-sentinel-egress-proxy.onrender.com, but its inbound allowlist is `0.0.0.0/0`; it is a test service, not a production security boundary.
- The Render PostgreSQL free instance has a recorded expiry of 2026-11-26. This does not affect local Docker Compose or GitHub-only portfolio completion; do not depend on it for persistent production data.
- The API and continuous worker are not deployed in Render. That is intentional for the free-only portfolio scope.
- CI status above was checked on 2026-10-29. Run #179 passed `checks` and `compose-smoke`; `proxy-integration` was skipped. Future runs still in progress are not passes.

No paid resources are required for the project goal. Do not label this deployment production-ready; it is a portfolio project with local demo and CI verification.
