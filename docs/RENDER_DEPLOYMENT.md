# Render deployment runbook

This runbook is for a **dedicated Uptime Sentinel Render workspace**. Do not deploy this project into an unrelated workspace. The connected Render integration currently exposes only the ESTIQ workspace, so no Render resources have been created by this runbook.

## Required architecture

Create these resources in the dedicated workspace and the same region:

1. **Render PostgreSQL** database, with backups appropriate to the data's importance.
2. **Web service** from this repository, using the Docker runtime and repository-root Dockerfile. Set the health check path to /health/ready.
3. **Background worker** from the same repository and Dockerfile, with Docker command overridden to python worker.py. Do not expose a public HTTP port for the worker.
4. A **controlled egress proxy** reachable from both services. It must enforce public destination IP policy itself and log rejections. Do not use a public/general-purpose proxy.

Use the same repository branch/commit for the API and worker. The Dockerfile installs the Python package and defaults to running the API with Uvicorn.

## Environment variables

Set these in the Render dashboard for **both API and worker** unless noted:

| Key | Value |
| --- | --- |
| APP_ENV | production |
| DATABASE_URL | Render PostgreSQL's internal connection URL, adjusted to SQLAlchemy's postgresql+psycopg:// driver form if needed |
| JWT_SECRET | Unique random secret generated in a password manager; at least 32 characters |
| EGRESS_PROXY_URL | Private URL of the controlled proxy; must be reachable from the service |
| RESULT_RETENTION_DAYS | 30 unless the data policy specifies otherwise |
| ACCESS_TOKEN_MINUTES | 60 unless a shorter token lifetime is required |
| CHECK_USER_AGENT | UptimeSentinel/0.1 or an approved identifying value |
| MAX_MONITORS_PER_USER | 50 |
| MAX_RESPONSE_BYTES | 65536 |

Do not commit production values to Git. Do not use the Compose-only local database password in production. Do not set DATABASE_URL to SQLite. Redis is not required by the current worker implementation.

## API service settings

- Runtime: Docker
- Dockerfile path: ./Dockerfile
- Docker context: .
- Health check path: /health/ready
- Start command: use the Dockerfile default (Uvicorn)
- Keep automatic deploys enabled only for the intended production branch.

The API container's default command does not run migrations. Before the first release and after each schema-changing release, run alembic upgrade head once against the production database using a controlled one-off command/job with the same image and database environment. Do not run migrations independently in both API and worker processes.

## Worker service settings

- Runtime: Docker
- Dockerfile path: ./Dockerfile
- Docker context: .
- Docker command override: python worker.py
- Use the same production environment variables as the API.
- Do not add a public HTTP health check or expose a port for this service. Monitor worker logs and restart events.

## Pre-launch release gate

Before accepting user traffic, verify all of the following:

- [ ] A dedicated workspace is selected and the API, worker, database, and proxy are in the intended region.
- [ ] The database URL is private/internal and uses PostgreSQL.
- [ ] The JWT secret is unique, random, and at least 32 characters.
- [ ] The controlled proxy is reachable and blocks private, loopback, link-local, reserved, multicast, metadata, mapped IPv6, DNS-rebinding, and unsafe redirect destinations.
- [ ] Proxy fixture endpoints and the six GitHub Actions repository secrets are configured: EGRESS_PROXY_TEST_URL, EGRESS_PUBLIC_URL, EGRESS_PRIVATE_URL, EGRESS_REBIND_URL, EGRESS_REDIRECT_URL, and EGRESS_BAD_TLS_URL.
- [ ] Manually run the GitHub Actions CI workflow to execute proxy-integration; confirm it passes and inspect proxy enforcement logs.
- [ ] Apply migrations once, then verify /health/live and /health/ready return success.
- [ ] Register a disposable test account, create a public test monitor, run a check, confirm worker scheduling, and confirm check/incident persistence. Remove the disposable account/monitor afterward.
- [ ] Confirm the API and worker logs contain no secrets and that the service has appropriate TLS, access controls, alerts, and backups.

A successful Docker Compose smoke test is not a production deployment. Do not mark the proxy security gate complete based on mocked unit tests or a successful API health check alone.
