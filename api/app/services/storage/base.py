"""Storage backend interface.

Used for staging large files during migration. Implementations must support
idempotent writes (same key overwritten = same result), prefix-based listing
for cleanup, and a usage-based quota.

Streams are typed as AsyncIterator[bytes] to allow the local backend to
stream from disk without buffering entire files in memory.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class StoredObject:
    """Metadata for a stored object."""

    key: str
    size_bytes: int
    modified_at: datetime
    etag: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at.isoformat(),
            "etag": self.etag,
        }


class StorageQuotaExceeded(Exception):
    """Raised when the configured quota is exceeded."""


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    async def put(self, key: str, data: bytes | AsyncIterator[bytes]) -> str:
        """Store object under key. Returns etag (or empty string)."""
        ...

    @abstractmethod
    def get(self, key: str) -> AsyncIterator[bytes]:
        """Stream object content (must be an async generator)."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a single object. Returns True if deleted."""
        ...

    @abstractmethod
    async def delete_prefix(self, prefix: str) -> int:
        """Delete all objects under a prefix. Returns count deleted."""
        ...

    @abstractmethod
    async def list_prefix(self, prefix: str) -> list[StoredObject]:
        """List all objects under a prefix (non-recursive)."""
        ...

    @abstractmethod
    async def usage_bytes(self) -> int:
        """Total bytes currently stored."""
        ...

    @abstractmethod
    async def cleanup_older_than_days(self, days: int) -> int:
        """Delete all objects older than `days` days. Returns count."""
        ...

    async def healthcheck(self) -> dict[str, Any]:
        """Check backend connectivity."""
        usage = await self.usage_bytes()
        return {"backend": self.__class__.__name__, "usage_bytes": usage, "checked_at": datetime.now(tz=timezone.utc).isoformat()}


__all__ = ["StorageBackend", "StorageQuotaExceeded", "StoredObject"]
