"""Local volume storage backend.

Uses a directory on the host filesystem (named Docker volume mounted to all
workers). Designed for single-host Coolify deployments where all worker
replicas share the same path.

Files are laid out:
    {base_path}/{tenant_id}/{job_id}/{relative_key}

Each top-level tenant dir is independently gc-able. Quota is enforced at
write time (best-effort), with periodic cleanup of old files.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.logging import get_logger
from app.services.storage.base import (
    StorageBackend,
    StorageQuotaExceeded,
    StoredObject,
)

logger = get_logger(__name__)


def _sha256_etag(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


@dataclass
class LocalVolumeBackend(StorageBackend):
    """Local filesystem storage backend."""

    base_path: str
    max_bytes: int = 500 * 1024**3  # 500 GB default
    retention_days: int = 14

    def __post_init__(self) -> None:
        self._base = Path(self.base_path).resolve()
        self._base.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _resolve_key(self, key: str) -> Path:
        """Safely resolve a key to a path under base."""
        if ".." in key or key.startswith("/"):
            raise ValueError(f"Invalid key: {key!r}")
        path = (self._base / key).resolve()
        if not str(path).startswith(str(self._base)):
            raise ValueError(f"Key escapes base directory: {key!r}")
        return path

    async def put(self, key: str, data: bytes | AsyncIterator[bytes]) -> str:
        target = self._resolve_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        # For bytes input we can predict size and check pre-flight quota.
        # For streaming input we check after accumulation (best-effort).
        predicted_size: int | None = None
        if isinstance(data, bytes):
            predicted_size = len(data)

        async with self._lock:
            current = await self.usage_bytes_locked()
            if predicted_size is not None and current + predicted_size > self.max_bytes:
                raise StorageQuotaExceeded(
                    f"Staging quota exceeded: would be "
                    f"{(current + predicted_size) / 1024**3:.1f} GB / "
                    f"{self.max_bytes / 1024**3:.1f} GB"
                )

            if isinstance(data, bytes):
                etag = _sha256_etag(data)
                tmp = target.with_suffix(target.suffix + ".tmp")
                tmp.write_bytes(data)
                os.replace(tmp, target)
                return etag

            # Stream write — read fully first since we don't have a true streaming interface yet.
            chunks = [chunk async for chunk in data]
            buf = b"".join(chunks)
            current = await self.usage_bytes_locked()
            if current + len(buf) > self.max_bytes:
                raise StorageQuotaExceeded(
                    f"Staging quota exceeded after stream: "
                    f"{(current + len(buf)) / 1024**3:.1f} GB / {self.max_bytes / 1024**3:.1f} GB"
                )
            etag = _sha256_etag(buf)
            tmp = target.with_suffix(target.suffix + ".tmp")
            with tmp.open("wb") as f:
                f.write(buf)
            os.replace(tmp, target)
            return etag

    async def get(self, key: str) -> AsyncIterator[bytes]:
        """Stream object content.

        Returns an async iterator (because this is an async generator, not a
        regular coroutine — callers should `async for chunk in backend.get(...)`).
        """
        path = self._resolve_key(key)

        if not path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        loop = asyncio.get_running_loop()

        # We need to pre-check existence before yielding — ensure async iterator
        if not await loop.run_in_executor(None, path.exists):
            raise FileNotFoundError(f"Key not found: {key}")

        with open(path, "rb") as f:
            while True:
                chunk = await loop.run_in_executor(None, f.read, 1024 * 256)
                if not chunk:
                    break
                yield chunk

    async def exists(self, key: str) -> bool:
        try:
            return self._resolve_key(key).exists()
        except ValueError:
            return False

    async def delete(self, key: str) -> bool:
        try:
            path = self._resolve_key(key)
        except ValueError:
            return False
        if path.exists() and path.is_file():
            try:
                path.unlink()
                return True
            except OSError as e:
                logger.warning("delete_failed", key=key, error=str(e))
        return False

    async def delete_prefix(self, prefix: str) -> int:
        try:
            base = self._resolve_key(prefix)
        except ValueError:
            return 0
        if not base.exists():
            return 0
        if base.is_file():
            base.unlink()
            return 1
        # Directory delete
        count = sum(1 for _ in base.rglob("*") if _.is_file())
        shutil.rmtree(base, ignore_errors=True)
        return count

    async def list_prefix(self, prefix: str) -> list[StoredObject]:
        try:
            base = self._resolve_key(prefix)
        except ValueError:
            return []
        if not base.exists():
            return []
        objects: list[StoredObject] = []
        if base.is_file():
            stat = base.stat()
            objects.append(
                StoredObject(
                    key=str(base.relative_to(self._base)),
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                )
            )
            return objects
        for path in base.rglob("*"):
            if path.is_file():
                stat = path.stat()
                objects.append(
                    StoredObject(
                        key=str(path.relative_to(self._base)),
                        size_bytes=stat.st_size,
                        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    )
                )
        return objects

    async def usage_bytes(self) -> int:
        async with self._lock:
            return await self.usage_bytes_locked()

    async def usage_bytes_locked(self) -> int:
        if not self._base.exists():
            return 0
        total = 0
        for path in self._base.rglob("*"):
            if path.is_file() and not path.name.endswith(".tmp"):
                try:
                    total += path.stat().st_size
                except OSError:
                    pass
        return total

    async def cleanup_older_than_days(self, days: int) -> int:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        if not self._base.exists():
            return 0
        deleted = 0
        for path in self._base.rglob("*"):
            if not path.is_file() or path.name.endswith(".tmp"):
                continue
            try:
                stat = path.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    path.unlink()
                    deleted += 1
            except OSError:
                continue
        # Cleanup empty dirs
        for path in sorted(self._base.rglob("*"), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()  # only removes if empty
                except OSError:
                    pass
        return deleted

    async def healthcheck(self) -> dict[str, Any]:
        result = await super().healthcheck()
        result["base_path"] = str(self._base)
        result["max_bytes"] = self.max_bytes
        result["retention_days"] = self.retention_days
        return result
