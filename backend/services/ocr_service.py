"""
services/ocr_service.py — Server-side license plate OCR using EasyOCR.

WHY OCR happens here (server-side) and not in the browser:
EasyOCR runs a PyTorch neural network that a mobile browser tab can't
execute. The Attendant PWA only captures the photo and uploads it; this
service does the actual text recognition. See project constraint #8
("OCR is server-side. QR scanning is client-side.").
"""

import io
import re
import logging
from typing import Optional

import cv2
import numpy as np
import easyocr
from PIL import Image

logger = logging.getLogger("neuropark.ocr")

# ----------------------------------------------------------------------
# WHY the reader is created once here, at module import time, instead of
# inside read_plate_from_image():
# EasyOCR loads a multi-hundred-MB neural network into memory the first
# time `easyocr.Reader(...)` is called. If we created a new Reader on
# every request, each API call would take 10-20+ seconds instead of
# ~1-2 seconds. Because Python only imports a module once per process,
# putting this at module level means the cost is paid exactly once,
# when uvicorn starts — not on every attendant's phone tap.
# ----------------------------------------------------------------------
try:
    # gpu=False: your dev machines are i5/Ryzen 5 laptops with 8GB RAM
    # and no CUDA GPU, so forcing CPU mode avoids a startup crash from
    # EasyOCR trying (and failing) to find a GPU.
    _reader: Optional[easyocr.Reader] = easyocr.Reader(["en"], gpu=False)
    logger.info("EasyOCR model loaded successfully (CPU mode).")
except Exception as exc:
    # We don't crash the whole server if the OCR model fails to load —
    # QR generation and health checks should still work. The
    # /ocr/read-plate endpoint reports the real error when it's called.
    logger.error(f"Failed to load EasyOCR model at startup: {exc}")
    _reader = None

# Indian number plate pattern, e.g. "UP16AB1234", "DL8CAF5031", "MH12DE1433".
# Format: 2 letters (state) + 1-2 digits (district) + 1-3 letters (series) + 3-4 digits.
#
# WHY this regex matters: EasyOCR frequently splits a plate into several
# separate text fragments ("UP16", "AB", "1234") because of bolts,
# frame borders, or glare cutting the plate visually into chunks. We
# join every fragment together first, THEN search for the substring
# that actually looks like a real plate — this is far more reliable
# than assuming the first or longest fragment is the answer.
_PLATE_PATTERN = re.compile(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}")


def _clean_plate_text(raw_fragments: list[str]) -> Optional[str]:
    """
    Joins OCR fragments and extracts the most plate-like substring.

    Returns None if nothing resembling a plate pattern was found, rather
    than guessing — the attendant should manually type it in that case
    instead of the app silently auto-filling garbage.
    """
    joined = "".join(raw_fragments).upper().replace(" ", "").replace("-", "")
    match = _PLATE_PATTERN.search(joined)
    if match:
        return match.group(0)
    return None


def read_plate_from_image(image_bytes: bytes) -> dict:
    """
    Runs EasyOCR on an uploaded image and returns the best-guess plate
    number, confidence, and raw detections.

    WHY this returns a dict with success=False instead of raising when
    no plate is found: "no plate detected" (bad angle, blur, glare) is
    an expected, common outcome that the PWA needs to handle gracefully
    (show a "retake photo" prompt) — it's not a server error. We only
    raise RuntimeError for actual failures (model not loaded, corrupt
    image bytes).
    """
    if _reader is None:
        raise RuntimeError(
            "OCR engine failed to load when the server started. Restart "
            "the backend and check the startup logs for the EasyOCR "
            "error — it's almost always either (1) no internet on first "
            "run, since EasyOCR downloads its model weights the first "
            "time it's used, or (2) a broken PyTorch install."
        )

    try:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_array = np.array(pil_image)

        # WHY grayscale conversion (and nothing more elaborate):
        # A quick grayscale pass measurably improves EasyOCR's accuracy
        # on typical phone-camera plate photos (uneven lighting, glare)
        # without building a full OpenCV preprocessing pipeline — the
        # project brief explicitly drops "standalone OpenCV" as a
        # dependency to build custom vision pipelines around, but using
        # cv2 for this one conversion call is just image I/O, not that.
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)

        results = _reader.readtext(gray, detail=1)
        # results is a list of (bounding_box, text, confidence) tuples.

        if not results:
            return {
                "success": False,
                "plate_number": None,
                "confidence": 0.0,
                "raw_detections": [],
                "message": "No text detected in image. Ask the attendant "
                           "to retake the photo with the plate centered, "
                           "in focus, and well-lit.",
            }

        fragments = [text for (_bbox, text, _conf) in results]
        avg_confidence = sum(conf for (_b, _t, conf) in results) / len(results)
        plate_guess = _clean_plate_text(fragments)

        return {
            "success": plate_guess is not None,
            "plate_number": plate_guess,
            "confidence": round(avg_confidence, 3),
            "raw_detections": fragments,
            "message": (
                "Plate read successfully. Attendant should still verify "
                "before confirming entry." if plate_guess else
                "Text was detected but didn't match a valid plate "
                "pattern — attendant must enter the number manually."
            ),
        }

    except Exception as exc:
        logger.error(f"OCR processing failed: {exc}")
        raise RuntimeError(
            f"Could not process the uploaded image: {exc}. Ensure the "
            "file is a valid, non-corrupted JPEG or PNG photo."
        ) from exc