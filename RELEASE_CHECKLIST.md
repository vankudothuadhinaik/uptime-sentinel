# Release checklist

## Push-readiness decision

**PUBLISHED** to the configured repository. Production deployment remains
blocked on the infrastructure gates listed below.

## Completed in this review

- [x] PostgreSQL-compatible Alembic migrations through `0003_lease_tokens`.
- [x] Database-backed scheduler claims with unique lease tokens and conditional completion.
- [x] Paused, due, expired, exception, and slow-check regression coverage.
- [x] SSRF validation for non-global and mixed DNS answers, mapped IPv6, credentials, and redirects.
- [x] HTTP total timeout and bounded response streaming.
- [x] Production JWT, PostgreSQL, and controlled-egress-proxy configuration validation.
- [x] Existing project environment tests, lint, formatting, type checking, compilation, migration round trip, and dependency audit.
- [x] Authentication rate-limit smoke test.

## Required before production deployment

- [x] Add PostgreSQL multi-worker/concurrency tests to CI; local execution remains blocked without PostgreSQL.
- [x] Run Docker Compose end-to-end smoke tests in GitHub Actions.
- [ ] Deploy behind a controlled egress proxy that revalidates destinations to address the DNS-rebinding residual risk.
- [ ] Configure secret management, TLS, metrics, structured logs, backups, and retention cleanup.
- [x] Verify the exact GitHub repository owner, repository name, remote URL, and branch before publishing.

## Verification notes for this release

- Existing virtual environment: 20 tests passed, 6 infrastructure-gated tests skipped, Ruff lint and format checks passed, mypy passed for 19 source files, compilation passed, and SQLite migration upgrade/downgrade/upgrade passed.
- A fresh isolated installation was attempted but hit the command's 120-second execution limit; it was not claimed as passed.
- `pip-audit 2.10.1 --skip-editable`: no known vulnerabilities; advisory database was reachable during the run.
- PostgreSQL multi-worker verification was not run because PostgreSQL tooling/service was unavailable in the review environment.
- PostgreSQL multi-worker verification passed in GitHub Actions run `40590812969`.
- Docker Compose build/startup passed in GitHub Actions run `40590812969`.
- Controlled egress-proxy integration remains pending manual CI/staging execution with controlled fixture secrets.
