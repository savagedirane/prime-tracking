import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from database import get_db
import cache
import models
import schemas
import auth
from utils import generate_tracking_number


def run_migrations() -> None:
    """Apply pending Alembic migrations at startup.

    Migrations are idempotent (the initial one adopts pre-Alembic databases),
    so this is safe on fresh SQLite files, your existing dev database, and
    the production Supabase instance alike. Single-instance deployments can
    auto-migrate like this; switch to running `alembic upgrade head` as a
    separate release step if you ever scale to multiple instances.
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(cfg, "head")


run_migrations()

app = FastAPI(title="Prime Crest Logistics Tracking API", version="1.1.0")

# ---------------------------------------------------------------------------
# Rate limiting (per client IP; memory store by default, Redis-ready)
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

TRACK_RATELIMIT = os.environ.get("TRACK_RATELIMIT", "30/minute")
AUTH_RATELIMIT = os.environ.get("AUTH_RATELIMIT", "10/minute")

# Allow the local Vite dev server (and any origin in dev). Lock this down to
# your real frontend domain(s) before deploying to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer(auto_error=False)


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """JWT bearer guard for admin endpoints.

    Expects an `Authorization: Bearer <token>` header, issued by
    /api/v1/admin/login. Replaces the earlier shared-secret x-admin-key.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        payload = auth.decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please sign in again")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]


# ---------------------------------------------------------------------------
# Shared query helpers
# ---------------------------------------------------------------------------

def _active_shipment(db: Session, tracking_number: str) -> models.Shipment:
    """Fetch a non-deleted shipment or raise 404."""
    shipment = db.scalar(
        select(models.Shipment).where(
            models.Shipment.tracking_number == tracking_number,
            models.Shipment.deleted_at.is_(None),
        )
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="No shipment found for that tracking number")
    return shipment


@app.get("/")
def health_check():
    return {"status": "ok", "service": "prime-crest-tracking-api"}


@app.post("/api/v1/admin/login", response_model=schemas.AdminTokenResponse)
@limiter.limit(AUTH_RATELIMIT)  # brute-force protection on credential checks
def admin_login(request: Request, payload: schemas.AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(models.AdminUser).where(models.AdminUser.username == payload.username))
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = auth.create_access_token(subject=user.username)
    return schemas.AdminTokenResponse(access_token=token, expires_in_minutes=auth.JWT_EXPIRES_MINUTES)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/shipments/track/{tracking_number}", response_model=schemas.ShipmentOut)
@limiter.limit(TRACK_RATELIMIT)
def track_shipment(request: Request, tracking_number: str, db: Session = Depends(get_db)):
    """Public lookup — the hottest endpoint, so it is rate-limited per IP and
    served from a short-TTL cache (see cache.py) instead of hitting Postgres
    on every request."""
    tracking_number = tracking_number.strip().upper()

    cached = cache.get_cached(tracking_number)
    if cached is not None:
        return cached

    shipment = _active_shipment(db, tracking_number)
    out = schemas.ShipmentOut.model_validate(shipment)
    cache.set_cached(tracking_number, out)
    return out


