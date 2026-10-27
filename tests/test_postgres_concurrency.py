import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from app.models import Monitor, User
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
            db.execute(
                update(Monitor)
                .where(Monitor.id == monitor_id)
                .values(lease_until=now - timedelta(seconds=1))
            )

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
