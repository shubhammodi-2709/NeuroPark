"""
services/qr_service.py — QR ticket generation.

WHY the QR code encodes ONLY a UUID token, never vehicle details:
Project constraint #4 — "QR token = UUID only. App fetches all details
using this token." This keeps a printed/displayed ticket meaningless by
itself (no plate number, no lot name visible to whoever picks up a
dropped ticket), and means the server is always the single source of
truth looked up fresh at exit time via /vehicles/exit.
"""

import io
import base64
import uuid
import logging

import qrcode

logger = logging.getLogger("neuropark.qr")


def generate_qr_token() -> str:
    """
    Generates a new random UUID to serve as this ticket's QR token.

    WHY uuid4 (random) rather than a sequential ID or uuid1 (time+MAC
    based): uuid4 has no predictable structure, so nobody can guess
    other active tickets' tokens by incrementing a number. This matters
    because /vehicles/exit (Week 2.1) will trust this token to look up
    and mutate a specific vehicle record.
    """
    return str(uuid.uuid4())


def generate_qr_image_base64(token: str) -> str:
    """
    Renders the token as a QR code PNG and returns it as a base64 data
    URI string — ready to drop straight into an <img src="..."> tag on
    the Attendant PWA. We return base64 instead of saving a file to
    disk because these tickets are only useful for a few hours (one
    parking visit) and don't need permanent file storage or a static
    file server.
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            # WHY ERROR_CORRECT_M (~15% recoverable) instead of L (~7%)
            # or H (~30%): printed tickets get creased, smudged, or
            # partially covered by a thumb during scanning. M survives
            # typical real-world damage without making the QR modules
            # unnecessarily dense/small the way H would.
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return f"data:image/png;base64,{encoded}"

    except Exception as exc:
        logger.error(f"QR image generation failed for token {token}: {exc}")
        raise RuntimeError(
            f"Failed to generate QR code image: {exc}. This shouldn't "
            "depend on user input — check that 'qrcode[pil]' (not just "
            "'qrcode') is installed, since Pillow is required to render "
            "the image."
        ) from exc