# ---------------------------------------------------------------------------
# Admin endpoints (require Authorization: Bearer <jwt> header)
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/admin/shipments",
    response_model=schemas.ShipmentPage,
    dependencies=[Depends(require_admin)],
)
def list_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = Query(None, description="Search tracking number, names, origin, destination"),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Paginated + searchable shipment list.

    Server-side pagination keeps the response size constant as the table
    grows (the old `.all()` would eventually ship the whole table to every
    dashboard load).
    """
    if status_filter and status_filter not in schemas.VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {schemas.VALID_STATUSES}",
        )

    conditions = []
    if not include_deleted:
        conditions.append(models.Shipment.deleted_at.is_(None))
    if status_filter:
        conditions.append(models.Shipment.status == status_filter)
    if q:
        like = f"%{q.strip()}%"
        conditions.append(
            or_(
                models.Shipment.tracking_number.ilike(like),
                models.Shipment.sender_name.ilike(like),
                models.Shipment.recipient_name.ilike(like),
                models.Shipment.origin.ilike(like),
                models.Shipment.destination.ilike(like),
            )
        )

    base = select(models.Shipment)
    if conditions:
        base = base.where(*conditions)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    total_pages = math.ceil(total / page_size)

    rows = db.scalars(
        base.order_by(models.Shipment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return schemas.ShipmentPage(
        items=[schemas.ShipmentOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.post(
    "/api/v1/admin/shipments",
    response_model=schemas.ShipmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_shipment(payload: schemas.ShipmentCreate, db: Session = Depends(get_db)):
    # Server-generated unguessable numbers are the default; a client-supplied
    # number (data imports etc.) is still honored but must be unique.
    tracking_number = payload.tracking_number or generate_tracking_number(db)

    existing = db.scalar(
        select(models.Shipment).where(models.Shipment.tracking_number == tracking_number)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Tracking number already exists")

    data = payload.model_dump()
    data["tracking_number"] = tracking_number
    shipment = models.Shipment(**data)
    db.add(shipment)
    db.flush()

    # Seed the first milestone automatically so the timeline is never empty.
    db.add(
        models.Milestone(
            shipment_id=shipment.id,
            status="Order Registered",
            location=payload.origin,
            note="Shipment created and registered in the system.",
        )
    )
    db.commit()
    db.refresh(shipment)
    return shipment


@app.patch(
    "/api/v1/admin/shipments/{tracking_number}",
    response_model=schemas.ShipmentOut,
    dependencies=[Depends(require_admin)],
)
def update_shipment(
    tracking_number: str,
    payload: schemas.ShipmentUpdate,
    db: Session = Depends(get_db),
):
    """Partial edit (recipient names, dimensions, ETA…). The headline status
    is deliberately NOT editable here — it always derives from milestones."""
    shipment = _active_shipment(db, tracking_number)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(shipment, field, value)
    db.commit()
    db.refresh(shipment)

    cache.invalidate(shipment.tracking_number)
    return shipment


@app.delete(
    "/api/v1/admin/shipments/{tracking_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_shipment(tracking_number: str, db: Session = Depends(get_db)):
    """Soft delete — hides the shipment from tracking and the admin list while
    keeping its history in the database (auditable, restorable)."""
    shipment = _active_shipment(db, tracking_number)
    shipment.deleted_at = datetime.now(timezone.utc)
    db.commit()

    cache.invalidate(shipment.tracking_number)


@app.post(
    "/api/v1/admin/shipments/{tracking_number}/restore",
    response_model=schemas.ShipmentOut,
    dependencies=[Depends(require_admin)],
)
def restore_shipment(tracking_number: str, db: Session = Depends(get_db)):
    """Undo a soft delete."""
    shipment = db.scalar(
        select(models.Shipment).where(models.Shipment.tracking_number == tracking_number)
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="No shipment found for that tracking number")
    if shipment.deleted_at is None:
        raise HTTPException(status_code=409, detail="Shipment is not deleted")

    shipment.deleted_at = None
    db.commit()
    db.refresh(shipment)

    cache.invalidate(shipment.tracking_number)
    return shipment


@app.post(
    "/api/v1/admin/shipments/{tracking_number}/milestones",
    response_model=schemas.ShipmentOut,
    dependencies=[Depends(require_admin)],
)
def add_milestone(
    tracking_number: str,
    payload: schemas.MilestoneCreate,
    db: Session = Depends(get_db),
):
    shipment = _active_shipment(db, tracking_number)

    db.add(
        models.Milestone(
            shipment_id=shipment.id,
            status=payload.status,
            location=payload.location,
            note=payload.note,
        )
    )
    # The shipment's headline status always reflects its latest milestone.
    shipment.status = payload.status
    db.commit()
    db.refresh(shipment)

    cache.invalidate(shipment.tracking_number)
    return shipment
