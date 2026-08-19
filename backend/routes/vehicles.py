"""
routes/vehicles.py — OCR + QR endpoints (Week 1.1 scope).

WHY these two endpoints live together in one router even though
/vehicles/entry and /vehicles/exit aren't built until later weeks:
they're all part of the same entry-flow described in the project brief
(camera → OCR → form → QR ticket → DB write), so keeping them in one
file avoids splitting a single workflow across multiple modules.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from models.vehicle import OCRReadResponse, QRGenerateRequest, QRGenerateResponse
from services.ocr_service import read_plate_from_image
from services.qr_service import generate_qr_token, generate_qr_image_base64

logger = logging.getLogger("neuropark.routes.vehicles")

router = APIRouter()

# Files larger than this are almost certainly a mistake (wrong file
# picked, or the phone accidentally selected a video) rather than a
# real plate photo — reject early instead of burning OCR compute on it.
_MAX_IMAGE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


@router.post("/ocr/read-plate", response_model=OCRReadResponse)
async def read_plate(file: UploadFile = File(...)):
    """
    Receives a photo from the Attendant PWA and returns the best-guess
    plate number. Runs server-side per constraint #8 — the phone only
    captures and uploads the image; EasyOCR never runs in the browser.
    """
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. "
                   "Please upload a JPEG, PNG, or WEBP photo of the number plate.",
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty. Please retake the photo and try again.",
        )

    if len(image_bytes) > _MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image is too large ({len(image_bytes) / 1_048_576:.1f} MB, "
                   f"max is 8 MB). Check the PWA's camera capture/compression settings.",
        )

    try:
        result = read_plate_from_image(image_bytes)
        return OCRReadResponse(**result)
    except RuntimeError as exc:
        # A RuntimeError from ocr_service means something structurally
        # wrong (model not loaded, corrupt image bytes) — not just "no
        # plate found," which is instead returned above as success=False
        # so the PWA can show a friendly "retake photo" prompt.
        logger.error(f"OCR endpoint failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/qr/generate", response_model=QRGenerateResponse)
async def generate_qr(payload: QRGenerateRequest):
    """
    Generates a QR ticket (UUID token + PNG image) for a vehicle about
    to be checked in. Does NOT write to MongoDB — see the note on
    QRGenerateRequest in models/vehicle.py for why that's deferred to
    Week 1.2's /vehicles/entry endpoint.
    """
    try:
        token = generate_qr_token()
        qr_image = generate_qr_image_base64(token)

        return QRGenerateResponse(
            qr_token=token,
            qr_image_base64=qr_image,
            vehicle_number=payload.vehicle_number,
            lot_id=payload.lot_id,
            slot_id=payload.slot_id,
            generated_at=datetime.now(timezone.utc),
        )
    except RuntimeError as exc:
        logger.error(f"QR generation endpoint failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc