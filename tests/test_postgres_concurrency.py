import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import Incident, Monitor, User
from app.monitoring import perform_check
from worker import _claim_due, _finish_claim

POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL is not configured")
def test_postgres_claim_is_exclusive_and_fenced():
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)
    user_id = None
    monitor_id = None
    try:
        with Session.begin() as db:
            user = User(email=f"concurrency-{uuid4().hex}@example.test", password_hash="test")
            db.add(user)
            db.flush()
            user_id = user.id
            monitor = Monitor(
                owner_id=user.id,
                name="concurrency",
                url="https://example.com",
                interval_seconds=60,
                timeout_seconds=5,
                next_check_at=now - timedelta(seconds=1),
            )
            db.add(monitor)
            db.flush()
            monitor_id = monitor.id

        barrier = Barrier(2)

        def claim_once():
            with Session() as db:
                barrier.wait()
                claimed = _claim_due(db, now)
                return None if claimed is None else claimed[1]

        with ThreadPoolExecutor(max_workers=2) as pool:
            tokens = [
                future.result() for future in (pool.submit(claim_once), pool.submit(claim_once))
            ]

        claimed_tokens = [token for token in tokens if token is not None]
        assert len(claimed_tokens) == 1
        first_token = claimed_tokens[0]

        with Session.begin() as db:
            monitor = db.get(Monitor, monitor_id)
            assert monitor is not None
            monitor.lease_until = now - timedelta(seconds=1)

        with Session() as db:
            reclaimed = _claim_due(db, now)
            assert reclaimed is not None
            _, second_token = reclaimed
            assert second_token != first_token

        with Session() as db:
            assert _finish_claim(db, monitor_id, first_token, now) is False
    finally:
        with Session.begin() as db:
            if monitor_id is not None:
                monitor = db.scalar(select(Monitor).where(Monitor.id == monitor_id))
                if monitor is not None:
                    db.delete(monitor)
            if user_id is not None:
                existing = db.get(User, user_id)
                if existing is not None:
                    db.delete(existing)
        engine.dispose()


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="POSTGRES_TEST_URL is not configured")
def test_postgres_concurrent_failures_create_one_open_incident(monkeypatch):
    """Concurrent failing checks must serialize incident changes under PostgreSQL."""
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    user_id = None
    monitor_id = None
    try:
        with Session.begin() as db:
            user = User(email=f"incident-{uuid4().hex}@example.test", password_hash="test")
            db.add(user)
            db.flush()
            user_id = user.id
            monitor = Monitor(
                owner_id=user.id,
                name="incident-concurrency",
                url="https://example.com",
                interval_seconds=60,
                timeout_seconds=5,
                next_check_at=datetime.now(timezone.utc),
            )
            db.add(monitor)
            db.flush()
            monitor_id = monitor.id

        monkeypatch.setattr("app.monitoring.validate_target", lambda _: None)
        barrier = Barrier(2)

        def fail_once():
            with Session() as db:
                monitor = db.get(Monitor, monitor_id)
                assert monitor is not None
                client = httpx.Client(
                    transport=httpx.MockTransport(lambda request: httpx.Response(503))
                )
                try:
                    barrier.wait()
                    perform_check(db, monitor, client)
                finally:
                    client.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(fail_once), pool.submit(fail_once)]
            for future in futures:
                future.result(timeout=15)

        with Session() as db:
            open_count = db.scalar(
                select(func.count(Incident.id)).where(
                    Incident.monitor_id == monitor_id,
                    Incident.resolved_at.is_(None),
                )
            )
            open_incident = db.scalar(
                select(Incident).where(
                    Incident.monitor_id == monitor_id,
                    Incident.resolved_at.is_(None),
                )
            )
            assert open_count == 1
            assert open_incident is not None
            assert open_incident.failure_count == 2
    finally:
        with Session.begin() as db:
            if monitor_id is not None:
                monitor = db.get(Monitor, monitor_id)
                if monitor is not None:
                    db.delete(monitor)
            if user_id is not None:
                user = db.get(User, user_id)
                if user is not None:
                    db.delete(user)
        engine.dispose()
