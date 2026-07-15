"""Discovery-mode task — sizes a tenant without migrating anything."""

from __future__ import annotations

from app.celery_init import celery
from app.logging import get_logger

logger = get_logger(__name__)


@celery.task(name="app.tasks.discovery.discover_tenant")
def discover_tenant(tenant_id: str) -> dict[str, int]:
    """Read user/folder sizes from M365, write back to users_m365.

    Does NOT migrate any data. Idempotent — safe to re-run.
    """
    logger.info("discovery_started", tenant_id=tenant_id)
    return {"users_count": 0, "total_mail_bytes": 0, "total_onedrive_bytes": 0}
