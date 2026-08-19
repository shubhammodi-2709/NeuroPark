"""
main.py — NeuroPark Backend Entry Point

FastAPI needs a single ASGI app instance that ties together all routes,
middleware, and startup/shutdown lifecycle hooks (like connecting to
MongoDB once when the server boots, instead of reconnecting on every
request — see the lifespan() function below for why this matters).

Run with: python -m uvicorn main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from routes import vehicles

# ----------------------------------------------------------------------
# Logging setup
# WHY: debugging EasyOCR / MongoDB Atlas connection issues is much
# easier with timestamps and severity levels than bare print() calls —
# especially once this runs headless during a demo.
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("neuropark")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    WHY a lifespan handler instead of connecting inside each route:
    Opening a new MongoDB TCP connection on every request would be slow
    and would quickly exhaust MongoDB Atlas's free-tier connection
    limit. We open ONE client when the server starts and reuse it for
    the whole process lifetime — this is the pattern Motor (the async
    MongoDB driver) is built around, and it also lets us fail fast at
    startup instead of on some unlucky user's first request.
    """
    logger.info("Starting NeuroPark backend...")

    if not settings.MONGODB_URI:
        logger.error("MONGODB_URI is not set. Check your .env file.")
        raise RuntimeError(
            "MONGODB_URI is missing. NeuroPark cannot start without a "
            "database connection. Check that .env exists at the project "
            "root (neuropark/.env) or inside backend/, and contains "
            "MONGODB_URI."
        )

    try:
        app.state.mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,  # fail fast instead of hanging forever
        )
        # Force a round-trip now to confirm Atlas is actually reachable,
        # rather than discovering a bad URI/whitelist on the first
        # real request from the PWA.
        await app.state.mongo_client.admin.command("ping")
        app.state.db = app.state.mongo_client.get_default_database()
        logger.info(f"MongoDB connected — database: '{app.state.db.name}'")
    except Exception as exc:
        logger.error(f"MongoDB connection failed: {exc}")
        raise RuntimeError(
            "Could not connect to MongoDB Atlas. Check that: "
            "(1) MONGODB_URI in .env is correct and the password has no "
            "unescaped special characters, "
            "(2) your current IP is whitelisted in Atlas → Network Access, "
            "(3) the free-tier cluster isn't paused."
        ) from exc

    yield  # ---- app serves requests here ----

    logger.info("Shutting down NeuroPark backend...")
    app.state.mongo_client.close()


app = FastAPI(
    title="NeuroPark API",
    description="Event-driven smart parking backend — DB writes only at vehicle entry/exit.",
    version="0.1.0",
    lifespan=lifespan,
)

# ----------------------------------------------------------------------
# CORS
# WHY: the Attendant PWA and User App run on different origins (separate
# Vite dev server ports now, separate deployed domains later) than this
# API. Without CORS enabled, the browser blocks every fetch() call from
# those apps before it even reaches FastAPI.
#
# allow_origins=["*"] is intentionally permissive for local development
# only — tighten this to your actual PWA/app domains before any real
# deployment (flagged again at Week 7 full-system testing).
# ----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount OCR + QR endpoints. No prefix here because the brief specifies
# the exact paths POST /ocr/read-plate and POST /qr/generate (not
# nested under /vehicles) — /vehicles/entry and /vehicles/exit will be
# added to this same router in Weeks 1.2 and 2.1.
app.include_router(vehicles.router, tags=["vehicles"])


@app.get("/")
async def root():
    """Liveness check — hit this first to confirm the server process is up."""
    return {
        "service": "NeuroPark API",
        "status": "running",
        "week": "1.1 — OCR + QR + MongoDB foundation",
    }


@app.get("/health")
async def health():
    """
    WHY a separate /health endpoint from '/':
    '/' only proves FastAPI itself is running. '/health' proves the
    MongoDB connection made at startup is still alive — useful when
    debugging Atlas IP-whitelist expiry or a paused free-tier cluster
    without digging through terminal logs.
    """
    try:
        await app.state.mongo_client.admin.command("ping")
        mongo_status = "ok"
    except Exception as exc:
        logger.warning(f"Health check MongoDB ping failed: {exc}")
        mongo_status = "unreachable"

    return {
        "api": "ok",
        "mongodb": mongo_status,
    }