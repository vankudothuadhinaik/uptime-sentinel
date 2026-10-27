import time

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import CheckResult, Incident, Monitor
from .ssrf import UnsafeTarget, validate_target


def perform_check(db: Session, monitor: Monitor, client: httpx.Client | None = None) -> CheckResult:
    started = time.perf_counter()
    result = CheckResult(monitor_id=monitor.id, is_up=False)
    own_client = client is None
    settings = get_settings()
    request_client = client or httpx.Client(
        follow_redirects=False,
        trust_env=False,
        proxy=settings.egress_proxy_url or None,
    )
    try:
        validate_target(monitor.url)
        with request_client.stream(
            "GET",
            monitor.url,
            timeout=httpx.Timeout(monitor.timeout_seconds),
            headers={"User-Agent": get_settings().check_user_agent},
        ) as response:
            result.status_code = response.status_code
            response_bytes = 0
            for chunk in response.iter_bytes():
                response_bytes += len(chunk)
                if response_bytes > settings.max_response_bytes:
                    break
            if response_bytes > get_settings().max_response_bytes:
                result.error_category = "response_too_large"
                result.error_message = "response exceeded configured size limit"
            elif 300 <= response.status_code < 400:
                result.error_category = "unsafe_redirect"
                result.error_message = "redirects are not followed by the monitor"
            else:
                result.is_up = 200 <= response.status_code < 300
                if not result.is_up:
                    result.error_category = "http_error"
    except httpx.TimeoutException:
        result.error_category, result.error_message = "timeout", "request timed out"
    except (httpx.HTTPError, UnsafeTarget):
        result.error_category, result.error_message = "request_error", "monitor request failed"
    except Exception:
        # Do not strand the worker or expose implementation details in API data.
        result.error_category, result.error_message = "internal_error", "monitor request failed"
    finally:
        if own_client:
            request_client.close()
    result.latency_ms = max(0, round((time.perf_counter() - started) * 1000))
    db.add(result)
    db.flush()
    open_incident = db.scalar(
        select(Incident).where(Incident.monitor_id == monitor.id, Incident.resolved_at.is_(None))
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
