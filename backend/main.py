import os
from typing import List

import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import Base, engine, get_db
import models
import schemas
import auth

# Create tables on startup if they don't exist yet (seed.py also does this).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Prime Crest Logistics Tracking API", version="1.0.0")

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


@app.get("/")
def health_check():
    return {"status": "ok", "service": "prime-crest-tracking-api"}


@app.post("/api/v1/admin/login", response_model=schemas.AdminTokenResponse)
def admin_login(payload: schemas.AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(models.AdminUser).where(models.AdminUser.username == payload.username))
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = auth.create_access_token(subject=user.username)
    return schemas.AdminTokenResponse(access_token=token, expires_in_minutes=auth.JWT_EXPIRES_MINUTES)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/shipments/track/{tracking_number}", response_model=schemas.ShipmentOut)
def track_shipment(tracking_number: str, db: Session = Depends(get_db)):
    shipment = db.scalar(
        select(models.Shipment).where(models.Shipment.tracking_number == tracking_number)
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="No shipment found for that tracking number")
    return shipment


# ---------------------------------------------------------------------------
# Admin endpoints (require Authorization: Bearer <jwt> header)
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/admin/shipments",
    response_model=List[schemas.ShipmentOut],
    dependencies=[Depends(require_admin)],
)
def list_shipments(db: Session = Depends(get_db)):
    return db.scalars(select(models.Shipment).order_by(models.Shipment.created_at.desc())).all()


@app.post(
    "/api/v1/admin/shipments",
    response_model=schemas.ShipmentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_shipment(payload: schemas.ShipmentCreate, db: Session = Depends(get_db)):
    existing = db.scalar(
        select(models.Shipment).where(models.Shipment.tracking_number == payload.tracking_number)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Tracking number already exists")

    shipment = models.Shipment(**payload.model_dump())
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
    shipment = db.scalar(
        select(models.Shipment).where(models.Shipment.tracking_number == tracking_number)
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="No shipment found for that tracking number")

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
    return shipment
