import asyncio
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .leases import _as_utc
from .models import CheckResult, Incident, Monitor
from .ssrf import UnsafeTarget, validate_target


class StaleLease(RuntimeError):
    """Raised when a monitor check finishes after another worker owns its lease."""


async def _request_with_deadline(monitor: Monitor) -> tuple[int | None, bool, str | None, str | None]:
    """Perform the complete HTTP exchange under one wall-clock deadline."""
    settings = get_settings()
    timeout_seconds = monitor.timeout_seconds
    proxy = (
        httpx.Proxy(
            settings.egress_proxy_url,
            auth=(
                (settings.egress_proxy_username, settings.egress_proxy_password)
                if settings.egress_proxy_username
                else None
            ),
        )
        if settings.egress_proxy_url
        else None
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            validate_target(monitor.url)
            async with (
                httpx.AsyncClient(
                    follow_redirects=False,
                    trust_env=False,
                    proxy=proxy,
                    timeout=httpx.Timeout(timeout_seconds),
                ) as client,
                client.stream(
                    "GET",
                    monitor.url,
                    headers={"User-Agent": settings.check_user_agent},
                ) as response,
            ):
                    status_code = response.status_code
                    response_bytes = 0
                    async for chunk in response.aiter_bytes():
                        response_bytes += len(chunk)
                        if response_bytes > settings.max_response_bytes:
                            return (
                                status_code,
                                False,
                                "response_too_large",
                                "response exceeded configured size limit",
                            )
                    if 300 <= status_code < 400:
                        return (
                            status_code,
                            False,
                            "unsafe_redirect",
                            "redirects are not followed by the monitor",
                        )
                    is_up = 200 <= status_code < 300
                    return status_code, is_up, None if is_up else "http_error", None
    except (TimeoutError, httpx.TimeoutException):
        return None, False, "timeout", "request timed out"
    except UnsafeTarget:
        return None, False, "request_error", "monitor request failed"
    except httpx.HTTPError:
        return None, False, "request_error", "monitor request failed"
    except Exception:
        # Do not expose implementation details in persisted API data.
        return None, False, "internal_error", "monitor request failed"


def _request_with_injected_client(
    monitor: Monitor,
    client: httpx.Client,
) -> tuple[int | None, bool, str | None, str | None]:
    """Synchronous transport path for deterministic unit-test transports."""
    settings = get_settings()
    deadline = time.monotonic() + monitor.timeout_seconds
    try:
        validate_target(monitor.url)
        with client.stream(
            "GET",
            monitor.url,
            timeout=httpx.Timeout(monitor.timeout_seconds),
            headers={"User-Agent": settings.check_user_agent},
        ) as response:
            response_bytes = 0
            for chunk in response.iter_bytes():
                if time.monotonic() >= deadline:
                    raise httpx.TimeoutException("total request deadline exceeded")
                response_bytes += len(chunk)
                if response_bytes > settings.max_response_bytes:
                    return (
                        response.status_code,
                        False,
                        "response_too_large",
                        "response exceeded configured size limit",
                    )
            if 300 <= response.status_code < 400:
                return (
                    response.status_code,
                    False,
                    "unsafe_redirect",
                    "redirects are not followed by the monitor",
                )
            is_up = 200 <= response.status_code < 300
            return response.status_code, is_up, None if is_up else "http_error", None
    except httpx.TimeoutException:
        return None, False, "timeout", "request timed out"
    except (httpx.HTTPError, UnsafeTarget):
        return None, False, "request_error", "monitor request failed"
    except Exception:
        return None, False, "internal_error", "monitor request failed"


def perform_check(
    db: Session,
    monitor: Monitor,
    client: httpx.Client | None = None,
    *,
    lease_token: str | None = None,
) -> CheckResult:
    started = time.perf_counter()
    if client is None:
        status_code, is_up, error_category, error_message = asyncio.run(
            _request_with_deadline(monitor)
        )
    else:
        status_code, is_up, error_category, error_message = _request_with_injected_client(
            monitor, client
        )

    # The monitor row is the serialization point for incident transitions.
    # PostgreSQL holds this lock until the check and incident update commit.
    try:
        locked_monitor = db.scalar(
            select(Monitor).where(Monitor.id == monitor.id).with_for_update()
        )
        if locked_monitor is None:
            raise StaleLease("monitor was deleted while its check was running")
        now = datetime.now(timezone.utc)
        if lease_token is not None:
            lease_until = locked_monitor.lease_until
            if (
                locked_monitor.lease_token != lease_token
                or lease_until is None
                or _as_utc(lease_until) <= now
            ):
                raise StaleLease("monitor lease expired or was replaced before result persistence")

        result = CheckResult(
            monitor_id=monitor.id,
            is_up=is_up,
            status_code=status_code,
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
            error_category=error_category,
            error_message=error_message,
        )
        db.add(result)
        db.flush()
        open_incident = db.scalar(
            select(Incident).where(
                Incident.monitor_id == monitor.id,
                Incident.resolved_at.is_(None),
            )
        )
        if result.is_up and open_incident:
            open_incident.resolved_at = result.checked_at
        elif not result.is_up and open_incident:
            open_incident.failure_count += 1
        elif not result.is_up:
            db.add(Incident(monitor_id=monitor.id, failure_count=1))
        db.commit()
        db.refresh(result)
        return result
    except Exception:
        db.rollback()
        raise
