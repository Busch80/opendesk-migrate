"""OAuth token management for M365 users.

Each M365 user has one OAuth token row (per-tenant delegation).
Refresh happens automatically in a Celery beat job, but also on-demand
when the API client notices expiry.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

import httpx

from app.config import get_settings
from app.logging import get_logger
from app.services.encryption import Cipher

logger = get_logger(__name__)


@dataclass
class TokenSet:
    """In-memory representation of a user's tokens."""

    access_token: str | None
    refresh_token: str
    expires_at: datetime
    scopes: list[str]


class TokenProvider(Protocol):
    async def ensure_fresh_access_token(self) -> str: ...
    async def invalidate_access_token(self) -> None: ...


class M365TokenProvider:
    """Concrete TokenProvider backed by TenantSecret + UserOAuthToken.

    Use: created per-user, holds a lock so that within a worker process
    concurrent migrations don't double-refresh the same token.
    """

    def __init__(
        self,
        *,
        user_id: str,
        tenant_id: str,
        tenant_secret_row: Any,  # ORM row with *_enc columns
        user_token_row: Any,  # ORM row with *_enc columns
        cipher: Cipher,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._user_id = user_id
        self._tenant_id = tenant_id
        self._tenant_secret = tenant_secret_row
        self._user_token = user_token_row
        self._cipher = cipher
        self._http = http_client or httpx.AsyncClient(timeout=30.0)
        self._lock = asyncio.Lock()
        self._cached: TokenSet | None = None

    async def ensure_fresh_access_token(self) -> str:
        async with self._lock:
            ts = self._cached or self._load_from_db()
            now = datetime.now(tz=timezone.utc)
            # Refresh if expiry within 5 minutes
            if ts.access_token is None or (ts.expires_at - now) < timedelta(minutes=5):
                ts = await self._refresh()
                self._persist(ts)
            self._cached = ts
            assert ts.access_token is not None
            return ts.access_token

    async def invalidate_access_token(self) -> None:
        """Force a refresh on next request."""
        async with self._lock:
            self._cached = None

    def _load_from_db(self) -> TokenSet:
        return TokenSet(
            access_token=self._cipher.decrypt(self._user_token.access_token_enc),
            refresh_token=self._cipher.decrypt(self._user_token.refresh_token_enc) or "",
            expires_at=self._user_token.expires_at or datetime.now(tz=timezone.utc),
            scopes=list(self._user_token.scopes or []),
        )

    async def _refresh(self) -> TokenSet:
        """Exchange refresh_token for new token set via MSAL."""
        from msal import ConfidentialClientApplication

        settings = get_settings()
        client_id = self._cipher.decrypt(self._tenant_secret.m365_client_id_enc) or ""
        client_secret = self._cipher.decrypt(self._tenant_secret.m365_client_secret_enc) or ""
        assert self._cached is not None
        assert self._cached.refresh_token, "No refresh token"

        authority = settings.m365_authority
        if self._tenant_secret.tenant.m365_tenant_id:
            authority = f"{settings.m365_authority}/{self._tenant_secret.tenant.m365_tenant_id}"

        app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority,
        )
        result = app.acquire_token_by_refresh_token(
            refresh_token=self._cached.refresh_token,
            scopes=self._cached.scopes or [
                "https://graph.microsoft.com/Mail.Read",
                "https://graph.microsoft.com/Calendars.Read",
                "https://graph.microsoft.com/Contacts.Read",
                "https://graph.microsoft.com/Files.Read.All",
                "https://graph.microsoft.com/User.Read",
                "offline_access",
            ],
        )

        if "error" in result:
            logger.warning("msal_refresh_failed", user_id=self._user_id, error=result.get("error_description"))
            raise RuntimeError(f"MSAL refresh failed: {result.get('error_description')}")

        access_token = result["access_token"]
        new_refresh = result.get("refresh_token") or self._cached.refresh_token
        expires_in = int(result.get("expires_in", 3600))
        new_expiry = datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)
        scopes = result.get("scope", "").split() or self._cached.scopes
        return TokenSet(access_token, new_refresh, new_expiry, scopes)

    def _persist(self, ts: TokenSet) -> None:
        self._user_token.access_token_enc = self._cipher.encrypt(ts.access_token)
        self._user_token.refresh_token_enc = self._cipher.encrypt(ts.refresh_token)
        self._user_token.expires_at = ts.expires_at
        self._user_token.scopes = ts.scopes


__all__ = ["M365TokenProvider", "TokenSet", "TokenProvider"]
