# Controlled egress proxy

This service is an authenticated HTTP forward proxy intended for controlled test
traffic. It is not an open proxy. It accepts HTTP forward requests and CONNECT
tunnels for TLS ports 443 and 8443 only.

## Security properties

- Requires HTTP Basic proxy authentication. Set `PROXY_USERNAME` (at least 8
  characters) and `PROXY_PASSWORD` (at least 32 random characters) as secrets.
- Resolves each destination immediately before connecting; rejects any DNS answer
  that is not globally routable; and connects directly to the exact resolved IP
  address. This avoids the common resolve-then-re-resolve DNS-rebinding race.
- Only permits HTTPS CONNECT to ports 443/8443 and plain HTTP to port 80.
- Does not follow redirects. The client controls redirect behavior and TLS
  certificate validation end-to-end.
- Provides `GET /healthz` for platform health checks. This endpoint is not a
  proxy request and does not require authentication.

## Deployment notes

Deploy this directory as a Docker web service only for controlled testing. A
Render web service is internet-reachable, so keep strong credentials, restrict
ingress at the platform/network layer where available, and do not use it as an
unauthenticated shared proxy. Prefer a private network endpoint for production.
Set a stable high-entropy password and do not commit secrets.

## Test endpoints

The proxy implementation alone does not provide the six test fixture URLs.
Create or use controlled HTTPS fixtures for:
- a normal public HTTPS response;
- a known private destination (expected HTTP 403);
- a controlled DNS-rebinding hostname that resolves to a private address (expected HTTP 403);
- a redirect response;
- a TLS endpoint with an invalid certificate.

Do not label `localhost` or a random failed connection as a DNS-rebinding test.
A failed connection is not proof of proxy policy enforcement. Configure the
six `EGRESS_*` GitHub Actions repository secrets only after these fixtures
are deployed and independently verified.
