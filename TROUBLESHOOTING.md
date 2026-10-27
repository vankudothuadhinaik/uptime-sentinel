# Troubleshooting

- `email-validator` errors: install the project with `pip install -e ".[dev]"` rather than only installing FastAPI.
- Readiness returns 503: check `DATABASE_URL` and run `alembic upgrade head`.
- Monitor creation rejects a hostname: the SSRF guard requires DNS to resolve to public IP space.
- Docker commands fail locally: install Docker Desktop, then run `docker compose up --build`.
- A second production worker must not be started until a distributed lease/idempotency mechanism is enabled; the included worker is intentionally single-process.
