"""S3-compatible storage backend (SeaweedFS / MinIO).

Drop-in replacement for LocalVolumeBackend. Same interface, drops to
`aioboto3` for async operations. Activation: STORAGE_BACKEND=s3 +
S3_* environment variables.

Currently a skeleton — implementation lands when the project migrates
to multi-host Coolify. Keeping the import surface stable so the switch is
a config change, not a code change.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.services.storage.base import StorageBackend, StoredObject


class S3Backend(StorageBackend):
    """S3-compatible storage backend (TODO: implement)."""

    def __init__(self) -> None:
        raise NotImplementedError(
            "S3Backend will be implemented when scaling beyond single-host. "
            "Run with STORAGE_BACKEND=local for now."
        )

    async def put(self, key: str, data: bytes | AsyncIterator[bytes]) -> str:
        raise NotImplementedError

    async def get(self, key: str) -> AsyncIterator[bytes]:
        raise NotImplementedError  # pragma: no cover
        if False:  # pragma: no cover
            yield b""

    async def exists(self, key: str) -> bool:
        return False

    async def delete(self, key: str) -> bool:
        return False

    async def delete_prefix(self, prefix: str) -> int:
        return 0

    async def list_prefix(self, prefix: str) -> list[StoredObject]:
        return []

    async def usage_bytes(self) -> int:
        return 0

    async def cleanup_older_than_days(self, days: int) -> int:
        return 0
