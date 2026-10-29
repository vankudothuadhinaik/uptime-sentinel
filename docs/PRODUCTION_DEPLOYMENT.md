# Production deployment guide

This production-oriented self-host profile adds TLS termination, internal-only database/cache networks, authenticated Redis, persistent volumes, container hardening, and required production configuration. API and worker run as the non-root user baked into the Docker image. It is not a security certification or a one-click free public host.

## Hard security prerequisites

**Do not deploy publicly until every item below is true.**

1. A Linux host you control, with Docker Engine and Compose v2. Configure its firewall to allow inbound TCP 80/443 only (and SSH from your trusted IP). The host must also enforce outbound egress policy: application containers must not bypass the controlled proxy for internet destinations. Compose networks alone do not provide this host-level egress firewall.
2. A domain with DNS records pointing to the host. Caddy obtains and renews HTTPS certificates automatically. Ports 80/443 must be reachable for ACME.
3. A **private, independently controlled egress proxy** that authenticates the app, resolves destinations at connection time, blocks loopback/private/link-local/multicast/reserved IP ranges, rejects DNS rebinding and unsafe redirects, validates TLS, and fails closed. The current public test proxy is not approved for production.
4. Unique high-entropy credentials and a backup/restore plan for PostgreSQL. Free databases may sleep, expire, have low limits, or lack production-grade backup guarantees.

Compose cannot create or certify the proxy or host firewall. Never use `APP_ENV=production` with a blank proxy or weak secrets; startup validation should fail closed.

## Configure

1. Clone the repository at a reviewed release commit.
2. Copy `.env.production.example` to `.env.production`. Generate independent random secrets locally; do not commit the completed file:
   ```sh
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   Run it separately for JWT, database, Redis, proxy username/password.
3. Replace `DOMAIN`, `EMAIL`, database values, and proxy endpoint/credentials with your own values. Ensure the private proxy is reachable from the API container.
4. Validate and start:
   ```sh
   docker compose --env-file .env.production -f docker-compose.production.yml config --quiet
   docker compose --env-file .env.production -f docker-compose.production.yml up --build -d
   docker compose --env-file .env.production -f docker-compose.production.yml ps
   docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=100 api worker caddy
   ```
5. Verify `https://YOUR_DOMAIN/health/live` and `/health/ready`. Confirm `/metrics`, `/docs`, `/redoc`, and `/openapi.json` return 404 through Caddy. Test a public HTTPS monitor and confirm private/loopback targets, redirect-to-private targets, DNS rebinding, and invalid TLS are blocked by the controlled proxy.
6. Verify worker scheduling, persisted check history, incident opening and recovery, and worker logs using endpoints you control.
7. Configure off-host encrypted database backups and perform a restore test. Define alerting for API health, worker progress, database capacity, and overdue checks. Do not expose `/metrics` publicly.
8. Before upgrades, take a backup, review migrations, deploy the same reviewed commit to API and worker, and verify health and scheduled processing.

## What is free and what is not

The repository, Docker, Caddy, GitHub Actions within plan limits, and local tests can be used free. **A reliable public production service is not guaranteed to be free**: it needs an always-on host, a controlled proxy, a domain (sometimes free), and durable backup storage. Free app hosts often sleep or limit workers, networking, and persistent disks. Do not claim 24/7 monitoring from a sleeping service.

For a zero-cost portfolio demonstration, continue using local Compose. For a real public service, verify current pricing, persistence, always-on worker support, egress/firewall control, and backup terms before choosing a host. Never use the existing public test proxy for production traffic.

## Known boundaries

- This profile does not bundle an egress proxy: implementing and validating that security boundary is separate work.
- Keep populated `.env.production` out of Git.
- Host firewall/egress rules, DNS, secrets, backups, and external security fixtures require operator setup and verification.
- Caddy blocks public access to metrics and Swagger/OpenAPI paths.
- Only successful deployment, external proxy tests, restore drills, and operational monitoring justify calling a live instance production-ready.
