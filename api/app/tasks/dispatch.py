"""Job dispatch — routes a job_id to the correct Celery task per type."""

from __future__ import annotations

from sqlalchemy import select

from app.celery_init import celery
from app.db import session_scope
from app.logging import get_logger
from app.models import JobType, MigrationJob

logger = get_logger(__name__)


@celery.task(name="app.tasks.dispatch.dispatch_job")
def dispatch_job(job_id: str) -> None:
    """Top-level dispatcher: pick the right per-type task.

    Real impl: load job, look at job_type, spawn the matching task.
    Uses Celery's `delay()` (so this returns immediately).
    """
    import asyncio

    async def _decide() -> JobType | None:
        async with session_scope() as session:
            res = await session.execute(select(MigrationJob).where(MigrationJob.id == job_id))
            j = res.scalar_one_or_none()
            return j.job_type if j else None

    job_type = asyncio.run(_decide())
    if job_type is None:
        logger.warning("dispatch_unknown_job", job_id=job_id)
        return

    task_map = {
        JobType.MAIL: "app.tasks.mail.migrate_full",
        JobType.CALENDAR: "app.tasks.calendar.migrate_full",
        JobType.CONTACTS: "app.tasks.contacts.migrate_full",
        JobType.ONEDRIVE: "app.tasks.onedrive.migrate_full",
    }
    target = task_map.get(job_type)
    if target is None:
        return
    celery.send_task(target, args=[job_id])


__all__ = ["dispatch_job"]
