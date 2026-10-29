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

- [x] Verify [CI run #229](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40849371364) on PR #11: `checks`, `compose-smoke`, and the new `proxy-local-integration` job all passed; the local proxy job ran 29 tests. PR #11 is merged to main.
- [x] Run the documented app locally with Docker Compose. On 2026-10-29 an isolated stack built and became healthy; registration, login, monitor creation, worker processing, persisted HTTP 200 check, and public status all passed. Existing stacks/volumes were preserved.
- [x] Search indexed source for common private-key, GitHub-token, AWS-key, and live Stripe-key markers; no matches were returned. This static search is not a substitute for GitHub secret-scanning alerts or rotating any credential that may have been exposed.
- [x] Review GitHub Secret scanning → Alerts in the UI. The user's screenshot dated 2026-10-29 showed 0 open and 0 closed alerts and “No secrets found.” A separate Advanced Security screenshot dated 2026-10-29 showed Secret Protection → Push protection **On**.
- [x] Make controlled local proxy security regressions required in ordinary CI; run #229 passed 29 tests covering address policy, DNS resolution/mixed answers, resolver pinning, redirects, authentication, unsupported requests, and TLS verification.
- [x] Clearly document that the separate external proxy integration remains opt-in and requires independently controlled fixture URLs/secrets; its skip is not counted as a pass for an external or production proxy.
- [x] Keep the Render public test proxy out of production use. It allows public ingress and has not completed independent live security verification; it is explicitly marked as test-only in the docs.
- [x] Keep instructions for local development aligned with the free-only scope; no paid hosting is required to clone, test, or demonstrate the project.

## Optional, explicitly out of scope

- Paid Render API/background-worker hosting.
- Production database upgrades, paid backups, high availability, and production SLOs.
- External proxy fixture infrastructure and live internet security testing requiring controlled hosts and repository secrets.
- Public production deployment and production readiness claims.

## Active PR hardening status — 2026-10-29

PR #12 is open on `fix/p0-monitoring-consistency`. The current branch contains the critical correctness changes listed in the section above this checklist. Its `checks` job passed on the latest tested commit, including the full pytest suite, PostgreSQL concurrency, lint/format/type checks, dependency audit, and migration round-trips. The latest CI run is available at https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40889435122; its Compose E2E and local proxy jobs were still in progress when this update was written.

- [x] Shared manual/scheduled lease protocol, persisted-result fencing, wall-clock request deadline, PATCH explicit-null 422 validation.
- [x] PostgreSQL guard for one open incident per monitor; regression test for concurrent failure transitions.
- [x] Concurrency-safe monitor quota check and stable bounded incident/check pagination.
- [x] Slow-stream timeout regression, full test suite, PostgreSQL concurrency, formatting/type/lint, dependency audit, and PostgreSQL/SQLite migration round-trips passed in the latest successful `checks` job.
- [ ] External controlled-proxy integration: **not run** because controlled fixture endpoints/secrets have not been configured.
- [ ] PR #12 merge and release tag: **not done**.

## Latest verified evidence and remaining work

- Latest completed main-branch CI evidence is [run #233](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40849831440), after the latest documentation updates. The local proxy security tests were verified in [run #229](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40849371364), associated with merged PR #11. `checks`, `compose-smoke`, and `proxy-local-integration` passed; the local proxy job reported 29 passed tests. The optional external `proxy-integration` job was skipped because external controlled fixture URLs/secrets were not configured.
- Proxy fail-closed authentication regression was merged in [PR #6](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/6).
- A free Render test proxy exists at https://uptime-sentinel-egress-proxy.onrender.com, but its inbound allowlist is `0.0.0.0/0`; it is a test service, not a production security boundary.
- The Render PostgreSQL free instance has a recorded expiry of 2026-11-26. This does not affect local Docker Compose or GitHub-only portfolio completion; do not depend on it for persistent production data.
- The API and continuous worker are not deployed in Render. That is intentional for the free-only portfolio scope.
- CI run #233 passed after documentation updates; run #229 passed `checks`, `compose-smoke`, and `proxy-local-integration` (29 passed). Only the external proxy integration remains unverified; it requires a controlled independently operated proxy and fixtures. Use the linked Actions page for newer runs.

No paid resources are required for the project goal. Do not label this deployment production-ready; it is a portfolio project with local demo and CI verification.
