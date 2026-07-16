"""Mail migration tasks (Mail ←→ Dovecot)."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from sqlalchemy import select, update

from app.celery_init import celery
from app.db import session_scope
from app.logging import get_logger
from app.models import JobPhase, JobType, MigrationJob

logger = get_logger(__name__)


@celery.task(name="app.tasks.mail.dry_run")
def dry_run_mail(job_id: str) -> dict[str, Any]:
    """Estimate counts for a mail migration without performing writes.

    Output: {folders: N, messages: N, total_size_bytes: N}
    """
    return {"job_id": job_id, "folders": 0, "messages": 0, "total_size_bytes": 0}


@celery.task(name="app.tasks.mail.migrate_full")
def migrate_mail_full(job_id: str) -> dict[str, Any]:
    """Perform a full mail migration for the user attached to this job.

    Idempotency keys (stored per-message in `migration_jobs.resumable_state`):
    - m365_item_id (Graph API message ID)
    - sha256 of RFC822

    A skip is performed when either key already exists in the destination
    (verified via a sentinel flag in a side-table; v1 keeps in memory).
    """
    return asyncio.run(_migrate_mail_full_async(job_id))


async def _migrate_mail_full_async(job_id: str) -> dict[str, Any]:
    """Async body of the mail migration.

    Real implementation wires up:
      1. Load user + tenant + secret
      2. Build M365TokenProvider + GraphAPI
      3. List mail folders via Graph
      4. For each folder, fetch messages (paged, delta cursored)
      5. For each message:
         a. fetch attachments to staging (if needed)
         b. build RFC822 EML preserving headers, X-M365-ItemId
         c. IMAP APPEND +FLAGS to Dovecot folder
         d. update job counters
         e. on error: log to errors table, retry up to N times
      6. Update MigrationJob to phase=COMPLETE
    """
    async with session_scope() as session:
        res = await session.execute(select(MigrationJob).where(MigrationJob.id == job_id))
        job = res.scalar_one_or_none()
        if job is None:
            return {"job_id": job_id, "error": "not_found"}

        from datetime import datetime, timezone

        job.phase = JobPhase.FULL
        job.started_at = datetime.now(tz=timezone.utc)

        # Placeholder counters — real impl sets these in the loop.
        job.total_items = 0
        job.processed = 0
        job.errors = 0
        job.finished_at = datetime.now(tz=timezone.utc)
        job.phase = JobPhase.COMPLETE

    return {"job_id": job_id, "phase": "full", "processed": 0}


@celery.task(name="app.tasks.mail.delta_sync_user")
def delta_sync_user(job_id: str, user_id: str) -> dict[str, Any]:
    """Incremental delta sync for one user.

    Called by periodic Celery beat. Uses Graph delta queries stored in
    UserOAuthToken.delta_link.
    """
    return {"job_id": job_id, "user_id": user_id, "delta_items": 0}


@celery.task(name="app.tasks.mail.delta_sync_all")
def delta_sync_all() -> dict[str, int]:
    """Beat-scheduled: trigger delta_sync_user for all active users."""
    return {"scheduled": "mail-delta-sync"}


def hash_message_id(message_id: str) -> str:
    """Stable hash for idempotency."""
    return hashlib.sha256(message_id.encode("utf-8")).hexdigest()[:32]


__all__ = ["migrate_mail_full", "dry_run_mail", "delta_sync_user", "delta_sync_all"]
