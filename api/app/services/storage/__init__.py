"""Storage backend abstraction.

Two implementations: LocalVolume (named Docker volume, default) and
S3Backend (SeaweedFS/MinIO, future when multi-host Coolify scaling).

The backend is selected via STORAGE_BACKEND env var. Default to LocalVolume
since the project runs on single-host Coolify with shared Docker volumes.
"""

from __future__ import annotations

from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalVolumeBackend

__all__ = ["StorageBackend", "LocalVolumeBackend", "get_storage"]


def get_storage() -> StorageBackend:
    """Factory returning the configured storage backend."""
    from app.config import get_settings

    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalVolumeBackend(
            base_path=settings.staging_path,
            max_bytes=settings.staging_max_gb * 1024**3,
            retention_days=settings.staging_retention_days,
        )
    if settings.storage_backend == "s3":
        from app.services.storage.s3 import S3Backend

        return S3Backend()
    raise ValueError(f"Unknown storage_backend: {settings.storage_backend}")
