"""Interval scheduler with fenced, database-backed monitor leases.

PostgreSQL workers use SELECT FOR UPDATE SKIP LOCKED. Every claim has a unique
token, and completion updates are conditional on that token, so an expired
worker cannot clear or reschedule a newer owner's lease.
"""

from datetime import datetime, timedelta, timezone
from signal import SIGINT, SIGTERM, signal
from threading import Event
from types import FrameType
from uuid import uuid4

from sqlalchemy import or_, select, update

from app.db import SessionLocal
from app.models import Monitor
from app.monitoring import perform_check


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _claim_due(db, now: datetime) -> tuple[Monitor, str] | None:
    statement = (
        select(Monitor)
        .where(
            Monitor.is_paused.is_(False),
            or_(Monitor.next_check_at.is_(None), Monitor.next_check_at <= now),
            or_(Monitor.lease_until.is_(None), Monitor.lease_until <= now),
        )
        .order_by(Monitor.next_check_at.asc().nulls_first(), Monitor.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    monitor = db.scalar(statement)
    if monitor is None:
        return None
    token = uuid4().hex
    # The lease is longer than the configured HTTP timeout, preventing normal
    # slow checks from overlapping while still allowing crash recovery.
    lease_seconds = max(monitor.interval_seconds, monitor.timeout_seconds + 60)
    monitor.lease_until = now + timedelta(seconds=lease_seconds)
    monitor.lease_token = token
    db.commit()
    db.refresh(monitor)
    return monitor, token


def _finish_claim(db, monitor_id: int, token: str, next_check_at: datetime) -> bool:
    result = db.execute(
        update(Monitor)
        .where(Monitor.id == monitor_id, Monitor.lease_token == token)
        .values(lease_until=None, lease_token=None, next_check_at=next_check_at)
    )
    db.commit()
    return result.rowcount == 1


def run_once(now: datetime | None = None) -> int:
    current_time = _as_utc(now or datetime.now(timezone.utc))
    checked = 0
    with SessionLocal() as db:
        while True:
            claimed = _claim_due(db, current_time)
            if claimed is None:
                break
            monitor, token = claimed
            try:
                perform_check(db, monitor)
            except Exception:
                db.rollback()
            finally:
                _finish_claim(
                    db,
                    monitor.id,
                    token,
                    current_time + timedelta(seconds=monitor.interval_seconds),
                )
            checked += 1
    return checked


def run_forever(stop_event: Event) -> None:
    while not stop_event.is_set():
        run_once()
        stop_event.wait(5)


if __name__ == "__main__":
    stop_event = Event()

    def request_stop(_: int, __: FrameType | None) -> None:
        stop_event.set()

    signal(SIGTERM, request_stop)
    signal(SIGINT, request_stop)
    run_forever(stop_event)
