# Controlled egress-proxy integration testing

The application requires `EGRESS_PROXY_URL` in production. The proxy is an
external security boundary; the application-side tests only verify that the
configured proxy is selected and that redirects are not followed.

Use a disposable, access-controlled forward proxy in an isolated test network.
The proxy configuration must:

- resolve the requested hostname itself and reject the request if any resolved
  address is private, loopback, link-local, reserved, multicast, metadata-range,
  or IPv4-mapped IPv6;
- resolve immediately before connecting and reject a changed answer (DNS
  rebinding), including a public-then-private answer;
- permit only `http` and `https` destinations, reject credentials, and deny
  proxy administration from the test client network;
- tunnel HTTPS without TLS interception so the client validates the upstream
  certificate; and
- reject connection targets and redirects that violate the same destination
  policy.

Run the application with a test-only secret and PostgreSQL URL, then set
`EGRESS_PROXY_URL` to the proxy's private test address. Exercise this matrix
through the application check endpoint and inspect both application and proxy
logs:

The repository also contains an opt-in HTTPX integration test. With the
controlled proxy and fixture endpoints running, set these test-only variables
and run it from the project root:

```powershell
$env:RUN_EGRESS_PROXY_INTEGRATION = "1"
$env:EGRESS_PROXY_TEST_URL = "http://proxy.test:3128"
$env:EGRESS_PUBLIC_URL = "https://public-fixture.test/ok"
$env:EGRESS_PRIVATE_URL = "http://private-fixture.test/"
$env:EGRESS_REBIND_URL = "http://rebind-fixture.test/"
$env:EGRESS_REDIRECT_URL = "https://redirect-fixture.test/to-private"
$env:EGRESS_BAD_TLS_URL = "https://bad-tls-fixture.test/"
.venv\Scripts\python.exe -m pytest -q tests/test_egress_proxy_integration.py
```

`EGRESS_REBIND_URL` must resolve to a public address on the first lookup and a
private address on the second lookup (or otherwise exercise the proxy's
revalidation path). The fixture DNS and proxy logs must prove this behavior.
The test is skipped unless explicitly enabled and must not be pointed at a
general-purpose or public proxy.

| Case | Expected result |
|---|---|
| Public HTTPS endpoint with valid certificate | Check proceeds to the endpoint |
| `127.0.0.1`, RFC1918, link-local, metadata, or mapped IPv6 target | Rejected before egress or by the proxy |
| Hostname whose second resolution becomes private | Proxy rejects the connection |
| 3xx response to a private or loopback URL | Recorded as `unsafe_redirect`; no follow-up request |
| Invalid upstream certificate | Check fails with a request error; no TLS bypass |

Do not use a general public proxy or a proxy with TLS verification disabled.
These cases are not considered passed until they run against the actual
controlled proxy and the proxy logs demonstrate destination-IP enforcement.
