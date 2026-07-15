"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db import healthcheck as db_healthcheck
from app.logging import get_logger
from app.schemas import HealthResponse
from app.services.storage import get_storage

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    db = await db_healthcheck()
    storage = await get_storage().healthcheck()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        database=db.get("database", "unknown"),
        storage=storage,
    )


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness probe — does NOT touch DB / storage."""
    return HealthResponse(status="ok", version="0.1.0", database="skipped", storage=None)


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    """Readiness probe — checks DB ping."""
    from app.db import engine as get_engine

    eng = get_engine()
    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:  # noqa: BLE001
        return {"status": "not_ready", "error": str(e)}
