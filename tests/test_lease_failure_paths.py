from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.leases import _as_utc, claim_monitor, finish_claim


class FailingSession:
    def __init__(self, monitor=None):
        self.monitor = monitor
        self.rolled_back = False

    def scalar(self, statement):
        return self.monitor

    def commit(self):
        raise RuntimeError("synthetic database commit failure")

    def refresh(self, instance):
        raise AssertionError("refresh must not run after a failed commit")

    def rollback(self):
        self.rolled_back = True

    def execute(self, statement):
        raise RuntimeError("synthetic database execute failure")


def test_as_utc_normalizes_naive_and_aware_datetimes():
    naive = datetime(2026, 10, 29, 12, 0)
    aware = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)

    assert _as_utc(naive).tzinfo is timezone.utc
    assert _as_utc(aware) == aware


def test_claim_monitor_rolls_back_and_reraises_commit_failure():
    monitor = SimpleNamespace(
        id=7,
        interval_seconds=60,
        timeout_seconds=5,
        lease_until=None,
        lease_token=None,
    )
    db = FailingSession(monitor)

    with pytest.raises(RuntimeError, match="synthetic database commit failure"):
        claim_monitor(db, monitor_id=7)

    assert db.rolled_back is True
    assert monitor.lease_token is not None
    assert monitor.lease_until is not None


def test_finish_claim_rolls_back_and_returns_false_on_database_failure():
    db = FailingSession()
    next_check = datetime.now(timezone.utc)

    assert finish_claim(db, monitor_id=7, token="old-token", next_check_at=next_check) is False
    assert db.rolled_back is True
