"""
models/vehicle.py — Pydantic models for vehicle records and API payloads.

WHY separate request/response models instead of one big "Vehicle" model:
The MongoDB 'vehicles' document (see project schema) has fields that
don't exist yet at entry time (exit_time, amount_charged) and others
that should never be client-settable (status, qr_token — server-
controlled). Splitting these out means FastAPI's automatic request
validation rejects malformed or spoofed input before it ever reaches
business logic, instead of us checking for it manually in every route.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class OCRReadResponse(BaseModel):
    """Response shape for POST /ocr/read-plate."""

    success: bool
    plate_number: Optional[str] = None
    confidence: float = 0.0
    raw_detections: list[str] = Field(default_factory=list)
    message: str


class QRGenerateRequest(BaseModel):
    """
    Request body for POST /qr/generate.

    WHY this endpoint takes vehicle_number + lot_id + slot_id as input
    but this file does NOT write anything to MongoDB yet: Week 1.1 only
    builds the QR ticket itself, as scoped. The actual INSERT into the
    'vehicles' collection (constraint #1 — exactly one DB write on
    entry) happens in /vehicles/entry, wired up in Week 1.2 once the
    Attendant PWA's entry form exists to call it after the attendant
    confirms the OCR-read plate number.
    """

    vehicle_number: str = Field(..., min_length=4, max_length=15)
    lot_id: str = Field(..., min_length=1)
    slot_id: str = Field(..., min_length=1)

    @field_validator("vehicle_number")
    @classmethod
    def normalize_plate(cls, v: str) -> str:
        # WHY normalize here: "up16 ab1234" and "UP16AB1234" must be
        # treated as the same vehicle. Doing this in the model (not in
        # the route) means every future caller of this model gets the
        # same normalization for free.
        return v.strip().upper().replace(" ", "")


class QRGenerateResponse(BaseModel):
    """Response shape for POST /qr/generate."""

    qr_token: str
    qr_image_base64: str
    vehicle_number: str
    lot_id: str
    slot_id: str
    generated_at: datetime


class VehicleRecord(BaseModel):
    """
    Mirrors the MongoDB 'vehicles' collection schema exactly as defined
    in the project brief. Not used by any endpoint yet in Week 1.1 —
    defined now so that Week 1.2's /vehicles/entry and Week 2.1's
    /vehicles/exit both import this same shape instead of two slightly
    different ones drifting apart over time.
    """

    vehicle_number: str
    lot_id: str
    slot_id: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    amount_charged: Optional[float] = None  # INR (₹) — constraint #9
    status: str = Field(default="active", pattern="^(active|completed)$")
    qr_token: str