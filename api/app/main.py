"""FastAPI application factory and entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings
from app.db import init_engine
from app.logging import get_logger, setup_logging
from app.routers import health, jobs, tenants, users, oauth, errors, audit
from app.services.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    logger = get_logger("odmig.startup")
    logger.info("startup_begin", env=settings.app_env, version=app.version)

    init_engine()
    storage = get_storage()
    await storage.healthcheck()

    logger.info("startup_complete", storage=storage.__class__.__name__)
    yield
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    app = FastAPI(
        title="opendesk-migrate",
        version="0.1.0",
        description="Multi-tenant migration tool: M365 → openDesk (Mail, Calendar, Contacts, OneDrive)",
        lifespan=lifespan,
        debug=settings.app_debug,
    )

    # Routers
    app.include_router(health.router)
    app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
    app.include_router(users.router, prefix="/api/v1", tags=["users"])
    app.include_router(oauth.router, prefix="/api/v1/oauth", tags=["oauth"])
    app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
    app.include_router(errors.router, prefix="/api/v1/errors", tags=["errors"])
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])

    # Prometheus instrumentation
    if settings.prometheus_enabled:
        try:
            Instrumentator(
                excluded_handlers=["/metrics", "/health", "/healthz"],
                inprogress_labels=True,
            ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        except TypeError:
            # Older signature
            Instrumentator(excluded_handlers=["/metrics", "/health", "/healthz"]).instrument(app).expose(
                app, endpoint="/metrics", include_in_schema=False
            )

    return app


app = create_app()


__all__ = ["app", "create_app"]
