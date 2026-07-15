"""Error listing route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session_dep
from app.models import Error
from app.schemas import ErrorRead

router = APIRouter()


@router.get("", response_model=list[ErrorRead])
async def list_errors(
    job_id: str | None = None,
    resolved: bool | None = False,
    limit: int = 100,
    session: AsyncSession = Depends(db_session_dep),
) -> list[ErrorRead]:
    stmt = select(Error).order_by(Error.created_at.desc()).limit(limit)
    if job_id is not None:
        stmt = stmt.where(Error.job_id == job_id)
    if resolved is not None:
        stmt = stmt.where(Error.resolved == resolved)
    res = await session.execute(stmt)
    return [ErrorRead.model_validate(e) for e in res.scalars()]


@router.post("/{error_id}/resolve", status_code=status.HTTP_204_NO_CONTENT)
async def resolve_error(error_id: int, session: AsyncSession = Depends(db_session_dep)) -> None:
    from sqlalchemy import update

    await session.execute(update(Error).where(Error.id == error_id).values(resolved=True))
    await session.commit()
