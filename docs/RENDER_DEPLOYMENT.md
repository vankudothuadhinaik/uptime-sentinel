# Render deployment runbook

This runbook is for the **dedicated Uptime Sentinel Render workspace** (workspace ID `tea-dbghjus9v7es73dnq900`). Do not deploy this project into an unrelated workspace. The PostgreSQL resource `uptime-sentinel-db` (`dpg-dbghkmc9v7es73dns2ig-a`) is available in Singapore. The API service, worker service, and controlled egress proxy have not yet been deployed or verified.

## Render Blueprint

The repository now includes a `render.yaml` defining the API web service and a genuine continuous background worker. Review it before using **New Blueprint Instance** in the Uptime Sentinel workspace.

Important:
- The blueprint does **not** create another database or an egress proxy. Reuse the existing PostgreSQL instance and provide its internal connection URL when prompted.
- It requires `DATABASE_URL`, `JWT_SECRET`, and `EGRESS_PROXY_URL` to be configured as secret environment values for both services. Do not enter dummy values or commit secrets.
- Configure the private, destination-validating proxy before deploying production services. The application intentionally refuses production startup without `EGRESS_PROXY_URL`.
- The blueprint uses Render Starter service plans for the API and worker. Review current pricing in the dashboard before creating resources; deploying the blueprint may incur charges.
- A successful blueprint parse or service creation is not proof that the proxy is secure or that the application works end to end.

## Required architecture

Use these resources in the dedicated workspace and the same region:

1. **Existing Render PostgreSQL** database, with backups appropriate to the data's importance.
2. **Web service** from this repository, using the Docker runtime and repository-root Dockerfile. Health check path: `/health/ready`.
3. **Background worker** from the same repository and Dockerfile, with Docker command overridden to `python worker.py`. Do not expose a public HTTP port for the worker.
4. A **controlled egress proxy** reachable from both services. It must enforce public destination IP policy itself and log rejections. Do not use a public/general-purpose proxy.

Use the same repository branch/commit for the API and worker. The Dockerfile installs the Python package and defaults to running the API with Uvicorn.

## Environment variables

Set these in the Render dashboard for **both API and worker** unless noted:

| Key | Value |
| --- | --- |
| APP_ENV | production |
| DATABASE_URL | Existing Render PostgreSQL internal connection URL, using `postgresql+psycopg://` if required by SQLAlchemy |
| JWT_SECRET | Unique random secret generated in a password manager; at least 32 characters |
| EGRESS_PROXY_URL | Private URL of the controlled proxy; reachable from both services |
| RESULT_RETENTION_DAYS | 30 unless the data policy specifies otherwise |
| ACCESS_TOKEN_MINUTES | 60 unless a shorter token lifetime is required |
| CHECK_USER_AGENT | UptimeSentinel/0.1 or an approved identifying value |
| MAX_MONITORS_PER_USER | 50 |
| MAX_RESPONSE_BYTES | 65536 |

Do not commit production values to Git. Do not use the Compose-only local database password in production. Do not set `DATABASE_URL` to SQLite. Redis is not required by the current worker implementation.

## API service settings

- Runtime: Docker
- Dockerfile path: `./Dockerfile`
- Docker context: `.`
- Health check path: `/health/ready`
- Start command: use the Dockerfile default (Uvicorn)
- Keep automatic deploys enabled only for the intended production branch.

The API container's default command does not run migrations. Before the first release and after each schema-changing release, run `alembic upgrade head` once against the production database using a controlled one-off command/job with the same image and database environment. Do not run migrations independently in both API and worker processes.

## Worker service settings

- Runtime: Docker
- Dockerfile path: `./Dockerfile`
- Docker context: `.`
- Docker command override: `python worker.py`
- Use the same production environment variables as the API.
- Do not add a public HTTP health check or expose a port for this service. Monitor worker logs and restart events.

## GitHub Actions proxy integration

Configure these **repository Actions secrets** only after the controlled proxy and fixture endpoints exist:

- `EGRESS_PROXY_TEST_URL`
- `EGRESS_PUBLIC_URL`
- `EGRESS_PRIVATE_URL`
- `EGRESS_REBIND_URL`
- `EGRESS_REDIRECT_URL`
- `EGRESS_BAD_TLS_URL`

Then manually dispatch the CI workflow and confirm that `proxy-integration` actually executes and passes. Inspect the proxy enforcement logs. A skipped job is not a security pass.

## Pre-launch release gate

Before accepting user traffic, verify all of the following:

- [ ] A dedicated workspace is selected and the API, worker, database, and proxy are in the intended region.
- [ ] The existing database URL is private/internal and uses PostgreSQL.
- [ ] The JWT secret is unique, random, and at least 32 characters.
- [ ] The controlled proxy is reachable and blocks private, loopback, link-local, reserved, multicast, metadata, mapped IPv6, DNS-rebinding, and unsafe redirect destinations.
- [ ] Proxy fixture endpoints and all six GitHub Actions secrets are configured.
- [ ] Manually run CI and verify `proxy-integration` passes; inspect proxy enforcement logs.
- [ ] Apply migrations once, then verify `/health/live` and `/health/ready` return success.
- [ ] Register a disposable test account, create a test monitor for an allowed public fixture, confirm worker scheduling and check/result persistence, verify recovery behavior, then clean up test data.
- [ ] Confirm API and worker logs contain no secrets and that TLS, access controls, alerts, and backups are appropriate.
- [ ] Review the existing database's current plan and expiry. Upgrade/renew it before its expiry if production continuity is required.

A successful Docker Compose smoke test is not a production deployment. Do not mark the proxy security gate complete based on mocked unit tests, a successful API health check, or blueprint creation alone.
