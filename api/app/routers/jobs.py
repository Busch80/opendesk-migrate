"""Migration job routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session_dep
from app.logging import get_logger
from app.models import AuditLog, JobPhase, MigrationJob
from app.schemas import JobRead, JobRetry, JobStart

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def start_job(payload: JobStart, session: AsyncSession = Depends(db_session_dep)) -> JobRead:
    job = MigrationJob(
        tenant_id=str(payload.user_id),  # placeholder; actual tenant_id is looked up from user
        user_id=str(payload.user_id),
        job_type=payload.job_type,
        phase=payload.phase,
    )
    # Look up tenant_id properly via user
    from app.models import UserM365

    res = await session.execute(select(UserM365).where(UserM365.id == str(payload.user_id)))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    job.tenant_id = user.tenant_id

    session.add(job)
    session.add(
        AuditLog(
            tenant_id=user.tenant_id,
            actor="system",
            action="job.start",
            target=str(payload.user_id),
            payload={"job_type": payload.job_type.value, "phase": payload.phase.value, "dry_run": payload.dry_run},
        )
    )
    await session.commit()
    await session.refresh(job)

    # Enqueue Celery task
    try:
        from app.tasks import dispatch_job  # local import — avoid celery import at startup

        dispatch_job.delay(str(job.id))
    except Exception as e:  # noqa: BLE001
        logger.warning("celery_dispatch_failed", job_id=str(job.id), error=str(e))

    return JobRead.model_validate(job)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    session: AsyncSession = Depends(db_session_dep),
) -> list[JobRead]:
    stmt = select(MigrationJob).order_by(MigrationJob.created_at.desc()).limit(100)
    if tenant_id is not None:
        stmt = stmt.where(MigrationJob.tenant_id == str(tenant_id))
    if user_id is not None:
        stmt = stmt.where(MigrationJob.user_id == str(user_id))
    res = await session.execute(stmt)
    return [JobRead.model_validate(j) for j in res.scalars()]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: UUID, session: AsyncSession = Depends(db_session_dep)) -> JobRead:
    res = await session.execute(select(MigrationJob).where(MigrationJob.id == str(job_id)))
    job = res.scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return JobRead.model_validate(job)


@router.post("/{job_id}/retry", response_model=JobRead)
async def retry_job(job_id: UUID, _payload: JobRetry, session: AsyncSession = Depends(db_session_dep)) -> JobRead:
    res = await session.execute(select(MigrationJob).where(MigrationJob.id == str(job_id)))
    job = res.scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    job.phase = JobPhase.FULL
    job.last_error = None
    session.add(
        AuditLog(tenant_id=job.tenant_id, actor="system", action="job.retry", target=str(job_id), payload={})
    )
    await session.commit()
    await session.refresh(job)
    try:
        from app.tasks import dispatch_job

        dispatch_job.delay(str(job.id))
    except Exception as e:  # noqa: BLE001
        logger.warning("celery_retry_dispatch_failed", job_id=str(job.id), error=str(e))
    return JobRead.model_validate(job)


@router.post("/{job_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(job_id: UUID, session: AsyncSession = Depends(db_session_dep)) -> None:
    res = await session.execute(select(MigrationJob).where(MigrationJob.id == str(job_id)))
    job = res.scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    job.phase = JobPhase.CANCELLED
    session.add(AuditLog(tenant_id=job.tenant_id, actor="system", action="job.cancel", target=str(job_id)))
    await session.commit()
