"""Shared database-backed monitor lease helpers used by manual and scheduled checks."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from .models import Monitor

logger = logging.getLogger(__name__)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def claim_monitor(
    db: Session,
    monitor_id: int | None,
    now: datetime | None = None,
    *,
    due_only: bool = False,
) -> tuple[Monitor, str] | None:
    """Atomically claim one monitor using the same lease fields for all triggers."""
    current = _as_utc(now or datetime.now(timezone.utc))
    statement = select(Monitor).where(
        Monitor.is_paused.is_(False),
        or_(Monitor.lease_until.is_(None), Monitor.lease_until <= current),
    )
    if monitor_id is not None:
        statement = statement.where(Monitor.id == monitor_id)
    if due_only:
        statement = (
            statement.where(or_(Monitor.next_check_at.is_(None), Monitor.next_check_at <= current))
            .order_by(Monitor.next_check_at.asc().nulls_first(), Monitor.id)
            .limit(1)
        )
    statement = statement.with_for_update(skip_locked=True)
    monitor = db.scalar(statement)
    if monitor is None:
        return None

    token = uuid4().hex
    lease_seconds = max(monitor.interval_seconds, monitor.timeout_seconds + 60)
    monitor.lease_until = current + timedelta(seconds=lease_seconds)
    monitor.lease_token = token
    try:
        db.commit()
        db.refresh(monitor)
    except Exception:
        db.rollback()
        logger.exception("monitor_lease_claim_failed", extra={"monitor_id": monitor.id})
        raise
    logger.info(
        "monitor_lease_claimed",
        extra={"monitor_id": monitor.id, "due_only": due_only},
    )
    return monitor, token


def finish_claim(db: Session, monitor_id: int, token: str, next_check_at: datetime) -> bool:
    """Release only the lease still owned by this token; expired leases self-recover."""
    try:
        result = db.execute(
            update(Monitor)
            .where(Monitor.id == monitor_id, Monitor.lease_token == token)
            .values(lease_until=None, lease_token=None, next_check_at=next_check_at)
            .execution_options(synchronize_session=False)
        )
        completed = getattr(result, "rowcount", None) == 1
        db.commit()
        if not completed:
            logger.warning(
                "monitor_lease_fence_rejected",
                extra={"monitor_id": monitor_id},
            )
        return completed
    except Exception:
        db.rollback()
        logger.exception("monitor_lease_finalize_failed", extra={"monitor_id": monitor_id})
        # Do not mask the check's original result/error. The lease expiry allows
        # another worker to recover if the database remains unavailable.
        return False
