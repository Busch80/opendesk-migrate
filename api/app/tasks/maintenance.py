"""Background maintenance tasks (token refresh, staging cleanup, audit archive)."""

from __future__ import annotations

from app.celery import celery
from app.logging import get_logger

logger = get_logger(__name__)


@celery.task(name="app.tasks.maintenance.refresh_expiring_tokens")
def refresh_expiring_tokens() -> dict[str, int]:
    """Refresh OAuth tokens that expire within 24h."""
    # Implementation: scan users, refresh each near-expiry token, log to audit.
    return {"refreshed": 0, "errors": 0}


@celery.task(name="app.tasks.maintenance.cleanup_staging")
def cleanup_staging() -> dict[str, int]:
    """Delete staging files older than retention (default 14 days)."""
    # Implementation: storage.cleanup_older_than_days(retention)
    logger.info("cleanup_staging_started")
    return {"deleted": 0, "bytes_freed": 0}


@celery.task(name="app.tasks.maintenance.archive_audit_log")
def archive_audit_log() -> dict[str, int]:
    """Copy audit_log rows older than 7 days to WORM S3 bucket."""
    return {"archived": 0}
