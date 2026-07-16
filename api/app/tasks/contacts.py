"""Contacts migration tasks."""

from __future__ import annotations

from app.celery_init import celery


@celery.task(name="app.tasks.contacts.migrate_full")
def migrate_contacts_full(job_id: str) -> dict[str, int]:
    """Full contacts migration.

    Real impl:
      - Graph /me/contacts (delta)
      - For each contact: serialize to vCard 3.0
      - POST to OX JSON API
    """
    return {"job_id": job_id, "contacts": 0, "errors": 0}


@celery.task(name="app.tasks.contacts.delta_sync_all")
def delta_sync_all() -> dict[str, str]:
    return {"scheduled": "contacts-delta-sync"}
