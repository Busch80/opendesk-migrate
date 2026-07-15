"""FastAPI dependencies shared across routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session


async def db_session_dep(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


TenantHeader = Annotated[str | None, Header(alias="X-Tenant-Code", description="KPX customer code")]
RequestIDHeader = Annotated[str | None, Header(alias="X-Request-ID", description="Correlation ID")]


__all__ = ["db_session_dep", "TenantHeader", "RequestIDHeader"]
