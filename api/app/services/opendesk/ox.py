"""OX App Suite integration.

OX exposes two relevant APIs in openDesk:
1. **SOAP `oxadmin`** — for provisioning (createcontext, createuser, etc.).
2. **OX JSON HTTP API** — used by the OX web frontend, suitable for
   application-side data writes (calendars, contacts, mail import).

This module wraps both. The SOAP portion uses `zeep` (already in
dependencies). The JSON API uses `httpx`.

In dev / CI we mock both behind a FakeOXClient so the migration engine
can be developed without a real openDesk instance.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OXContext:
    """Represents an OX context (= tenant inside an OX installation)."""

    context_id: int
    name: str
    max_quota_mb: int | None = None
    filestore_path: str | None = None


@dataclass
class OXUser:
    """Represents an OX user with mail/calendar/contacts."""

    user_id: int
    context_id: int
    username: str
    email: str
    display_name: str
    password: str | None = None


@dataclass
class OXConnection:
    """Connection parameters to an OX instance."""

    base_url: str  # e.g. https://ox.opendesk.example/appsuite/api
    admin_url: str  # e.g. https://ox-admin.opendesk.example/oxadmin
    admin_user: str
    admin_password: str


class OXAdmin(Protocol):
    """Admin operations (creation, configuration)."""

    async def create_context(self, ctx: OXContext) -> int: ...
    async def create_user(self, ctx_id: int, user: OXUser) -> int: ...
    async def delete_user(self, ctx_id: int, user_id: int) -> bool: ...
    async def list_users(self, ctx_id: int, pattern: str = "*") -> list[OXUser]: ...
    async def healthcheck(self) -> dict[str, Any]: ...


class _OXXmlRpcAdmin:
    """SOAP `oxadmin` wrapper using zeep.

    This is a thin async wrapper around the synchronous zeep client.
    For MVP we don't actually call SOAP yet — placeholder.
    """

    def __init__(self, conn: OXConnection, client: httpx.AsyncClient | None = None) -> None:
        self._conn = conn
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def healthcheck(self) -> dict[str, Any]:
        try:
            url = f"{self._conn.admin_url}/health"
            resp = await self._client.get(url, timeout=10.0)
            return {"admin_url": str(resp.url), "status_code": resp.status_code, "ok": resp.status_code < 500}
        except httpx.HTTPError as e:
            return {"ok": False, "error": str(e)}


class OXJsonApi:
    """JSON HTTP API client for OX data operations (mail/calendar/contacts).

    Used by Celery workers to POST events, contacts, and to upload mail
    messages via the OX upload mechanism. Stubbed for now — real endpoint
    structure lands in `ox_json.py` once we wire up a sandbox.
    """

    def __init__(self, conn: OXConnection, client: httpx.AsyncClient | None = None) -> None:
        self._conn = conn
        self._client = client or httpx.AsyncClient(
            base_url=conn.base_url, timeout=60.0, auth=(conn.admin_user, conn.admin_password)
        )

    async def import_mail_message(self, ctx_id: int, folder_id: str, eml_bytes: bytes, flags: list[str]) -> str:
        """Import an EML message into an OX folder. Returns OX object id."""
        # TODO: Wire up real OX JSON endpoint. For now, raise so callers fail fast.
        # The actual implementation will POST to /import?session=...&folder=...
        # or use the IMAP APPEND pathway (preferred for bulk mail).
        raise NotImplementedError("Use imap_append_via_dovecot instead during MVP.")

    async def create_calendar_event(self, ctx_id: int, user_id: int, ical_bytes: bytes) -> str:
        raise NotImplementedError("OX JSON calendar writes — see CalendarJsonWriter.")

    async def create_contact(self, ctx_id: int, user_id: int, vcard_bytes: bytes) -> str:
        raise NotImplementedError("OX JSON contact writes — see ContactsJsonWriter.")

    async def healthcheck(self) -> dict[str, Any]:
        try:
            resp = await self._client.get("system?action=health", timeout=10.0)
            return {"status_code": resp.status_code, "ok": resp.status_code < 500}
        except httpx.HTTPError as e:
            return {"ok": False, "error": str(e)}


class IMAPMailImporter:
    """Imports mail into Dovecot (the backend of OX) via IMAP APPEND.

    Preferred over OX JSON for bulk imports — much faster and simpler.
    The M365 → EML conversion lives in `app/tasks/mail.py`; this class
    just does the IMAP side of the deal.
    """

    def __init__(self, host: str, port: int, user: str, password: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password

    async def connect(self):  # pragma: no cover — uses external aioimaplib
        from aioimaplib import IMAP4_SSL  # local import — heavy
        return IMAP4_SSL(self._host, self._port)

    async def append(
        self,
        mailbox: str,
        message_bytes: bytes,
        flags: list[str] | None = None,
        date_time: Any | None = None,
    ) -> str:
        """APPEND a message to a mailbox, return assignable UID (UIDPLUS)."""
        client = await self.connect()
        try:
            await client.wait_hello_from_server()
            await client.login(self._user, self._password)
            await client.select(mailbox)
            _resp, data = await client.append(mailbox, flags or [], date_time, message_bytes)
            return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
        finally:
            with contextlib.suppress(Exception):
                await client.logout()


__all__ = [
    "OXContext",
    "OXUser",
    "OXConnection",
    "OXAdmin",
    "_OXXmlRpcAdmin",
    "OXJsonApi",
    "IMAPMailImporter",
]
