# Uptime Sentinel verification report

Run date: 2026-10-30

## Final repository verification

- PR #14, **Harden proxy limits and operational metrics**, merged into `main` as `0ae9c20f0e6dc7c946fb968a1dff6b8e5a49ef42`.
- Latest documentation commit: `c857035f783514be763d397e90610a221e54e613`.
- Latest main-branch CI: [run #346](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40934553581) — **success**.
- No release tag was created.
- Scope is the free GitHub portfolio project: code, automated CI, local proxy fixtures, Docker Compose demo, and documentation. Paid production hosting is not required.

## CI results

| Job | Result | Evidence |
|---|---|---|
| `checks` | **PASS** | Run #346 completed successfully, including lint, formatting, type checks, tests, migrations, and dependency audit. |
| `proxy-local-integration` | **PASS** | Controlled local proxy security integration tests passed. |
| `compose-smoke` | **PASS** | Docker Compose smoke test passed, including API health and service/worker exercise. |
| `proxy-integration` | **SKIPPED** | External controlled fixtures and the six fixture configuration secrets are not configured. This is not a security pass for an external proxy. |

## Implemented and verified in repository scope

- FastAPI monitoring API, authentication and ownership-scoped operations.
- PostgreSQL-compatible migrations and database-backed leased worker.
- Bounded HTTP checks, no automatic redirect following, response-size limits, SSRF-oriented URL/address checks, and incident lifecycle.
- Egress proxy authentication fail-closed behavior, destination policy tests, local fixture coverage, and TLS-verification regressions.
- Operational metrics and bounded proxy concurrency/overload behavior from merged PR #14.
- CI for lint, formatting, typing, tests, database migration checks, dependency audit, local proxy integration, and Docker Compose smoke.

## External security boundary

The opt-in external suite in `.github/workflows/ci.yml` requires an independently controlled proxy and fixture URLs for public HTTPS, private destination, DNS rebinding, redirects, and invalid TLS. The required GitHub Actions secret names are:

- `EGRESS_PROXY_TEST_URL`
- `EGRESS_PUBLIC_URL`
- `EGRESS_PRIVATE_URL`
- `EGRESS_REBIND_URL`
- `EGRESS_REDIRECT_URL`
- `EGRESS_BAD_TLS_URL`

These values must refer to infrastructure the project owner controls. They cannot be safely fabricated, and skipped tests must not be reported as passed.

## Render observation

The connected Uptime Sentinel Render workspace has:
- PostgreSQL instance `uptime-sentinel-db`, PostgreSQL 16, Free plan, reported available and with expiry `2026-11-26T21:40:41Z`.
- Test proxy service `uptime-sentinel-egress-proxy` at https://uptime-sentinel-egress-proxy.onrender.com.
- The proxy service is configured to deploy from `integration/sentry-doppler`, not `main`, and its ingress allowlist permits `0.0.0.0/0`.

The test proxy is not independently security-certified and must not be used for sensitive or production traffic. The API and continuous worker are not deployed. This is intentional for the free-only portfolio scope; the paid Render blueprint was removed. No service settings or secrets were changed in this verification.

## Final decision

**Free-only portfolio project: repository implementation and standard CI verified.**

**Production deployment/security certification: not complete and not claimed.** It requires controlled external proxy infrastructure, external fixture-backed evidence, a separately approved hosting plan, secure production configuration, migrations, and deployed end-to-end checks.

