"""
config.py — Centralized environment variable loading.

WHY this file exists instead of scattering os.getenv() calls everywhere:
1. Single place to see every environment variable the backend depends on.
2. Fails loudly (via warnings/errors) if something critical is missing,
   instead of crashing deep inside a request handler with a confusing
   traceback that's hard to trace back to ".env wasn't loaded".
3. Every other module imports `settings` from here instead of reading
   the .env file directly — one source of truth, one place to add a
   new variable when Week 2+ needs it (e.g. GOOGLE_MAPS_API_KEY usage).
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("neuropark.config")

# ----------------------------------------------------------------------
# WHY we check TWO locations for .env:
# The project brief's folder structure puts .env at neuropark/.env
# (project root, one level above backend/). But it's a common mistake
# to accidentally create it inside backend/ instead — and that mistake
# produces a confusing "MONGODB_URI is empty" error with no clue why.
# Checking both locations means the backend works either way, and we
# log which one we used so it's never a mystery.
# ----------------------------------------------------------------------
_ROOT_ENV = Path(__file__).resolve().parent.parent / ".env"
_LOCAL_ENV = Path(__file__).resolve().parent / ".env"

if _ROOT_ENV.exists():
    load_dotenv(dotenv_path=_ROOT_ENV)
    logger.info(f"Loaded .env from project root: {_ROOT_ENV}")
elif _LOCAL_ENV.exists():
    load_dotenv(dotenv_path=_LOCAL_ENV)
    logger.info(f"Loaded .env from backend/: {_LOCAL_ENV}")
else:
    logger.warning(
        "No .env file found at project root or backend/. "
        "Falling back to system environment variables (if any)."
    )


class Settings:
    """
    WHY a class instead of loose module-level variables:
    lets us validate + log which vars are missing in one place, and
    gives editor autocomplete when other files do
    `from config import settings; settings.MONGODB_URI`.
    """

    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")

    # Business-logic constants from the project brief live here (not
    # hardcoded inside routing_service.py later) so they can be tuned
    # in one place without touching logic — matches constraint #5
    # (walk-in buffer) and the rerouting algorithm spec.
    WALK_IN_BUFFER: float = 0.30
    REROUTE_THRESHOLD: float = 0.80
    REROUTE_DISTANCE_MIN_METERS: int = 1000

    def warn_if_missing(self) -> None:
        """Called once at import time below — surfaces config problems
        the moment the server starts, not on the first request that hits them."""
        required = {
            "MONGODB_URI": self.MONGODB_URI,
            "SECRET_KEY": self.SECRET_KEY,
        }
        for name, value in required.items():
            if not value:
                logger.warning(
                    f"{name} is not set in .env — endpoints depending on "
                    f"it will fail until this is fixed."
                )

        if not self.GOOGLE_MAPS_API_KEY:
            # Not fatal for Week 1.1 (OCR/QR don't touch Maps), but flag
            # it since the brief notes a teammate is still adding it.
            logger.info(
                "GOOGLE_MAPS_API_KEY is not set yet — fine for Week 1.1, "
                "but required before Week 3.2 (User App Maps integration)."
            )


settings = Settings()
settings.warn_if_missing()