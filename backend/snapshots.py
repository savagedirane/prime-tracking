"""
Serialize a shipment's current state to JSON — the shared "snapshot" shape
used by the SSE stream, cache, and write-path publishes. Always opens its
own short-lived DB session so callers (including long-lived SSE generators
and background threads) never depend on a request-scoped session.
"""
from sqlalchemy import select

import models
import schemas
from database import SessionLocal


def shipment_snapshot_json(tracking_number: str) -> str | None:
    """Current ShipmentOut JSON for a tracking number, or None if unknown.
    Includes soft-deleted shipments (their deleted_at is set), so live
    watchers learn about deletions gracefully."""
    db = SessionLocal()
    try:
        shipment = db.scalar(
            select(models.Shipment).where(models.Shipment.tracking_number == tracking_number)
        )
        if not shipment:
            return None
        return schemas.ShipmentOut.model_validate(shipment).model_dump_json()
    finally:
        db.close()
