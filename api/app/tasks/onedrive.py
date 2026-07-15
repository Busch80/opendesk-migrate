"""OneDrive → Nextcloud migration tasks."""

from __future__ import annotations

from app.celery import celery


@celery.task(name="app.tasks.onedrive.migrate_full")
def migrate_onedrive_full(job_id: str) -> dict[str, int]:
    """Full OneDrive migration.

    Real impl:
      1. Graph /me/drive/root/children (tree walk)
      2. For each file:
         - size < 2 GB: stream download → WebDAV PUT
         - size >= 2 GB or interrupted: /staging/{tenant}/{job}/path → WebDAV PUT
      3. Permissions: Graph /items/{id}/permissions re-set on Nextcloud shares
      4. Versionen: /items/{id}/versions → WebDAV VERSION
      5. Sharing links: warning-only (M365 links become invalid; user must relink)
    """
    return {"job_id": job_id, "files": 0, "errors": 0, "total_bytes": 0}


@celery.task(name="app.tasks.onedrive.migrate_delta")
def migrate_onedrive_delta(job_id: str) -> dict[str, int]:
    return {"job_id": job_id, "delta_files": 0}
