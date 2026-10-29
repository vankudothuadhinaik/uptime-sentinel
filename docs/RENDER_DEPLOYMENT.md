# Historical Render deployment notes

**Status: out of scope.** Uptime Sentinel is being completed as a free GitHub portfolio project with automated CI and a local Docker Compose demo. Paid hosting is not required, and this document is not an instruction to deploy services.

The earlier Render exploration included:
- A free test egress-proxy service at `https://uptime-sentinel-egress-proxy.onrender.com`.
- A free PostgreSQL instance with an expiry date; it is not required by the local demo.
- A proposed API/worker blueprint using paid Starter plans.

The paid `render.yaml` blueprint was removed on 2026-10-29. No Render API or worker deployment is claimed. Do not recreate paid services just to complete the portfolio project.

## Security warning

The old test proxy was publicly reachable and had not passed the controlled egress-proxy integration suite. Do not use it for sensitive or production traffic. Application-side URL/DNS validation alone cannot fully prevent DNS-rebinding time-of-check/time-of-use attacks; production use would require a private, independently verified egress proxy.

## If production deployment is considered later

Treat it as a separate project decision. Before provisioning any service, explicitly review current costs and approve the budget. Then separately plan private proxy enforcement, controlled integration fixtures, secrets, database continuity, migrations, and end-to-end verification. A skipped proxy integration job is not a security pass, and a green CI run is not production-readiness evidence.

For the current free-only scope, use the [README quick start](../README.md#quick-start), [CI workflow](../.github/workflows/ci.yml), and [release checklist](../RELEASE_CHECKLIST.md).
