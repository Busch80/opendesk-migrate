"""Audit log route — read-only access to AuditLog rows."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session_dep
from app.models import AuditLog

router = APIRouter()


@router.get("")
async def list_audit_log(
    tenant_id: str | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(db_session_dep),
) -> list[dict]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if tenant_id is not None:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    res = await session.execute(stmt)
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "actor": r.actor,
            "action": r.action,
            "target": r.target,
            "payload": r.payload,
            "ip": r.ip,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in res.scalars()
    ]
