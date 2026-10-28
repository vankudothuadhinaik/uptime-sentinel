# Doppler development workflow

Uptime Sentinel reads configuration from environment variables. Doppler can
provide those variables for local development without adding a secret file to
the repository. The application does not import the Doppler SDK and does not
require the Doppler CLI at runtime.

## Project and configuration

[`doppler.yaml`](./doppler.yaml) selects the existing Doppler project
`uptime-sentinel` and development configuration `dev_personal`. It contains no
token or secret value.

The application settings are listed in [`app/config.py`](./app/config.py), with
the optional `SENTRY_DSN` read by [`app/sentry.py`](./app/sentry.py). Keep
variable names aligned with those files.

## Windows PowerShell

After installing and logging in to the Doppler CLI:

```powershell
cd C:\path\to\uptime-sentinel
doppler setup --project uptime-sentinel --config dev_personal
doppler run -- python -m alembic upgrade head
doppler run -- uvicorn app.main:app --reload
```

The wrapper injects secrets only into the child process. Do not use
`Get-Content .env`, `printenv`, or environment enumeration in shared logs.

Use the development configuration for local work. Select staging or production
only from an approved deployment environment; never copy those secrets into a
local file.

## Docker Compose and CI

The existing Compose file reads a physical, ignored `.env` through `env_file`.
Use `.env.example` as the safe template, then set the Compose service
connection values before starting the stack. The application container must
use PostgreSQL and the Compose service hostnames, not the template's
SQLite/localhost defaults:

```powershell
Copy-Item .env.example .env
# Set DATABASE_URL to the repository's local PostgreSQL Compose URL.
# Set REDIS_URL=redis://redis:6379/0.
docker compose up --build
```

Alternatively, generate `.env` from the approved development Doppler
configuration without displaying its contents, then verify that
`DATABASE_URL` targets `postgres` and `REDIS_URL` targets `redis` before
starting Compose. Do not use a production or staging configuration for this
local stack.

`doppler run -- docker compose up` does not replace Compose's required
`env_file`. Public CI does not require Doppler authentication and should retain
its existing service environment and repository secrets.
