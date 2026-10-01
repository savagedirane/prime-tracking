from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator

VALID_STATUSES = [
    "Order Registered",
    "Departed Origin",
    "In Transit",
    "Customs Clearance",
    "Out for Delivery",
    "Delivered",
]


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class MilestoneCreate(BaseModel):
    status: str
    location: str
    note: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    location: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    note: Optional[str] = None
    timestamp: datetime
    created_by: Optional[str] = None


def _clean_tracking_number(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = v.strip().upper()
    if not v:
        return None
    if len(v) < 6 or len(v) > 32 or not all(c.isalnum() or c == "-" for c in v):
        raise ValueError("tracking_number must be 6-32 characters (letters, digits, dashes)")
    return v


class ShipmentCreate(BaseModel):
    # Optional: when omitted the server generates an unguessable, Luhn-valid
    # number (see utils.generate_tracking_number). Provided numbers are still
    # accepted for data imports / backwards compatibility.
    tracking_number: Optional[str] = None
    origin: str
    destination: str
    sender_name: str
    recipient_name: str
    carrier: str = "Prime Crest Logistics"
    shipping_mode: str = "Air Express"
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    estimated_delivery: Optional[datetime] = None

    @field_validator("tracking_number")
    @classmethod
    def tracking_number_format(cls, v: Optional[str]) -> Optional[str]:
        return _clean_tracking_number(v)


class ShipmentUpdate(BaseModel):
    """Partial update — only provided fields are applied (exclude_unset)."""
    origin: Optional[str] = None
    destination: Optional[str] = None
    sender_name: Optional[str] = None
    recipient_name: Optional[str] = None
    carrier: Optional[str] = None
    shipping_mode: Optional[str] = None
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    estimated_delivery: Optional[datetime] = None


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tracking_number: str
    status: str
    origin: str
    destination: str
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lng: Optional[float] = None
    sender_name: str
    recipient_name: str
    carrier: str
    shipping_mode: str
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    estimated_delivery: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    milestones: List[MilestoneOut] = []


class ShipmentPage(BaseModel):
    """Paginated result envelope for GET /api/v1/admin/shipments."""
    items: List[ShipmentOut]
    total: int
    page: int
    page_size: int
    total_pages: int
