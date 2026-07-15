"""Celery application — separate module to avoid circular imports.

Worker entrypoint:
    cd api/ && celery -A app.celery_boot:celery worker -Q mail -l info

Beat entrypoint:
    celery -A app.celery_boot:celery beat -l info
"""

from __future__ import annotations

from celery import Celery
from kombu import Queue

from app.config import get_settings

_settings = get_settings()

celery = Celery(
    "odmig",
    broker=_settings.redis_url,
    backend=_settings.redis_result_backend,
    include=[
        "app.tasks.discovery",
        "app.tasks.mail",
        "app.tasks.calendar",
        "app.tasks.contacts",
        "app.tasks.onedrive",
        "app.tasks.maintenance",
        "app.tasks.dispatch",
    ],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=500,
    task_time_limit=_settings.celery_task_time_limit,
    task_soft_time_limit=_settings.celery_task_time_limit - 60,
    task_default_queue="default",
    task_create_missing_queues=True,
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("mail", routing_key="mail"),
        Queue("calendar", routing_key="calendar"),
        Queue("contacts", routing_key="contacts"),
        Queue("onedrive", routing_key="onedrive"),
        Queue("maintenance", routing_key="maintenance"),
    ),
    task_routes={
        "app.tasks.mail.*": {"queue": "mail"},
        "app.tasks.calendar.*": {"queue": "calendar"},
        "app.tasks.contacts.*": {"queue": "contacts"},
        "app.tasks.onedrive.*": {"queue": "onedrive"},
        "app.tasks.maintenance.*": {"queue": "maintenance"},
        "app.tasks.dispatch.*": {"queue": "default"},
        "app.tasks.discovery.*": {"queue": "default"},
    },
    beat_schedule={
        "refresh-expiring-tokens": {
            "task": "app.tasks.maintenance.refresh_expiring_tokens",
            "schedule": 30 * 60.0,
        },
        "delta-sync-mail": {
            "task": "app.tasks.mail.delta_sync_all",
            "schedule": 15 * 60.0,
        },
        "delta-sync-calendar": {
            "task": "app.tasks.calendar.delta_sync_all",
            "schedule": 15 * 60.0,
        },
        "delta-sync-contacts": {
            "task": "app.tasks.contacts.delta_sync_all",
            "schedule": 30 * 60.0,
        },
        "cleanup-staging": {
            "task": "app.tasks.maintenance.cleanup_staging",
            "schedule": 6 * 60 * 60.0,
        },
        "archive-audit-log": {
            "task": "app.tasks.maintenance.archive_audit_log",
            "schedule": 24 * 60 * 60.0,
        },
    },
)

__all__ = ["celery"]
