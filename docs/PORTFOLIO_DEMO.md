# Portfolio demo: Uptime Sentinel

Use this guide for a 2–3 minute screen-share or project interview. The demo uses the local Docker Compose stack; it does not depend on a public deployment.

## Before the demo

1. Clone the repository and follow the [README quick start](../README.md#docker-compose).
2. Copy `.env.example` to `.env` and set the local Compose `DATABASE_URL` described in the README.
3. Start the stack with `docker compose up --build`.
4. Open [Swagger UI](http://127.0.0.1:8000/docs) and verify the API is healthy at `/health/live`.
5. Keep the [latest CI run](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40935659101) open in another tab.

## Suggested walkthrough

### 1. Explain the problem (20 seconds)

“Uptime Sentinel periodically checks configured HTTP/HTTPS endpoints, stores check history, and tracks incidents through failure and recovery. The project focuses on correctness and operational behavior, not just a CRUD API.”

### 2. Show the architecture (20 seconds)

Open [the architecture diagram](images/architecture.svg). Explain the API, PostgreSQL, background worker, bounded checker, and the separate production egress-proxy boundary.

### 3. Demonstrate the flow (60–90 seconds)

- Register or log in using disposable local-demo credentials.
- Create a monitor for a safe public test endpoint.
- Trigger a check or wait for the worker to process it.
- Show the recorded check result and public status view.
- Explain the incident lifecycle: first failure opens an incident, consecutive failures update it, and a successful check resolves it.

Use the example requests in the [README](../README.md#example-register-and-create-a-monitor). Never use personal credentials or real secrets during a screen-share.

### 4. Explain the engineering choices (30–45 seconds)

- PostgreSQL-backed scheduling uses leases/fencing to reduce duplicate or stale work.
- HTTP checks bound response reads and do not follow redirects.
- URL/address validation and proxy-focused tests cover SSRF-related risks.
- CI includes linting, formatting, typing, tests, migration round trips, dependency audit, local proxy integration, and a Docker Compose end-to-end smoke test.

### 5. State the security boundary accurately (15 seconds)

“The local regression suite and standard CI pass. The external controlled-proxy suite is opt-in and has not been run because it needs independently controlled fixtures. Application-level validation alone is not a production security boundary, so I do not claim this project is production-certified.”

## Interview questions to prepare for

- Why use a separate worker instead of doing checks inside API requests?
- How do database leases and fencing tokens help with concurrency?
- Why is checking DNS once insufficient to prevent DNS-rebinding attacks?
- Why are redirects disabled and response bodies bounded?
- What does the local proxy test suite prove, and what does it not prove?
- How would you scale shared rate limiting and worker processing?
- How would you monitor the worker and safely operate database migrations?

## Evidence links

- [Repository](https://github.com/vankudothuadhinaik/uptime-sentinel)
- [CI runs](https://github.com/vankudothuadhinaik/uptime-sentinel/actions)
- [Latest standard CI run](https://github.com/vankudothuadhinaik/uptime-sentinel/actions/runs/40935659101)
- [Merged hardening PR #14](https://github.com/vankudothuadhinaik/uptime-sentinel/pull/14)
- [Verification report](../VERIFICATION_REPORT.md)
