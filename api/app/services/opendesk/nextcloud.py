"""Nextcloud integration for OneDrive target.

Two paths:
1. **OCS Admin** for user provisioning and shares (admin-level).
2. **WebDAV** for file uploads from the user perspective.

In dev / CI we mock both.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NextcloudConnection:
    base_url: str  # e.g. https://nc.opendesk.example
    admin_user: str
    admin_password: str


class NextcloudAdmin(Protocol):
    async def create_user(self, user_id: str, password: str, display_name: str = "", email: str = "") -> bool: ...
    async def delete_user(self, user_id: str) -> bool: ...
    async def list_users(self, search: str = "") -> list[dict[str, Any]]: ...
    async def healthcheck(self) -> dict[str, Any]: ...


class NextcloudOCSAdmin:
    """OCS Admin client. Real implementation lands in nextcloud_ocs.py."""

    def __init__(self, conn: NextcloudConnection, client: httpx.AsyncClient | None = None) -> None:
        self._conn = conn
        self._client = client or httpx.AsyncClient(
            base_url=f"{conn.base_url}/ocs/v2.php/cloud",
            timeout=30.0,
            auth=(conn.admin_user, conn.admin_password),
            headers={"OCS-APIRequest": "true", "Accept": "application/json"},
        )

    async def healthcheck(self) -> dict[str, Any]:
        try:
            resp = await self._client.get("users", timeout=10.0)
            return {
                "base_url": str(resp.url),
                "status_code": resp.status_code,
                "ok": resp.status_code in (200, 997),  # 997 = no users yet
            }
        except httpx.HTTPError as e:
            return {"ok": False, "error": str(e)}

    async def create_user(self, user_id: str, password: str, display_name: str = "", email: str = "") -> bool:
        resp = await self._client.post(
            "users",
            data={
                "userid": user_id,
                "password": password,
                "displayName": display_name,
                "email": email,
            },
        )
        return resp.status_code == 200

    async def delete_user(self, user_id: str) -> bool:
        resp = await self._client.delete(f"users/{user_id}")
        return resp.status_code == 200


class NextcloudWebDavClient:
    """WebDAV client for OneDrive → Nextcloud file transfers."""

    def __init__(self, conn: NextcloudConnection, user_id: str, password: str) -> None:
        self._dav_url = f"{conn.base_url}/remote.php/dav/files/{user_id}"
        self._auth = httpx.BasicAuth(user_id, password)
        self._client = httpx.AsyncClient(
            base_url=self._dav_url, auth=self._auth, timeout=httpx.Timeout(300.0, read=600.0)
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def mkdir(self, path: str) -> bool:
        resp = await self._client.request("MKCOL", path)
        return resp.status_code in (201, 301, 405)

    async def upload(self, path: str, content: bytes | httpx.AsyncIterator[bytes]) -> bool:
        resp = await self._client.put(path, content=content)
        return resp.status_code in (201, 204)

    async def upload_file(self, path: str, local_path: str) -> bool:
        with open(local_path, "rb") as f:
            resp = await self._client.put(path, content=f)
        return resp.status_code in (201, 204)

    async def stat(self, path: str) -> dict[str, Any] | None:
        resp = await self._client.request("PROPFIND", path, headers={"Depth": "0"})
        if resp.status_code == 404:
            return None
        if resp.status_code == 207:
            return {"path": path, "status": resp.status_code}
        return None

    async def list_dir(self, path: str) -> list[dict[str, Any]]:
        resp = await self._client.request(
            "PROPFIND", path, headers={"Depth": "1", "Content-Type": "application/xml"}
        )
        if resp.status_code != 207:
            return []
        # Real parse of multistatus XML goes here.
        return []


__all__ = [
    "NextcloudAdmin",
    "NextcloudConnection",
    "NextcloudOCSAdmin",
    "NextcloudWebDavClient",
]
