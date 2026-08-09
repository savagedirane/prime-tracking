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
    note: Optional[str] = None
    timestamp: datetime


class ShipmentCreate(BaseModel):
    tracking_number: str
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


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tracking_number: str
    status: str
    origin: str
    destination: str
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
    milestones: List[MilestoneOut] = []
