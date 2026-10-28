import os
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.types import Event, Hint

_initialized = False


def _scrub_event(event: Event, hint: Hint) -> Event:
    event_data = cast(dict[str, Any], event)
    request = event_data.get("request")
    if isinstance(request, dict):
        request.pop("headers", None)
        request.pop("cookies", None)
        request.pop("data", None)
        request.pop("query_string", None)
        url = request.get("url")
        if isinstance(url, str):
            parsed = urlsplit(url)
            request["url"] = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    event_data.pop("breadcrumbs", None)
    return event


def initialize_sentry() -> None:
    global _initialized
    if _initialized:
        return
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return
    init = cast(Any, sentry_sdk.init)
    init(
        dsn=dsn,
        integrations=[FastApiIntegration()],
        send_default_pii=False,
        request_bodies="never",
        include_local_variables=False,
        before_send=_scrub_event,
    )
    _initialized = True
