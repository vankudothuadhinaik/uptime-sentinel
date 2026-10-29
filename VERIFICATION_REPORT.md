# Uptime Sentinel verification report

Run date: 2026-10-30

## Current change

PR #14 is open from `hardening/ops-metrics-proxy-limits-recovery`. The latest code-validated commit is `3d6df4e41f88a8b3f4d1a99719adf4c8d05635e2` (`Refresh verification report with latest CI evidence`). GitHub Actions run [#336](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40933176847) completed successfully for that commit: `checks`, `proxy-local-integration`, and `compose-smoke` passed; the opt-in external `proxy-integration` job was skipped because controlled fixture infrastructure is not configured. Subsequent commits only refresh this report and README; their latest-head workflow is being checked separately.

## Release gates

| Gate | Result | Evidence |
|---|---|---|
| Local dependencies | **PASS** | `pip check`: no broken requirements. |
| Lint and formatting | **PASS** | Ruff check passed; 37 files already formatted. |
| Configured type check | **PASS** | `mypy app worker.py migrations tests`: no issues in 27 files. |
| Application test suite | **PASS** | `pytest -q`: 73 passed, 8 skipped, 3 warnings. |
| Compilation | **PASS** | `compileall` completed successfully. |
| Dependency audit | **PASS** | `pip-audit --skip-editable`: no known vulnerabilities. |
| PostgreSQL 16 migrations | **PASS** | Docker PostgreSQL 16 migration upgrade completed. |
| PostgreSQL concurrency/fencing | **PASS** | Real two-session Docker test: 2 passed; exclusive claims, expired-lease reclaim, fencing, and incident serialization exercised. |
| Docker Compose smoke | **PASS** | Images built; PostgreSQL/Redis health, API migrations/readiness, auth, monitor creation, worker persistence, and public status passed. |
| Local egress proxy security | **PASS** | Real local fixture tests cover private/mixed DNS answers, DNS failures, resolver pinning, redirects, auth, unsupported methods/ports, target credentials, invalid TLS, overload 503, and oversized headers. |
| External controlled egress proxy | **BLOCKED** | All six fixture variables are unset; `tests/test_egress_proxy_integration.py` reported 5 skipped. No external security pass is claimed. |
| GitHub Actions run #336 | **PASS** | Workflow completed successfully for code-validated commit `3d6df4e41f88a8b3f4d1a99719adf4c8d05635e2`; `checks`, local proxy integration, and Compose smoke passed. External `proxy-integration` was skipped. |

## Changes made

- Renamed the retained failed-check metric from an `_total` name to a gauge name and added assertions for empty/populated values and types.
- Added deterministic proxy overload and oversized-header regression tests; oversized headers now return HTTP 431 instead of escaping as an unhandled stream-reader exception.
- Added a real socket-level allowed-forwarding fixture and disposed every SQLite test engine to eliminate test-resource warnings.
- Made the PostgreSQL concurrency regression test isolate unrelated existing monitors and restore their state, so persistent test databases cannot invalidate the exclusive-claim assertion.
- Corrected proxy, README, and release-checklist documentation where literal escape sequences or stale behavior descriptions were present.

## Skips and blockers

The local test suite previously reported eight skips, including the five external proxy cases, PostgreSQL tests without a configured URL in the host virtual environment, and an OpenSSL-dependent fixture. The local invalid-TLS test has now been tightened to require a certificate-verification-specific error; run #333 passed with this assertion. The PostgreSQL tests were separately run against Docker PostgreSQL 16 and passed. The external proxy cases require an independently controlled authenticated proxy plus public, private, rebinding, redirect, and invalid-TLS fixture URLs. They cannot be safely invented or replaced with mocks.

The project is not production-certified. Production use still requires controlled proxy infrastructure, real external proxy integration evidence, production secrets, migration/release procedures, and operational continuity controls.

## Render deployment observation

The Render workspace contains `uptime-sentinel-egress-proxy` at `https://uptime-sentinel-egress-proxy.onrender.com`, currently configured to deploy from `integration/sentry-doppler` (not this PR branch). Render reports the deployment as live from commit `e7f5c547a034c051cc4d35afbefc23b93a78dc86`. The service's IP allowlist permits all source IPs, so its safety depends on the proxy's fail-closed authentication and destination validation. I did not change service settings or expose/read secret values. A live deployment is not proof that the external proxy security matrix passed; fixture-backed verification remains blocked.

## Git state

- Remote: `https://github.com/vankudothuadhinaik/uptime-sentinel.git`
- Branch: `hardening/ops-metrics-proxy-limits-recovery`
- PR: #14, open, not merged
- No new repository, remote, tag, or force push was created.
