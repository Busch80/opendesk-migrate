"""Unit tests for the Graph rate limiter token-bucket math."""

from __future__ import annotations

import asyncio
import time

import fakeredis.aioredis as fakeredis
import pytest

from app.services.m365.client import GraphRateLimiter


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=False)


@pytest.mark.asyncio
async def test_initial_acquire_uses_capacity(redis) -> None:
    rl = GraphRateLimiter(redis, key="tenant_a:m365", capacity=10, refill_per_sec=1.0)
    # Should never block when bucket is at capacity
    t0 = time.monotonic()
    for _ in range(10):
        await rl.acquire()
    elapsed = time.monotonic() - t0
    assert elapsed < 0.5


@pytest.mark.asyncio
async def test_blocks_when_empty(redis) -> None:
    rl = GraphRateLimiter(redis, key="tenant_b:m365", capacity=2, refill_per_sec=5.0)
    await rl.acquire()
    await rl.acquire()
    t0 = time.monotonic()
    await rl.acquire()  # should sleep ~0.2s
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.15
