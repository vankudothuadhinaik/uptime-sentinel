# Uptime Sentinel project checklist

## Chosen scope

**Goal: a polished, working GitHub portfolio project using free tools only.** Deliverables are source code, automated CI, deterministic local security tests, a Docker Compose demo, and accurate documentation. Paid hosting, production uptime guarantees, and independently operated external proxy infrastructure are optional and out of scope.

## Implementation

- [x] FastAPI uptime-monitoring API with authentication and ownership-scoped monitor operations.
- [x] PostgreSQL-compatible Alembic migrations.
- [x] Database-backed scheduler/worker with leases and fencing.
- [x] Bounded HTTP checks, result history, incident lifecycle, and public read-only status.
- [x] Application SSRF-oriented URL/address validation, redirect disabling, and response-size bounds.
- [x] Egress proxy authentication fails closed when credentials are absent.
- [x] Proxy destination-policy, redirect, resolver pinning, TLS, overload, and malformed/unsupported request regression coverage.
- [x] Prometheus operational gauges and bounded proxy concurrency/overload handling.
- [x] Dockerfiles, Docker Compose demo, README, runbook, verification report, CI workflow, and portfolio demo/interview walkthrough.
- [x] Production-oriented Compose profile with Caddy TLS edge, private data network, authenticated Redis, persistent volumes, container hardening, and public docs/metrics blocking.
- [x] Production deployment runbook and environment template; configuration validator rejects common placeholder credentials.

## Final verification — 2026-10-30

- [x] PR #14 merged into `main`: [PR #14](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/14), merge commit `0ae9c20f0e6dc7c946fb968a1dff6b8e5a49ef42`.
- [x] Latest full main CI passed: [run #375](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40945979277), commit `2016301838f0a4a92a0808994e163c13281df770`; checks, local proxy integration, Compose smoke, and production Compose validation passed.
- [x] Earlier run [#374](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40945479831) failed at type checking and was superseded by the successful #375 run. The older run #372 was cancelled; it is not a pending gate.
- [x] Main CI checks passed.
- [x] Controlled local proxy security integration passed.
- [x] Docker Compose smoke passed.
- [x] Repository docs updated to reflect the current merge and CI state; stale queued-run references removed.
- [x] No paid Render resources were created for this portfolio scope.
- [ ] External controlled-proxy security suite: **not run**; intentionally optional for the free portfolio scope and required before claiming production proxy security.
- [ ] Production deployment: **not performed**; outside the selected free-only scope.

## Remaining production release gates

The production configuration is merged, but **a public production deployment is not complete or certified**. Do not call it production-ready until these gates are completed:

- [ ] Provision a private controlled proxy and host-level egress firewall; the existing Render proxy allows public ingress and is not approved for production.
- [ ] Decide where to host the API and continuously running worker. Free tiers may sleep or restrict background services; do not claim 24/7 monitoring without verifying always-on behavior.
- [ ] Configure real domain/DNS and unique production secrets outside Git, then deploy and verify health, scheduled checks, incident recovery, and backups.

## External security and hosting work

- [ ] Provision a private, access-controlled proxy that enforces destination IP policy at connection time.
- [ ] Operate controlled public HTTPS, private destination, DNS-rebinding, redirect, and invalid-TLS fixtures.
- [ ] Configure GitHub Actions secrets `EGRESS_PROXY_TEST_URL`, `EGRESS_PUBLIC_URL`, `EGRESS_PRIVATE_URL`, `EGRESS_REBIND_URL`, `EGRESS_REDIRECT_URL`, and `EGRESS_BAD_TLS_URL`; manually dispatch CI with `run_external_proxy_tests` enabled and inspect proxy logs.
- [ ] Review and approve hosting cost before provisioning production API and genuine continuous worker services.
- [ ] Supply production secrets securely, run migrations once, and verify deployed API health, worker processing, persistence, recovery, and cleanup.
- [ ] Plan database continuity before the current Free Render PostgreSQL instance's recorded expiry, `2026-11-26T21:40:41Z`.

## Honest release statement

The **free-only portfolio project is implemented and its standard CI passed**. The external proxy integration job was skipped, so external/production egress security is not certified. The existing Render proxy is a test service with public ingress allowed; do not use it for sensitive or production traffic. A green CI run is not a claim of production readiness.
