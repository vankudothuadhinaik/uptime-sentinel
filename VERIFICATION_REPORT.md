# Uptime Sentinel verification report

Run date: 2026-10-29

## Current change

PR #14 is open from `hardening/ops-metrics-proxy-limits-recovery`. The latest pushed commit is `6bec54c` (`Document latest proxy fixture verification`). GitHub Actions run [#325](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40924701371) passed for parent commit `4adefa5`; GitHub's checks page for `6bec54c` is still loading and does not expose a completed result, so the latest-SHA CI gate is **PENDING/BLOCKED**.

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
| GitHub Actions run #325 | **PASS** | Required CI jobs passed for parent commit `4adefa5`; opt-in `proxy-integration` was skipped. |
| CI for latest commit `6bec54c` | **PENDING/BLOCKED** | The push is present on the remote branch, but GitHub's public checks page is still loading and no completed workflow result is exposed for this SHA. |

## Changes made

- Renamed the retained failed-check metric from an `_total` name to a gauge name and added assertions for empty/populated values and types.
- Added deterministic proxy overload and oversized-header regression tests; oversized headers now return HTTP 431 instead of escaping as an unhandled stream-reader exception.
- Added a real socket-level allowed-forwarding fixture and disposed every SQLite test engine to eliminate test-resource warnings.
- Made the PostgreSQL concurrency regression test isolate unrelated existing monitors and restore their state, so persistent test databases cannot invalidate the exclusive-claim assertion.
- Corrected proxy, README, and release-checklist documentation where literal escape sequences or stale behavior descriptions were present.

## Skips and blockers

The eight local test skips include the five external proxy cases, PostgreSQL tests without a configured URL in the host virtual environment, and an OpenSSL-dependent fixture. The PostgreSQL tests were separately run against Docker PostgreSQL 16 and passed. The external proxy cases require an independently controlled authenticated proxy plus public, private, rebinding, redirect, and invalid-TLS fixture URLs. They cannot be safely invented or replaced with mocks.

The project is not production-certified. Production use still requires controlled proxy infrastructure, real external proxy integration evidence, production secrets, migration/release procedures, and operational continuity controls.

## Git state

- Remote: `https://github.com/vankudothuadhinaik/uptime-sentinel.git`
- Branch: `hardening/ops-metrics-proxy-limits-recovery`
- PR: #14, open, not merged
- No new repository, remote, tag, or force push was created.
