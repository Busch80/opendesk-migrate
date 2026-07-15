"""Microsoft Graph API client.

Thin wrapper around httpx that handles:
- Per-user OAuth token refresh via MSAL
- Rate limiting via Redis-backed semaphore
- Retry with exponential backoff on 429/503
- Delta-query cursor management

This module does NOT perform migrations — it just calls the Graph API on
behalf of a user. Migration logic lives in app/tasks/.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import get_settings
from app.logging import get_logger
from app.services.m365.tokens import TokenProvider

logger = get_logger(__name__)


class GraphRateLimiter:
    """Token-bucket rate limiter.

    Uses a Redis-backed counter to coordinate across worker processes.
    """

    def __init__(self, redis_client: Any, key: str, capacity: int, refill_per_sec: float) -> None:
        self._redis = redis_client
        self._key = key
        self._capacity = capacity
        self._refill = refill_per_sec

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, sleeping if necessary."""
        while True:
            bucket = float(await self._redis.get(self._key) or self._capacity)
            now = time.monotonic()
            last_refill = float(await self._redis.get(f"{self._key}:last_refill") or now)
            elapsed = max(0.0, now - last_refill)
            bucket = min(self._capacity, bucket + elapsed * self._refill)
            if bucket >= tokens:
                bucket -= tokens
                await self._redis.set(self._key, str(bucket))
                await self._redis.set(f"{self._key}:last_refill", str(now))
                return
            needed = tokens - bucket
            sleep_for = needed / self._refill
            await asyncio.sleep(sleep_for)


class GraphAPI:
    """Async Graph API client with retry + rate limiting."""

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        token_provider: TokenProvider,
        rate_limiter: GraphRateLimiter | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._tokens = token_provider
        self._rate_limiter = rate_limiter
        self._client = client or httpx.AsyncClient(base_url=self.GRAPH_BASE, timeout=httpx.Timeout(60.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GraphAPI":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        settings = get_settings()
        max_attempts = settings.graph_retry_max_attempts

        url = path if path.startswith("http") else f"{self.GRAPH_BASE}{path}"
        attempt = 0
        backoff = 1.0
        while True:
            attempt += 1
            if self._rate_limiter is not None:
                await self._rate_limiter.acquire()

            token = await self._tokens.ensure_fresh_access_token()
            headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {token}"}

            try:
                resp = await self._client.request(method, url, headers=headers, **kwargs)
            except httpx.TransportError as e:
                if attempt >= max_attempts:
                    logger.warning("graph_transport_error", path=path, attempt=attempt, error=str(e))
                    raise
                await asyncio.sleep(min(30, backoff))
                backoff *= 2
                continue

            if resp.status_code == 401:
                # Token expired — invalidate and retry once
                await self._tokens.invalidate_access_token()
                if attempt < max_attempts:
                    continue
                resp.raise_for_status()

            if resp.status_code in (429, 500, 502, 503, 504):
                retry_after = float(resp.headers.get("Retry-After", backoff))
                if attempt >= max_attempts:
                    logger.warning("graph_retry_exhausted", path=path, attempt=attempt, status=resp.status_code)
                    resp.raise_for_status()
                await asyncio.sleep(min(60, retry_after))
                backoff = max(backoff * 2, retry_after)
                continue

            resp.raise_for_status()
            return resp

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request("GET", path, **kwargs)

    async def get_json(self, path: str, **kwargs: Any) -> dict[str, Any]:
        resp = await self.get(path, **kwargs)
        return resp.json()

    async def get_paged(self, path: str, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        """Iterate an OData-paged collection."""
        url = path
        while url is not None:
            resp = await self.get(url, **kwargs)
            payload = resp.json()
            for value in payload.get("value", []):
                yield value
            url = payload.get("@odata.nextLink")

    async def get_delta(self, path: str, delta_link: str | None = None, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        """Issue a delta query and return (items, new_delta_link)."""
        url = delta_link or f"{path}/delta"
        resp = await self.get(url, **kwargs)
        payload = resp.json()
        return payload.get("value", []), payload.get("@odata.deltaLink")

    async def download(self, url: str) -> AsyncIterator[bytes]:
        """Stream-download a binary URL (e.g. attachment or OneDrive content)."""
        token = await self._tokens.ensure_fresh_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with self._client.stream("GET", url, headers=headers) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                yield chunk


__all__ = ["GraphAPI", "GraphRateLimiter"]
