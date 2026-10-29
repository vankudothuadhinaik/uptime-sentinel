"""Interval scheduler with shared database-backed monitor leases and fencing."""

import logging
from datetime import datetime, timedelta, timezone
from signal import SIGINT, SIGTERM, signal
from threading import Event
from types import FrameType

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.leases import _as_utc, claim_monitor, finish_claim
from app.models import CheckResult, Monitor
from app.monitoring import StaleLease, perform_check

logger = logging.getLogger(__name__)
RETENTION_CLEANUP_INTERVAL = timedelta(hours=24)
RETENTION_RETRY_INTERVAL = timedelta(hours=1)


def _claim_due(db, now: datetime) -> tuple[Monitor, str] | None:
    """Claim one due monitor using the same lease protocol as manual checks."""
    return claim_monitor(db, None, now, due_only=True)


def _finish_claim(db, monitor_id: int, token: str, next_check_at: datetime) -> bool:
    """Compatibility wrapper for callers/tests using the former worker helper."""
    return finish_claim(db, monitor_id, token, next_check_at)


def cleanup_old_results(db: Session, now: datetime | None = None) -> int:
    """Delete expired check history but preserve incident records."""
    retention_days = get_settings().result_retention_days
    if retention_days < 1:
        raise ValueError("RESULT_RETENTION_DAYS must be at least 1")

    cutoff = _as_utc(now or datetime.now(timezone.utc)) - timedelta(days=retention_days)
    try:
        result = db.execute(
            delete(CheckResult)
            .where(CheckResult.checked_at < cutoff)
            .execution_options(synchronize_session=False)
        )
        deleted = max(0, getattr(result, "rowcount", 0) or 0)
        db.commit()
        return deleted
    except Exception:
        db.rollback()
        raise


def run_once(now: datetime | None = None) -> int:
    current_time = _as_utc(now or datetime.now(timezone.utc))
    checked = 0
    with SessionLocal() as db:
        while True:
            claimed = _claim_due(db, current_time)
            if claimed is None:
                break
            monitor, token = claimed
            monitor_id = monitor.id
            try:
                perform_check(db, monitor, lease_token=token)
                checked += 1
                logger.info("monitor_check_completed", extra={"monitor_id": monitor_id})
            except StaleLease:
                db.rollback()
                logger.warning("monitor_check_stale_lease", extra={"monitor_id": monitor_id})
            except Exception:
                db.rollback()
                logger.exception("monitor_check_failed", extra={"monitor_id": monitor_id})
                # Leave a short, bounded retry delay if this worker still owns
                # the lease; finalization is fenced against a newer claim.
                raise
            finally:
                finish_claim(
                    db,
                    monitor_id,
                    token,
                    current_time + timedelta(seconds=monitor.interval_seconds),
                )
    return checked


def run_forever(stop_event: Event) -> None:
    next_retention_cleanup = datetime.min.replace(tzinfo=timezone.utc)
    while not stop_event.is_set():
        now = datetime.now(timezone.utc)
        if now >= next_retention_cleanup:
            try:
                with SessionLocal() as db:
                    deleted = cleanup_old_results(db, now=now)
                if deleted:
                    logger.info(
                        "retention_cleanup_completed",
                        extra={"deleted_check_results": deleted},
                    )
            except Exception:
                logger.exception("retention_cleanup_failed")
                next_retention_cleanup = now + RETENTION_RETRY_INTERVAL
            else:
                next_retention_cleanup = now + RETENTION_CLEANUP_INTERVAL

        try:
            run_once()
        except Exception:
            # A transient database/persistence problem should be observable but
            # must not permanently terminate the continuous scheduler loop.
            logger.exception("scheduler_cycle_failed")
        stop_event.wait(5)


if __name__ == "__main__":
    stop_event = Event()

    def request_stop(_: int, __: FrameType | None) -> None:
        stop_event.set()

    signal(SIGTERM, request_stop)
    signal(SIGINT, request_stop)
    run_forever(stop_event)
