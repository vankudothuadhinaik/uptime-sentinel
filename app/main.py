from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .leases import claim_monitor, finish_claim
from .models import CheckResult, Incident, Monitor, User
from .monitoring import StaleLease, perform_check
from .schemas import AuthIn, CheckOut, IncidentOut, MonitorIn, MonitorOut, MonitorPatch, Token
from .security import current_user, hash_password, make_token, verify_password
from .sentry import initialize_sentry
from .ssrf import UnsafeTarget, validate_target

initialize_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    storage_uri=get_settings().rate_limit_storage_uri,
)
app = FastAPI(title="Uptime Sentinel", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(select(func.count(User.id)))
    except Exception as exc:
        raise HTTPException(503, "database unavailable") from exc
    return {"status": "ready"}


@app.post("/auth/register", response_model=Token, status_code=201)
@limiter.limit("10/minute")
def register(request: Request, data: AuthIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "email already registered")
    user = User(email=email, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "email already registered") from exc
    db.refresh(user)
    return Token(access_token=make_token(user.id))


@app.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, data: AuthIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "invalid email or password")
    return Token(access_token=make_token(user.id))


def owned_monitor(monitor_id: int, user: User, db: Session) -> Monitor:
    monitor = db.scalar(
        select(Monitor).where(Monitor.id == monitor_id, Monitor.owner_id == user.id)
    )
    if not monitor:
        raise HTTPException(404, "monitor not found")
    return monitor


@app.post("/monitors", response_model=MonitorOut, status_code=201)
def create_monitor(
    data: MonitorIn, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    # Resolve/validate before taking the owner's quota lock so network DNS work
    # cannot unnecessarily block other monitor-management requests.
    try:
        validate_target(str(data.url))
    except UnsafeTarget as exc:
        raise HTTPException(422, str(exc)) from exc

    # Serialize quota checks for this owner. The row lock is held through the
    # count and insert/commit, preventing concurrent requests exceeding quota.
    locked_owner = db.scalar(select(User).where(User.id == user.id).with_for_update())
    if locked_owner is None:
        raise HTTPException(401, "authenticated user no longer exists")
    count = db.scalar(select(func.count(Monitor.id)).where(Monitor.owner_id == user.id)) or 0
    if count >= get_settings().max_monitors_per_user:
        db.rollback()
        raise HTTPException(429, "monitor limit reached")
    monitor = Monitor(
        owner_id=user.id,
        url=str(data.url),
        next_check_at=datetime.now(timezone.utc),
        **data.model_dump(exclude={"url"}),
    )
    db.add(monitor)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "monitor creation conflicted with another request") from exc
    db.refresh(monitor)
    return monitor


@app.get("/monitors", response_model=list[MonitorOut])
def list_monitors(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return db.scalars(
        select(Monitor)
        .where(Monitor.owner_id == user.id)
        .order_by(Monitor.id.asc())
        .offset(offset)
        .limit(limit)
    ).all()


@app.get("/monitors/{monitor_id}", response_model=MonitorOut)
def get_monitor(monitor_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return owned_monitor(monitor_id, user, db)


@app.patch("/monitors/{monitor_id}", response_model=MonitorOut)
def update_monitor(
    monitor_id: int,
    data: MonitorPatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    monitor = owned_monitor(monitor_id, user, db)
    values = data.model_dump(exclude_unset=True)
    if "url" in values:
        try:
            validate_target(str(values["url"]))
        except UnsafeTarget as exc:
            raise HTTPException(422, str(exc)) from exc
        values["url"] = str(values["url"])
    for key, value in values.items():
        setattr(monitor, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(422, "monitor update violates a data constraint") from exc
    db.refresh(monitor)
    return monitor


@app.delete("/monitors/{monitor_id}", status_code=204)
def delete_monitor(
    monitor_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    db.delete(owned_monitor(monitor_id, user, db))
    db.commit()


@app.post("/monitors/{monitor_id}/check", response_model=CheckOut)
def check_monitor(
    monitor_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    monitor = owned_monitor(monitor_id, user, db)
    claimed = claim_monitor(db, monitor.id, datetime.now(timezone.utc))
    if claimed is None:
        raise HTTPException(409, "monitor check is already running or the monitor is paused")
    claimed_monitor, token = claimed
    try:
        return perform_check(db, claimed_monitor, lease_token=token)
    except StaleLease as exc:
        raise HTTPException(409, "monitor lease expired; retry the check") from exc
    finally:
        finish_claim(
            db,
            claimed_monitor.id,
            token,
            datetime.now(timezone.utc) + timedelta(seconds=claimed_monitor.interval_seconds),
        )


@app.get("/monitors/{monitor_id}/checks", response_model=list[CheckOut])
def checks(
    monitor_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    owned_monitor(monitor_id, user, db)
    return db.scalars(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@app.get("/monitors/{monitor_id}/incidents", response_model=list[IncidentOut])
def incidents(
    monitor_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    owned_monitor(monitor_id, user, db)
    return db.scalars(
        select(Incident)
        .where(Incident.monitor_id == monitor_id)
        .order_by(Incident.started_at.desc(), Incident.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@app.get("/status/{monitor_id}")
def public_status(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.scalar(select(Monitor).where(Monitor.id == monitor_id, Monitor.public.is_(True)))
    if not monitor:
        raise HTTPException(404, "public status page not found")
    latest = db.scalar(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor.id)
        .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
    )
    return {
        "name": monitor.name,
        "status": "up" if latest and latest.is_up else "down",
        "last_check": CheckOut.model_validate(latest) if latest else None,
    }
