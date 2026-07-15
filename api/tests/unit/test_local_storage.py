"""Unit tests for LocalVolumeBackend storage."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.services.storage import LocalVolumeBackend
from app.services.storage.base import StorageQuotaExceeded


@pytest.fixture
def tmp_backend(tmp_path: Path):
    backend = LocalVolumeBackend(base_path=str(tmp_path), max_bytes=10 * 1024 * 1024, retention_days=1)
    return backend


@pytest.mark.asyncio
async def test_put_and_get(tmp_backend: LocalVolumeBackend) -> None:
    etag = await tmp_backend.put("tenant_a/job_1/file.txt", b"hello")
    assert etag
    chunks = []
    async for chunk in tmp_backend.get("tenant_a/job_1/file.txt"):
        chunks.append(chunk)
    assert b"".join(chunks) == b"hello"


@pytest.mark.asyncio
async def test_list_prefix(tmp_backend: LocalVolumeBackend) -> None:
    await tmp_backend.put("a/1.txt", b"x")
    await tmp_backend.put("a/b/2.txt", b"y")
    await tmp_backend.put("c/3.txt", b"z")

    objs = await tmp_backend.list_prefix("a")
    assert {o.key for o in objs} == {"a/1.txt", "a/b/2.txt"}


@pytest.mark.asyncio
async def test_delete_prefix(tmp_backend: LocalVolumeBackend) -> None:
    await tmp_backend.put("a/1.txt", b"x")
    await tmp_backend.put("a/b/2.txt", b"y")
    n = await tmp_backend.delete_prefix("a")
    assert n == 2
    assert await tmp_backend.usage_bytes() == 0


@pytest.mark.asyncio
async def test_quota_enforced(tmp_backend: LocalVolumeBackend) -> None:
    await tmp_backend.put("big.bin", b"x" * (9 * 1024 * 1024))  # 9 MB
    with pytest.raises(StorageQuotaExceeded):
        await tmp_backend.put("alsobig.bin", b"x" * (5 * 1024 * 1024))  # would overflow


@pytest.mark.asyncio
async def test_path_traversal_rejected(tmp_backend: LocalVolumeBackend) -> None:
    with pytest.raises(ValueError):
        await tmp_backend.put("../etc/passwd", b"x")
    with pytest.raises(ValueError):
        await tmp_backend.put("/etc/passwd", b"x")


@pytest.mark.asyncio
async def test_cleanup_older_than_days(tmp_path: Path) -> None:
    import os
    import time

    backend = LocalVolumeBackend(base_path=str(tmp_path), max_bytes=10 * 1024 * 1024, retention_days=0)
    f = tmp_path / "old.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"old")
    # set mtime to 2 days ago
    old_time = time.time() - 2 * 86400
    os.utime(f, (old_time, old_time))

    n = await backend.cleanup_older_than_days(1)
    assert n == 1
    assert not f.exists()


@pytest.mark.asyncio
async def test_etag_stable(tmp_backend: LocalVolumeBackend) -> None:
    e1 = await tmp_backend.put("k", b"hello")
    e2 = await tmp_backend.put("k", b"hello")
    assert e1 == e2
