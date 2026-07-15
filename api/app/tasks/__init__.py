"""Celery tasks for the opendesk-migrate migration engine.

Importable via app.tasks — each module exposes a Celery task (or set of tasks)
registered against the central app.celery_init.celery application.

Auto-loaded by Celery's `include` mechanism (see celery_init.celery.conf).

Modules:
    discovery        — pre-migration sizing (no data writes)
    mail             — M365 mail → Dovecot/IMAP APPEND
    calendar         — M365 calendar → OX App Suite
    contacts         — M365 contacts → OX App Suite
    onedrive         — OneDrive → Nextcloud via WebDAV
    dispatch         — routes a Job ID to the correct per-type task
    maintenance      — token refresh, staging cleanup, audit archive
"""

from __future__ import annotations

# Tasks are accessed by name (e.g. "app.tasks.mail.migrate_full") via
# celery_app.send_task() — explicit imports are not required at this layer.
__all__: list[str] = []
