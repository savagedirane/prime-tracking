import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, Index
from sqlalchemy.orm import relationship

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(String, primary_key=True, default=_uuid)
    tracking_number = Column(String, unique=True, index=True, nullable=False)

    status = Column(String, nullable=False, default="Order Registered", index=True)
    # One of: Order Registered, Departed Origin, In Transit, Customs Clearance,
    # Out for Delivery, Delivered

    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)

    sender_name = Column(String, nullable=False)
    recipient_name = Column(String, nullable=False)

    carrier = Column(String, default="Prime Crest Logistics")
    shipping_mode = Column(String, default="Air Express")

    weight_kg = Column(Float, nullable=True)
    length_cm = Column(Float, nullable=True)
    width_cm = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)

    estimated_delivery = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    # Soft delete: when set, the shipment is hidden from public tracking and
    # the default admin list, but the history is retained and restorable.
    deleted_at = Column(DateTime, nullable=True)

    milestones = relationship(
        "Milestone",
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="Milestone.timestamp",
    )


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True, default=_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class Milestone(Base):
    __tablename__ = "milestones"
    __table_args__ = (
        # The tracking lookup joins milestones by shipment and sorts by time —
        # a composite index serves that whole query pattern.
        Index("ix_milestones_shipment_timestamp", "shipment_id", "timestamp"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(String, ForeignKey("shipments.id"), nullable=False)

    status = Column(String, nullable=False)
    location = Column(String, nullable=False)
    note = Column(String, nullable=True)
    timestamp = Column(DateTime, default=_utcnow, index=True)

    shipment = relationship("Shipment", back_populates="milestones")
