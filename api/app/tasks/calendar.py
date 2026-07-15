"""Calendar migration tasks (Calendar ←→ OX App Suite)."""

from __future__ import annotations

from app.celery import celery


@celery.task(name="app.tasks.calendar.migrate_full")
def migrate_calendar_full(job_id: str) -> dict[str, int]:
    """Full calendar migration.

    Real impl:
      - Graph delta query /events
      - For each event: serialize to iCal (RRULE 1:1, VALARM preserved)
      - POST to OX JSON API for calendar event creation
      - Track retries per event ID
    """
    return {"job_id": job_id, "events": 0, "errors": 0}


@celery.task(name="app.tasks.calendar.delta_sync_all")
def delta_sync_all() -> dict[str, str]:
    return {"scheduled": "calendar-delta-sync"}
